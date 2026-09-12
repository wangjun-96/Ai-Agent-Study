"""数据模型层：SQLAlchemy ORM 模型定义。

- 字段注释、索引、关联关系完整书写，禁止裸写原生 SQL 字符串拼接。
- 表结构变更统一通过 Alembic 迁移脚本管理，禁止手动改表。
- 所有模型继承自 Base，统一注册到 Base.metadata，供 Alembic 自动检测。
"""
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """用户表。

    字段：
    - id          ：自增主键
    - username    ：用户名，唯一非空，建立索引加速唯一性校验
    - password    ：密码哈希（bcrypt），不保留明文
    - create_time ：创建时间，由数据库 server_default=now() 自动填充
    """

    __tablename__ = "users"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID")
    # 用户名：唯一非空，加索引便于登录与唯一性校验
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="用户名"
    )
    # 密码哈希存储
    password: Mapped[str] = mapped_column(String(128), nullable=False, comment="密码哈希")
    # 创建时间：由数据库自动填充当前时间
    create_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
