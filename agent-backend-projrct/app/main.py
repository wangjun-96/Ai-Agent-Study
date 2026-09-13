"""FastAPI 应用入口：初始化日志、创建应用实例、注册全局异常处理器、挂载路由。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import register_exception_handlers, settings, setup_logging
from app.core.logger import get_logger
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.v1 import users

# 初始化日志（控制台 + 按天滚动文件 + 错误文件，级别随环境配置）
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动/关闭时记录关键日志，便于留痕排障。"""
    logger.info(
        "应用启动 env={} log_level={} sql_echo={}",
        settings.APP_ENV,
        settings.LOG_LEVEL,
        settings.SQL_ECHO,
    )
    yield
    logger.info("应用关闭 env={}", settings.APP_ENV)


app = FastAPI(
    title=settings.APP_NAME,
    description="基于 FastAPI + SQLAlchemy 2.0 + MySQL 的用户增删改查示例",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册全局异常处理器，所有接口异常统一捕获并返回标准化响应
register_exception_handlers(app)

# 健康检查路由：挂载在根路径，不添加前缀、不挂载鉴权，供监控系统直接调用
app.include_router(health_router)

# 认证路由：注册/登录/令牌刷新为匿名公开接口（白名单），/auth/me 内部挂载 JWT 鉴权
app.include_router(auth_router)

# 业务路由：统一前缀 /api/v1；各业务路由组内部通过 dependencies 统一挂载 JWT
# 登录鉴权，未登录请求统一返回 401，后续新增业务路由在组内自动纳入保护
app.include_router(users.router, prefix="/api/v1")


@app.get("/", summary="健康检查")
def root() -> dict:
    """根路径健康检查。"""
    return {"code": 0, "message": f"{settings.APP_NAME} 已启动", "data": None}
