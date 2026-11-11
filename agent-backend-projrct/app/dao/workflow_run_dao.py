"""工作流运行记录 DAO：封装 workflow_runs 表的全部数据库操作。

设计要点：
1. 写操作统一加事务，失败自动回滚；
2. run_id 与 LangGraph thread_id 一致，按 run_id 定位运行记录；
3. 禁止裸写原生 SQL 字符串拼接，统一使用 SQLAlchemy 2.0 语法。
"""
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401
from app.db.models import WorkflowRun


class WorkflowRunDao:
    """工作流运行记录数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def insert(self, run: WorkflowRun) -> WorkflowRun:
        """插入运行记录，自带事务，失败自动回滚。"""
        try:
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception:
            self.db.rollback()
            raise

    def get_by_run_id(self, run_id: str) -> WorkflowRun | None:
        """按工作流运行 ID 查询，不存在返回 None。"""
        stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        return self.db.scalars(stmt).first()

    def update_status(
        self,
        run: WorkflowRun,
        status: str,
        *,
        state_json: dict | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> WorkflowRun:
        """更新运行状态与业务快照，自带事务。

        :param run: 待更新的运行记录
        :param status: 新状态
        :param state_json: 业务状态快照，传 None 表示不覆盖原快照
        :param error_message: 失败原因，传 None 表示不写入
        :param completed: 是否标记完成，True 时写入完成时间
        """
        try:
            run.status = status
            run.updated_at = int(time.time())
            if state_json is not None:
                run.state_json = state_json
            if error_message is not None:
                run.error_message = error_message
            if completed:
                run.completed_at = int(time.time())
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception:
            self.db.rollback()
            raise
