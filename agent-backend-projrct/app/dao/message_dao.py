"""消息 DAO：封装 chat_messages 表的全部数据库操作。

设计要点：
1. 列表查询按 create_at 升序（聊天时序），与 (session_id, create_at) 复合索引对齐；
2. 级联删除由 SessionDao.delete_cascade 统一处理，本 DAO 不单独提供删除方法；
3. 禁止裸写原生 SQL 字符串拼接，统一使用 SQLAlchemy 2.0 语法。
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401
from app.db.models import ChatMessage


class MessageDao:
    """消息数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def count_by_session(self, session_id: int) -> int:
        """统计指定会话下的消息总数。"""
        stmt = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.session_id == session_id
        )
        return self.db.scalar(stmt) or 0

    def list_by_session(
        self, session_id: int, *, offset: int, limit: int
    ) -> list[ChatMessage]:
        """按会话分页查询消息，按创建时间升序（聊天时序）。"""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.create_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def list_all_by_session(self, session_id: int) -> list[ChatMessage]:
        """查询会话下的全部消息（级联删除时用于收集 segments 中的 resource_id）。"""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.create_at.asc())
        )
        return list(self.db.scalars(stmt))

    def list_recent_by_session(self, session_id: int, *, limit: int) -> list[ChatMessage]:
        """查询会话下最近的 limit 条消息（短期记忆用），返回按时间正序。

        时间粒度为秒，同一秒内按自增主键二次排序，保证对话时序稳定。
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.create_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        rows = list(self.db.scalars(stmt))
        rows.reverse()
        return rows

    def insert_message(self, message: ChatMessage) -> ChatMessage:
        """插入一条聊天消息，自带事务，失败自动回滚。"""
        try:
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception:
            self.db.rollback()
            raise

    def get_by_request_id(self, request_id: str) -> ChatMessage | None:
        """按请求唯一标识查询消息（工作流按 run_id 回写用）。"""
        stmt = select(ChatMessage).where(ChatMessage.request_id == request_id)
        return self.db.scalars(stmt).first()

    def update_response(
        self,
        message: ChatMessage,
        *,
        response_text: str,
        response_payload: dict | None = None,
    ) -> ChatMessage:
        """更新 AI 回复正文与结构化数据，自带事务。"""
        try:
            message.response_text = response_text
            message.response_payload = response_payload
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception:
            self.db.rollback()
            raise
