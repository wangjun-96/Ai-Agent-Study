"""提示词模板 DAO：封装 prompt_templates 表的全部数据库操作。

设计要点：
1. 版本按 (agent_name, scene) 分组独立递增；
2. 生效版本切换（回滚）在单个事务内完成：同组全部置 0 → 目标版本置 1；
3. 公共模板 agent_name 为空，查询时用 IS NULL 语义匹配。
"""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import PromptTemplate


def _group_condition(agent_name: str | None, scene: str):
    """构造版本分组条件：agent_name 为空表示公共模板（IS NULL）。"""
    if agent_name is None:
        return (PromptTemplate.agent_name.is_(None)) & (PromptTemplate.scene == scene)
    return (PromptTemplate.agent_name == agent_name) & (PromptTemplate.scene == scene)


class PromptTemplateDao:
    """提示词模板数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, template_id: int) -> PromptTemplate | None:
        """按主键查询模板，不存在返回 None。"""
        return self.db.get(PromptTemplate, template_id)

    def get_active(
        self, agent_name: str | None, scene: str
    ) -> PromptTemplate | None:
        """查询指定分组下当前生效版本（is_active=1），不存在返回 None。"""
        stmt = select(PromptTemplate).where(
            _group_condition(agent_name, scene),
            PromptTemplate.is_active == 1,
        )
        return self.db.scalars(stmt).first()

    def list_active(self) -> list[PromptTemplate]:
        """查询全部生效版本（启动时批量加载到 Redis）。"""
        stmt = select(PromptTemplate).where(PromptTemplate.is_active == 1)
        return list(self.db.scalars(stmt))

    def list_by_group(
        self, agent_name: str | None, scene: str
    ) -> list[PromptTemplate]:
        """查询指定分组下的全部历史版本，按版本号倒序。"""
        stmt = (
            select(PromptTemplate)
            .where(_group_condition(agent_name, scene))
            .order_by(PromptTemplate.version.desc())
        )
        return list(self.db.scalars(stmt))

    def max_version(self, agent_name: str | None, scene: str) -> int:
        """查询指定分组下的最大版本号，无记录返回 0。"""
        stmt = select(func.max(PromptTemplate.version)).where(
            _group_condition(agent_name, scene)
        )
        return self.db.scalar(stmt) or 0

    def insert(self, template: PromptTemplate) -> PromptTemplate:
        """插入模板，自带事务。"""
        try:
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)
            return template
        except Exception:
            self.db.rollback()
            raise

    def activate(self, template: PromptTemplate) -> PromptTemplate:
        """一键回滚/切换生效版本：同组其余版本置 0，目标版本置 1，单事务完成。"""
        try:
            self.db.execute(
                update(PromptTemplate)
                .where(
                    _group_condition(template.agent_name, template.scene),
                    PromptTemplate.id != template.id,
                )
                .values(is_active=0)
            )
            template.is_active = 1
            self.db.commit()
            self.db.refresh(template)
            return template
        except Exception:
            self.db.rollback()
            raise
