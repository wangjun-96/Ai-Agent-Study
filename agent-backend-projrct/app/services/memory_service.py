"""业务层：会话记忆（即时记忆 / 工作记忆 / 记忆服务）。

三层记忆：
1. InstantMemory：MySQL 最近 8 轮 + 字符预算裁剪，作为 Redis 失效时的兜底；
2. WorkingMemory：Redis 保存原始对话与摘要，超过 8000 字触发总结裁剪，TTL 8 小时；
3. LongTermMemory（见 long_term_memory.py）：用户画像摘要注入，跨会话长期生效。

本模块只负责读取、裁剪、格式化上下文；模型实例由调用方传入或按需创建。
"""
from collections.abc import Iterable
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core import get_logger, settings
from app.dao.message_dao import MessageDao
from app.db.models import ChatMessage
from app.integrations.redis_client import RedisCache
from app.services.long_term_memory import LongTermMemory

logger = get_logger("memory_service")

# 工作记忆 Key 前缀：memory:working:{user_id}:{session_id}
WORKING_KEY_PREFIX = "memory:working"
# 工作记忆 Hash 字段
WORKING_STATE_FIELD = "state"


def build_chat_history_from_rows(rows: Iterable[ChatMessage]) -> list[BaseMessage]:
    """把数据库消息行转换为 LangChain 消息列表（按时间正序）。"""
    history: list[BaseMessage] = []
    for row in rows:
        if row.request_text:
            history.append(HumanMessage(content=row.request_text))
        if row.response_text:
            history.append(AIMessage(content=row.response_text))
    return history


def build_chat_history_from_messages(messages: list[dict]) -> list[BaseMessage]:
    """把工作记忆中的 {role, content} 列表转换为 LangChain 消息列表。"""
    history: list[BaseMessage] = []
    for item in messages:
        role = item.get("role")
        content = item.get("content") or ""
        if not content:
            continue
        if role == "user":
            history.append(HumanMessage(content=content))
        elif role == "assistant":
            history.append(AIMessage(content=content))
    return history


class InstantMemory:
    """即时记忆：直接读取 MySQL 最近若干轮对话，并按字符预算裁剪。"""

    def __init__(
        self,
        message_dao: MessageDao,
        max_turns: int | None = None,
        max_chars: int | None = None,
    ) -> None:
        self.message_dao = message_dao
        self.max_turns = max_turns or settings.MEMORY_MAX_TURNS
        self.max_chars = max_chars or settings.MEMORY_MAX_CHARS

    def load(self, session_id: int) -> list[BaseMessage]:
        """加载最近对话轮次，超出字符预算时从最旧一轮开始裁剪。"""
        rows = self.message_dao.list_recent_by_session(
            session_id, limit=self.max_turns
        )
        rows = self._fit_char_budget(rows)
        return build_chat_history_from_rows(rows)

    def _fit_char_budget(self, rows: list[ChatMessage]) -> list[ChatMessage]:
        """字符预算裁剪：从最新一轮向前累计，超预算即停止。"""
        if not rows:
            return []

        kept: list[ChatMessage] = []
        total = 0
        for row in reversed(rows):
            current = len(row.request_text or "") + len(row.response_text or "")
            if kept and total + current > self.max_chars:
                break
            kept.append(row)
            total += current
        kept.reverse()

        if len(kept) < len(rows):
            logger.info(
                "即时记忆超出预算已裁剪 original={} kept={} chars={} budget={}",
                len(rows),
                len(kept),
                total,
                self.max_chars,
            )
        return kept


def quick_summarize(
    llm: Any, messages: list[dict], old_summary: str = ""
) -> str:
    """把较早对话压缩为不超过 SUMMARY_MAX_CHARS 的摘要。

    :param llm: LangChain 模型实例（一次性生成）
    :param messages: [{role, content}] 较早的对话消息
    :param old_summary: 已有摘要，需与新内容合并
    """
    transcript = "\n".join(
        f"{'用户' if item.get('role') == 'user' else 'AI'}：{item.get('content', '')}"
        for item in messages
        if item.get("content")
    )
    if not transcript.strip():
        return old_summary
    prompt = (
        "请把以下对话压缩成中文摘要，保留用户目标、关键事实、已解决问题与待办事项。"
        f"摘要不超过 {settings.SUMMARY_MAX_CHARS} 字。\n"
        f"已有摘要：{old_summary or '无'}\n"
        f"新增对话：\n{transcript}\n"
        "只输出摘要正文，不要解释。"
    )
    try:
        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
    except Exception as exc:  # noqa: BLE001 摘要失败降级为截断
        logger.warning("工作记忆摘要失败，降级为截断 error={}", exc)
        content = (old_summary + "\n" + transcript).strip()
    return content.strip()[: settings.SUMMARY_MAX_CHARS]


class WorkingMemory:
    """工作记忆：Redis 保存原始对话 + 摘要，读写自动续期 TTL。"""

    def __init__(self, cache: RedisCache | None, llm: Any | None = None) -> None:
        self.cache = cache
        self.llm = llm

    @staticmethod
    def _key(user_id: int, session_id: int) -> str:
        return f"{WORKING_KEY_PREFIX}:{user_id}:{session_id}"

    def get(self, user_id: int, session_id: int) -> dict:
        """读取工作记忆，命中时续期 TTL；无缓存返回空状态。"""
        if self.cache is None:
            return {"messages": [], "summary": ""}
        state = self.cache.hget_json(self._key(user_id, session_id), WORKING_STATE_FIELD)
        if not state:
            return {"messages": [], "summary": ""}
        self.cache.expire(
            self._key(user_id, session_id), settings.WORKING_MEMORY_TTL_SECONDS
        )
        return {
            "messages": state.get("messages") or [],
            "summary": state.get("summary") or "",
        }

    def append_turn(
        self,
        user_id: int,
        session_id: int,
        request_text: str,
        response_text: str,
    ) -> None:
        """追加一轮对话；总字符超阈值时保留最近若干条并生成摘要。"""
        if self.cache is None:
            # Redis 不可用时无需写入，下一轮由 InstantMemory 从 MySQL 兜底
            return
        state = self.get(user_id, session_id)
        messages: list[dict] = list(state["messages"])
        summary: str = state["summary"]
        messages.extend(
            [
                {"role": "user", "content": request_text},
                {"role": "assistant", "content": response_text},
            ]
        )

        total_chars = sum(len(item.get("content") or "") for item in messages)
        if total_chars > settings.WORKING_MEMORY_MAX_CHARS:
            keep = settings.WORKING_MEMORY_KEEP_MESSAGES
            older = messages[:-keep] if len(messages) > keep else []
            if older:
                llm = self._resolve_llm()
                if llm is not None:
                    summary = quick_summarize(llm, older, summary)
                else:
                    summary = quick_summarize_offline(older, summary)
                messages = messages[-keep:]
                logger.info(
                    "工作记忆触发总结 user_id={} session_id={} summarized={} kept={}",
                    user_id,
                    session_id,
                    len(older),
                    len(messages),
                )

        self.cache.hset_json(
            self._key(user_id, session_id),
            WORKING_STATE_FIELD,
            {"messages": messages, "summary": summary},
        )
        self.cache.expire(
            self._key(user_id, session_id), settings.WORKING_MEMORY_TTL_SECONDS
        )

    def _resolve_llm(self) -> Any | None:
        """获取摘要模型：优先复用传入实例，否则按需创建（失败返回 None）。"""
        if self.llm is not None:
            return self.llm
        try:
            from app.llm.llm import get_llm

            self.llm = get_llm(streaming=False)
            return self.llm
        except Exception as exc:  # noqa: BLE001 模型不可用降级为截断摘要
            logger.warning("工作记忆摘要模型不可用，降级为截断 error={}", exc)
            return None


def quick_summarize_offline(messages: list[dict], old_summary: str) -> str:
    """无模型时的离线摘要：拼接旧摘要与较早对话并截断。"""
    transcript = "\n".join(
        f"{'用户' if item.get('role') == 'user' else 'AI'}：{item.get('content', '')}"
        for item in messages
        if item.get("content")
    )
    merged = (old_summary + "\n" + transcript).strip()
    return merged[-settings.SUMMARY_MAX_CHARS :]


class MemoryService:
    """记忆服务：统一加载上下文（长期画像 + 工作记忆/即时记忆）与写入轮次。"""

    def __init__(
        self,
        message_dao: MessageDao,
        cache: RedisCache | None = None,
        llm: Any | None = None,
    ) -> None:
        self.message_dao = message_dao
        self.instant = InstantMemory(message_dao)
        self.working = WorkingMemory(cache, llm)

    def load_context(
        self,
        session_id: int,
        user_id: int,
        *,
        enable_long_term: bool = True,
    ) -> list[BaseMessage]:
        """加载完整上下文：长期画像 SystemMessage + 摘要 + 对话消息。

        Redis 优先读取工作记忆，未命中回落 MySQL 即时记忆。
        """
        history: list[BaseMessage] = []

        if enable_long_term:
            profile_text = LongTermMemory.load_memory_context(
                user_id, self.message_dao.db
            )
            if profile_text:
                history.append(SystemMessage(content=profile_text))

        working = self.working.get(user_id, session_id)
        summary = working.get("summary") or ""
        if summary:
            history.append(
                SystemMessage(content=f"以下是本会话较早对话的摘要：\n{summary}")
            )

        raw_messages = working.get("messages") or []
        if raw_messages:
            history.extend(build_chat_history_from_messages(raw_messages))
        else:
            history.extend(self.instant.load(session_id))

        logger.info(
            "记忆上下文加载 session_id={} user_id={} messages={} long_term={}",
            session_id,
            user_id,
            len(history),
            bool(enable_long_term),
        )
        return history

    def append_turn(
        self,
        user_id: int,
        session_id: int,
        request_text: str,
        response_text: str,
    ) -> None:
        """把本轮问答写入工作记忆。"""
        self.working.append_turn(user_id, session_id, request_text, response_text)

    def recent_context_text(self, session_id: int, limit_turns: int = 4) -> str:
        """取最近若干轮对话的纯文本，用于长期记忆画像抽取上下文。"""
        rows = self.message_dao.list_recent_by_session(session_id, limit=limit_turns)
        lines: list[str] = []
        for row in rows:
            if row.request_text:
                lines.append(f"用户：{row.request_text}")
            if row.response_text:
                lines.append(f"AI：{row.response_text}")
        return "\n".join(lines)
