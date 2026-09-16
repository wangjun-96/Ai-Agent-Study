"""资源 DAO：封装 resources 表的全部数据库操作。

设计要点：
1. 写操作（insert/delete）统一加事务，失败自动回滚，避免脏数据；
2. DAO 只负责持久化，业务校验（MD5 去重、场景分流）在 Service 层完成；
3. 禁止裸写原生 SQL 字符串拼接，统一使用 SQLAlchemy 2.0 select 语法。
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401  # 触发模型注册，便于类型解析
from app.db.models import Resource


class ResourceDao:
    """资源数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def insert(self, resource: Resource) -> Resource:
        """插入资源元数据，自带事务，失败自动回滚。

        并发下命中 uk_file_hash_user_id 唯一键时抛出 IntegrityError，
        由 Service 层捕获并转成业务错误（数据库兜底去重）。
        """
        try:
            self.db.add(resource)
            self.db.commit()
            # 回填自增 id、create_time 等服务端默认值
            self.db.refresh(resource)
            return resource
        except Exception:
            self.db.rollback()
            raise

    def get_by_hash(self, file_hash: str, user_id: int) -> Resource | None:
        """按 MD5 + 用户 ID 查询（用户级去重预查），不存在返回 None。"""
        stmt = select(Resource).where(
            Resource.file_hash == file_hash,
            Resource.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def list_expired(self, now: datetime) -> list[Resource]:
        """查询 expire_time 已到期且非空的全部资源记录。"""
        stmt = (
            select(Resource)
            .where(Resource.expire_time.is_not(None))
            .where(Resource.expire_time <= now)
        )
        return list(self.db.scalars(stmt))

    def delete(self, resource: Resource) -> None:
        """删除资源元数据（物理删除，过期清理专用），自带事务。"""
        try:
            self.db.delete(resource)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
