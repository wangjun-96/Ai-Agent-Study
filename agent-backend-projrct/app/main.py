"""FastAPI 应用入口：初始化日志、创建应用实例、注册全局异常处理器、挂载路由。"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core import register_exception_handlers, settings, setup_logging
from app.core.logger import get_logger
from app.core.scheduler import daily_cleanup_loop
from app.routers.health import router as health_router
from app.routers.v1.api import api_router as v1_router

# 初始化日志（控制台 + 按天滚动文件 + 错误文件，级别随环境配置）
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时清理任务，关闭时取消。"""
    logger.info(
        "应用启动 env={} log_level={} sql_echo={}",
        settings.APP_ENV,
        settings.LOG_LEVEL,
        settings.SQL_ECHO,
    )
    # 每日 03:00 过期资源清理任务（睡眠等待，不到点不访问数据库/MinIO）
    cleanup_task = asyncio.create_task(daily_cleanup_loop())
    yield
    cleanup_task.cancel()
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

# v1 业务路由统一出口：auth/users/files/avatar 全部在 api.py 中聚合
# 新增 v1 模块只需在 app/routers/v1/api.py 追加 include_router，无需改动本文件
app.include_router(v1_router, prefix="/api/v1")

# 上传文件静态资源服务：/uploads/{user_id}/{md5}.ext
# StaticFiles 要求目录必须存在，启动时确保上传根目录已创建
settings.upload_root.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.UPLOAD_URL_PREFIX,
    StaticFiles(directory=str(settings.upload_root)),
    name="uploads",
)


@app.get("/", summary="健康检查")
def root() -> dict:
    """根路径健康检查。"""
    return {"code": 0, "message": f"{settings.APP_NAME} 已启动", "data": None}
