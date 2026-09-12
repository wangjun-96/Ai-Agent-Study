"""数据库连接层：使用 SQLAlchemy 2.0 + MySQL，统一管理 Engine 与 Session。

- 连接串、SQL 回显开关统一从配置层（app.core.config.settings）读取，禁止硬编码。
- 提供同步 Session 工厂与 FastAPI 依赖注入，业务层通过依赖获取 Session。
- 数据库操作全部封装在 DAO 层，Service 不直接操作 Session、写 SQL 语句。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLAlchemy 引擎（同步）：
# - pool_pre_ping：连接前 ping 检查，避免使用被 MySQL 端 wait_timeout 断开的失效连接
# - pool_recycle：连接回收周期（秒），低于 MySQL 的 wait_timeout 默认值，避免长连接失效
# - echo：是否回显 SQL，由环境变量 SQL_ECHO 控制（仅开发排障时开启）
engine = create_engine(
    settings.MYSQL_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.SQL_ECHO,
)

# Session 工厂：所有 DAO 通过此工厂获取 Session
# - autoflush=False：禁止自动 flush，避免隐式触发 SQL，事务由业务显式控制
# - autocommit=False：事务显式提交，失败自动回滚，避免脏数据
# - expire_on_commit=False：commit 后对象属性不过期，避免 commit 后立即访问触发额外查询
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Session:
    """FastAPI 依赖：按请求生命周期管理 Session，请求结束自动关闭。

    用法：在路由/服务中通过 Depends(get_db) 注入 Session。
    业务异常时由全局异常处理器捕获，此处无需单独 try-except。
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
