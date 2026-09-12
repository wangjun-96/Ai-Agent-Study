"""测试夹具配置：使用 SQLite 内存数据库隔离测试，覆写依赖注入。

测试策略：
1. 用 SQLite 内存数据库替代 MySQL，冒烟测试不依赖外部数据库服务。
2. 通过 FastAPI dependency_overrides 覆写 get_db 与鉴权依赖，无需真实凭证。
3. 通过 starlette TestClient（基于 httpx）同步调用 ASGI 应用，无需启动 uvicorn。
4. 每个用例执行后清理表数据，保证用例间互不影响。
"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 tests 包能 import app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.core.rate_limit import register_rate_limiter
from app.db.base import Base
from app.db.database import get_db
from app.db.models import User  # noqa: F401  # 触发模型注册，确保建表
from app.main import app
from app.security import verify_api_key

# ---------------------------------------------------------------------------
# SQLite 内存数据库引擎与 Session 工厂
# ---------------------------------------------------------------------------

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # 内存数据库必须用静态连接池，所有 Session 共享同一连接
)
_TestSessionLocal = sessionmaker(
    bind=_test_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _override_get_db():
    """覆写 get_db 依赖：测试环境使用 SQLite 内存数据库。"""
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _override_verify_api_key():
    """覆写鉴权依赖：测试环境跳过 X-API-Key 校验。"""
    return None


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    """测试会话开始时创建所有表，结束时销毁。"""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def client():
    """提供基于 httpx 的测试客户端，通过 TestClient 同步调用 FastAPI 应用。

    TestClient 内部基于 httpx，无需启动 uvicorn，依赖覆写在 yield 前注入，
    用例结束后清理，避免影响其他测试。
    """
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[verify_api_key] = _override_verify_api_key
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session():
    """直接提供测试库 Session，供用例绕过接口校验落库数据（如密码哈希存储）。"""
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _clean_tables():
    """每个用例执行前后清理表数据并重置限流器，保证用例间状态隔离。"""
    register_rate_limiter.reset()
    yield
    with _TestSessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    register_rate_limiter.reset()
