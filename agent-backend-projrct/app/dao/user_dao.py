"""用户 DAO：封装 users 表的全部数据库操作。

设计要点：
1. 所有写操作（insert/update/delete）统一加事务，失败自动回滚，避免脏数据。
2. DAO 只负责持久化，不包含业务校验逻辑（唯一性校验等在 Service 层完成）。
3. Service 通过构造函数注入 DAO 实例，DAO 通过构造函数注入 Session。
4. 禁止裸写原生 SQL 字符串拼接，统一使用 SQLAlchemy 2.0 select 语法。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.base import Base  # noqa: F401  # 触发模型注册，便于类型解析


class UserDao:
    """用户数据访问对象：每个请求一个实例，绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def insert_user(self, user: User) -> User:
        """插入一条用户记录，自带事务，失败自动回滚。

        :param user: 已构造好的 User 模型实例（密码应已哈希）
        :return: 持久化后的 user（含自增 id 与 create_time）
        """
        try:
            self.db.add(user)
            self.db.commit()
            # refresh 触发服务端默认值（如 create_time、自增 id）回填
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def get_user(self, user_id: int) -> User | None:
        """按主键查询单个用户，不存在返回 None。"""
        # 主键查询直接使用 get，命中 identity map，避免额外 SQL
        return self.db.get(User, user_id)

    def find_by_username(self, username: str) -> User | None:
        """按用户名查询用户（用于唯一性校验），不存在返回 None。"""
        stmt = select(User).where(User.username == username)
        return self.db.scalars(stmt).first()

    def list_users(self) -> list[User]:
        """返回全部用户记录，按 id 升序，保证分页/列表顺序稳定。"""
        stmt = select(User).order_by(User.id.asc())
        return list(self.db.scalars(stmt))

    def update_user(self, user: User, update_data: dict) -> User:
        """更新指定用户字段，自带事务，失败自动回滚。

        :param user: 已查询到的持久化 User 实例
        :param update_data: 待更新字段键值对（仅含需要变更的字段）
        :return: 更新后的 user
        """
        try:
            for key, value in update_data.items():
                setattr(user, key, value)
            self.db.commit()
            # 回填服务端可能变更的默认值
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def delete_user(self, user: User) -> None:
        """删除指定用户，自带事务，失败自动回滚。

        :param user: 已查询到的持久化 User 实例
        """
        try:
            self.db.delete(user)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
