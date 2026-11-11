"""业务层：AI 聊天流式响应编排。

职责：
- 复用分层：模型层（app.llm.llm）→ 提示词层（app.llm.prompt_layer）
  → 记忆层（app.services.memory_service）；
- 负责会话归属校验、RAG 检索、SSE 事件组织、本轮消息落库；
- 不直接写 SQL、不拼接提示词、不创建模型实例。

SSE 事件协议（每条 data 为 JSON）：
- {"type": "start",  "session_id": 1}
- {"type": "delta",  "content": "增量文本"}
- {"type": "done",   "message_id": 123, "create_at": 1694502400,
  "content": "完整回复", "sources": [来源片段]}
- {"type": "error",  "code": 50000, "message": "中文提示"}
"""
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core import BusinessException, SystemException, get_logger
from app.dao.message_dao import MessageDao
from app.dao.prompt_template_dao import PromptTemplateDao
from app.dao.session_dao import SessionDao
from app.dao.user_profile_dao import UserProfileDao
from app.db.models import ChatMessage
from app.enums.response_code import ResponseCode
from app.integrations.redis_client import get_redis_cache
from app.llm.llm import get_llm
from app.llm.prompt_layer import (
    DEFAULT_SYSTEM_PROMPT,
    build_chain,
    merge_system_messages,
)
from app.rag.chat_rag import (
    build_rag_system_prompt,
    format_retrieved_chunks,
    should_retrieve,
)
from app.rag.retriever import search_similar_chunks
from app.schemas.message import StreamChatRequest
from app.services.long_term_memory import LongTermMemory
from app.services.memory_service import MemoryService
from app.services.prompt_template_service import PromptTemplateManager
from app.services.prompt_variable_service import PromptVariableService

logger = get_logger("stream_chat_service")


def _sse(payload: dict[str, Any]) -> str:
    """把事件字典编码为 SSE 数据帧（data: {...}\\n\\n）。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_to_text(chunk: Any) -> str:
    """提取模型流式增量文本：兼容纯文本与分段内容列表两种返回形态。"""
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


class StreamChatService:
    """流式聊天业务服务。"""

    def __init__(
        self,
        session_dao: SessionDao,
        db_factory: Callable[[], Session],
    ) -> None:
        """
        :param session_dao: 会话 DAO（请求级，用于流开始前的归属校验）
        :param db_factory: Session 工厂（流式响应期间需独立管理 Session 生命周期）
        """
        self.session_dao = session_dao
        self.db_factory = db_factory

    def assert_session(self, session_id: int, user_id: int) -> None:
        """校验会话存在且归属当前用户，越权统一按不存在处理（返回 404）。"""
        if self.session_dao.get_session_by_user(session_id, user_id) is None:
            raise BusinessException(
                ResponseCode.SESSION_NOT_FOUND, detail=f"session_id={session_id}"
            )

    async def stream(
        self, session_id: int, user_id: int, payload: StreamChatRequest
    ) -> AsyncIterator[str]:
        """执行流式对话并逐帧输出 SSE 事件。

        流式响应期间不能依赖请求级数据库会话（FastAPI 会在返回响应前清理依赖），
        因此在生成器内部通过 db_factory 独立创建 Session，结束时关闭。
        """
        db = self.db_factory()
        message_dao = MessageDao(db)
        reply_parts: list[str] = []
        try:
            # 1. 模型层：流式模型实例（同时供工作记忆摘要复用）
            llm = get_llm(streaming=True)

            # 2. 记忆层：长期画像 + 工作记忆/即时记忆
            memory = MemoryService(message_dao, get_redis_cache(), llm)
            history = memory.load_context(session_id, user_id)

            # 3. 长期记忆写入意图判断：命中则跳过 RAG，避免画像类输入被资料干扰
            profile_write = LongTermMemory.should_write(payload.request_text)

            # 4. RAG 检索：规则判断 → 向量召回；检索异常不影响主对话
            sources: list[dict] = []
            if not profile_write and should_retrieve(payload.request_text):
                try:
                    sources = search_similar_chunks(
                        payload.request_text, user_id, db
                    )
                except Exception as exc:  # noqa: BLE001 检索失败降级为普通对话
                    logger.warning(
                        "RAG 检索失败，降级为普通对话 session_id={} error={}",
                        session_id,
                        exc,
                    )

            # 5. 提示词层：公共模板 + 私有模板 + 用户画像变量
            template_manager = PromptTemplateManager(
                PromptTemplateDao(db), get_redis_cache()
            )
            system_prompt = (
                PromptVariableService(UserProfileDao(db)).build_system_prompt(
                    template_manager, payload.agent_name, user_id
                )
                or DEFAULT_SYSTEM_PROMPT
            )
            if sources:
                system_prompt = build_rag_system_prompt(system_prompt)

            # 合并记忆层注入的 SystemMessage（长期画像 / 工作记忆摘要）
            history, system_prompt = merge_system_messages(history, system_prompt)
            chain = build_chain(llm, system_prompt=system_prompt)

            # 本轮问题前拼接参考资料
            request_text = payload.request_text
            if sources:
                request_text = (
                    f"{format_retrieved_chunks(sources)}\n\n"
                    f"用户问题：{payload.request_text}"
                )

            yield _sse({"type": "start", "session_id": session_id})

            # 6. 流式输出，逐段下发增量文本
            async for chunk in chain.astream(
                {
                    "history": history,
                    "request_text": request_text,
                }
            ):
                text = _chunk_to_text(chunk)
                if not text:
                    continue
                reply_parts.append(text)
                yield _sse({"type": "delta", "content": text})

            reply_text = "".join(reply_parts)
            if not reply_text:
                raise SystemException(
                    code=ResponseCode.SYSTEM_ERROR,
                    message="大模型未返回内容，请稍后再试",
                    detail="stream finished without content",
                )

            # 7. 本轮问答落库（RAG 来源只存 chunk_id / score）
            reference_sources = [
                {"chunk_id": item["chunk_id"], "score": item["score"]}
                for item in sources
            ]
            message = message_dao.insert_message(
                ChatMessage(
                    user_id=user_id,
                    session_id=session_id,
                    select_model=int(payload.select_model),
                    request_id=uuid.uuid4().hex,
                    request_text=payload.request_text,
                    response_text=reply_text,
                    request_segments=[
                        segment.model_dump() for segment in payload.request_segments
                    ],
                    reference_sources=reference_sources or None,
                )
            )

            # 8. 写入工作记忆；画像类输入异步更新长期记忆
            memory.append_turn(user_id, session_id, payload.request_text, reply_text)
            if profile_write:
                LongTermMemory.submit_profile_update_async(
                    user_id,
                    payload.request_text,
                    memory.recent_context_text(session_id, limit_turns=4),
                )

            logger.info(
                "流式对话完成 session_id={} user_id={} message_id={} reply_chars={} sources={}",
                session_id,
                user_id,
                message.id,
                len(reply_text),
                len(reference_sources),
            )
            yield _sse(
                {
                    "type": "done",
                    "message_id": message.id,
                    "create_at": message.create_at,
                    "content": reply_text,
                    "sources": sources,
                }
            )
        except (BusinessException, SystemException) as exc:
            logger.warning(
                "流式对话业务异常 session_id={} code={} detail={}",
                session_id,
                exc.code,
                exc.detail,
            )
            yield _sse({"type": "error", "code": exc.code, "message": exc.message})
        except Exception as exc:  # noqa: BLE001 流式场景需兜底，保证前端收到结束事件
            logger.exception("流式对话异常 session_id={} error={}", session_id, exc)
            yield _sse(
                {
                    "type": "error",
                    "code": int(ResponseCode.SYSTEM_ERROR),
                    "message": "系统繁忙，请稍后再试",
                }
            )
        finally:
            db.close()

    async def stream_chat(
        self, session_id: int, user_id: int, payload: StreamChatRequest
    ) -> AsyncIterator[str]:
        """兼容入口：供流程总控路由复用流式聊天分支。"""
        async for event in self.stream(session_id, user_id, payload):
            yield event
