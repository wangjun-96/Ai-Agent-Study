"""Alembic 迁移环境：自动检测 app.db.models 中的表结构变更。

设计要点：
1. 连接串从 app/db/database.py 的 settings 注入，禁止在 alembic.ini 中硬编码。
2. 通过导入 app.db.models，使 Base.metadata 包含全部表定义，实现自动检测。
3. compare_type=True：检测列类型变更（如 String(50) -> String(100)），避免漏迁移。
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection

# 将项目根目录加入 sys.path，便于 alembic 直接以 `alembic` 命令运行时导入 app 包
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.db.base import Base  # noqa: E402
from app.db.database import engine, settings  # noqa: E402
from app.db import models  # noqa: E402,F401  # 触发模型注册到 Base.metadata

# Alembic 配置对象
config = context.config

# 从项目 settings 注入连接串，避免在 alembic.ini 中硬编码
config.set_main_option("sqlalchemy.url", settings.MYSQL_URL)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 迁移目标元数据：所有 ORM 模型表定义
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL，不连接数据库。

    适用于 CI/CD 环境预先生成迁移 SQL，再由 DBA 执行。
    """
    context.configure(
        url=settings.MYSQL_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库执行迁移。

    复用项目自身的 engine，避免在 alembic.ini 中重复配置连接池参数。
    """
    connectable = engine

    with connectable.connect() as connection:  # type: Connection
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
