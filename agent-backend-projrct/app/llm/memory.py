"""记忆层：只负责从数据库查询多轮历史对话，构建并拼接成最终上下文。

职责边界（见 prompt.md「三层架构」）：
- 只做「历史消息读取 + 字符预算裁剪 + 上下文格式化」；
- 不负责模型实例创建（模型层 llm.py）；
- 不负责提示词模板与链路组装（提示词层 prompt_layer.py）。

上下文形态：
- load()          ：返回 LangChain 消息列表（HumanMessage / AIMessage），供 Prompt 直接插入；
- build_context() ：返回纯文本上下文，供需要以字符串方式注入提示词的场景使用。
"""
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.core import get_logger, settings
from app.dao.message_dao import MessageDao
from app.db.models import ChatMessage

logger = get_logger("memory")


class ChatMemory:
    """短期记忆：按会话读取最近若干轮对话并裁剪为可控长度的上下文。"""

    def __init__(
        self,
        message_dao: MessageDao,
        max_turns: int | None = None,
        max_chars: int | None = None,
    ) -> None:
        """
        :param message_dao: 消息 DAO（数据库查询统一走 DAO 层）
        :param max_turns: 最大回带轮数，缺省读取配置 MEMORY_MAX_TURNS
        :param max_chars: 上下文总字符预算，缺省读取配置 MEMORY_MAX_CHARS
        """
        self.message_dao = message_dao
        self.max_turns = max_turns or settings.MEMORY_MAX_TURNS
        self.max_chars = max_chars or settings.MEMORY_MAX_CHARS

    def load(self, session_id: int) -> list[BaseMessage]:
        """加载会话历史，转换为 LangChain 消息列表（按时间正序）。

        :param session_id: 会话 ID
        :return: [HumanMessage, AIMessage, ...] 按对话时序排列
        """
        rows = self._load_rows(session_id)
        history: list[BaseMessage] = []
        for row in rows:
            if row.request_text:
                history.append(HumanMessage(content=row.request_text))
            if row.response_text:
                history.append(AIMessage(content=row.response_text))
        return history

    def build_context(self, session_id: int) -> str:
        """加载会话历史并拼接为纯文本上下文。

        格式：每轮两行——「用户：xxx」「AI：xxx」，轮次之间空行分隔。

        :param session_id: 会话 ID
        :return: 可直接注入提示词的上下文字符串，无历史时返回空串
        """
        rows = self._load_rows(session_id)
        lines: list[str] = []
        for row in rows:
            if row.request_text:
                lines.append(f"用户：{row.request_text}")
            if row.response_text:
                lines.append(f"AI：{row.response_text}")
        context = "\n\n".join(
            "\n".join(lines[index : index + 2]) for index in range(0, len(lines), 2)
        )
        logger.info(
            "构建会话上下文 session_id={} rounds={} chars={}",
            session_id,
            len(rows),
            len(context),
        )
        return context

    def _load_rows(self, session_id: int) -> list[ChatMessage]:
        """按会话读取最近 max_turns 轮消息，并按字符预算裁剪。"""
        rows = self.message_dao.list_recent_by_session(
            session_id, limit=self.max_turns
        )
        return self._fit_char_budget(rows)

    def _fit_char_budget(self, rows: list[ChatMessage]) -> list[ChatMessage]:
        """字符预算裁剪：从最新一轮向前累计，超预算即停止，保证时序连续。

        :param rows: 按时间正序排列的消息行
        :return: 裁剪后的消息行（仍为正序）
        """
        if not rows:
            return []

        kept: list[ChatMessage] = []
        total = 0
        # 从最新（列表末尾）向前遍历，累计字符数未超预算则保留
        for row in reversed(rows):
            current = len(row.request_text or "") + len(row.response_text or "")
            if kept and total + current > self.max_chars:
                break
            kept.append(row)
            total += current
        kept.reverse()

        if len(kept) < len(rows):
            logger.info(
                "上下文超出字符预算已裁剪 original={} kept={} chars={} budget={}",
                len(rows),
                len(kept),
                total,
                self.max_chars,
            )
        return kept
