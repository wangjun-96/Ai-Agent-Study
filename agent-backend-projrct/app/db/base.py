"""数据库基础层：SQLAlchemy 2.0 声明式基类。

所有 ORM 模型继承自 Base，统一管理 MetaData，
便于 Alembic 自动检测表结构变更（compare_type=True）。
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类，所有模型继承此类。"""
    
