"""面试记录 DAO：封装 interviews 表的全部数据库操作。

设计要点：
1. 面试记录需按 interview_id + user_id 联合查询（越权访问控制）；
2. 级联删除由 SessionDao.delete_cascade 统一处理，本 DAO 不单独提供删除方法；
3. 禁止裸写原生 SQL 字符串拼接，统一使用 SQLAlchemy 2.0 语法。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401
from app.db.models import Interview


class InterviewDao:
    """面试记录数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_interview(self, interview_id: int) -> Interview | None:
        """按主键查询面试记录，不存在返回 None。"""
        return self.db.get(Interview, interview_id)

    def get_interview_by_user(
        self, interview_id: int, user_id: int
    ) -> Interview | None:
        """按面试 ID + 用户 ID 查询（越权访问控制），不存在返回 None。"""
        stmt = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def list_status_by_ids(self, interview_ids: list[int]) -> dict[int, int]:
        """按面试 ID 列表批量查询状态，返回 {interview_id: status} 映射。

        用于消息列表接口回填每条面试消息的 status 字段。
        """
        if not interview_ids:
            return {}
        stmt = select(Interview.id, Interview.status).where(
            Interview.id.in_(interview_ids)
        )
        return {row.id: row.status for row in self.db.execute(stmt).all()}
