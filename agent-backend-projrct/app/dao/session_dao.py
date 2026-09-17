"""会话 DAO：封装 sessions 表的全部数据库操作。

设计要点：
1. 写操作统一加事务，失败自动回滚；
2. 级联删除（delete_cascade）在单个事务内完成：面试记录 → 消息 → 资源 → 会话，
   保证外键依赖顺序与原子性；
3. 禁止裸写原生 SQL 字符串拼接，统一使用 SQLAlchemy 2.0 语法。
"""
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401
from app.db.models import ChatMessage, Interview, Resource, Session as SessionModel


class SessionDao:
    """会话数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_session(self, session_id: int) -> SessionModel | None:
        """按主键查询会话，不存在返回 None。"""
        return self.db.get(SessionModel, session_id)

    def get_session_by_user(self, session_id: int, user_id: int) -> SessionModel | None:
        """按会话 ID + 用户 ID 查询（越权访问控制），不存在返回 None。"""
        stmt = select(SessionModel).where(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def count_by_user(
        self, user_id: int, session_model: int | None = None
    ) -> int:
        """统计指定用户的会话总数，可按 session_model 过滤。"""
        stmt = select(func.count()).select_from(SessionModel).where(
            SessionModel.user_id == user_id
        )
        if session_model is not None:
            stmt = stmt.where(SessionModel.session_model == session_model)
        return self.db.scalar(stmt) or 0

    def list_by_user(
        self,
        user_id: int,
        *,
        offset: int,
        limit: int,
        session_model: int | None = None,
    ) -> list[SessionModel]:
        """按用户分页查询会话列表，按创建时间倒序，可按 session_model 过滤。"""
        stmt = select(SessionModel).where(SessionModel.user_id == user_id)
        if session_model is not None:
            stmt = stmt.where(SessionModel.session_model == session_model)
        stmt = stmt.order_by(SessionModel.create_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt))

    def insert(self, session: SessionModel) -> SessionModel:
        """插入会话，自带事务。"""
        try:
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception:
            self.db.rollback()
            raise

    def update_session(self, session: SessionModel, update_data: dict) -> SessionModel:
        """更新会话字段（title / session_model），自带事务。"""
        try:
            for key, value in update_data.items():
                setattr(session, key, value)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception:
            self.db.rollback()
            raise

    def delete_cascade(self, session_id: int, resource_ids: list[int]) -> None:
        """级联删除会话及其全部关联数据，单事务保证原子性。

        删除顺序（满足外键依赖）：
        1. interviews（依赖 chat_messages.message_id 与 sessions.id）
        2. chat_messages（依赖 sessions.id）
        3. resources（按消息 segments 收集的 resource_ids 物理删除）
        4. sessions

        :param session_id: 待删除的会话 ID
        :param resource_ids: 从消息 segments 中收集的资源 ID 列表
        """
        try:
            # 1. 删除会话下的面试记录
            self.db.execute(
                delete(Interview).where(Interview.session_id == session_id)
            )
            # 2. 删除会话下的聊天消息
            self.db.execute(
                delete(ChatMessage).where(ChatMessage.session_id == session_id)
            )
            # 3. 删除关联资源元数据（MinIO 对象已由 Service 层提前删除）
            if resource_ids:
                self.db.execute(
                    delete(Resource).where(Resource.id.in_(resource_ids))
                )
            # 4. 删除会话本身
            self.db.execute(
                delete(SessionModel).where(SessionModel.id == session_id)
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
