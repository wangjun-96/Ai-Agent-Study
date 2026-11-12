"""FastAPI 应用入口：初始化日志、创建应用实例、注册全局异常处理器、挂载路由。"""
import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core import register_exception_handlers, settings, setup_logging
from app.core.logger import get_logger
from app.core.scheduler import daily_cleanup_loop
from app.dao.prompt_template_dao import PromptTemplateDao
from app.db.database import SessionLocal
from app.integrations.redis_client import get_redis_cache
from app.routers.health import router as health_router
from app.routers.v1.api import api_router as v1_router
from app.services.prompt_template_service import PromptTemplateManager
from app.services.semantic_intent_service import SemanticIntentClassifier

# Swagger UI 静态资源 CDN：
# - jsdelivr 在国内经常被强制关闭连接；
# - 优先使用国内镜像 npmmirror（https://registry.npmmirror.com），
#   该镜像同步 npm 包内容，路径格式为 /<包名>/<版本>/files/<文件相对路径>；
# - 如需完全离线，可下载 swagger-ui-dist@5 到项目 static/swagger-ui/ 后改为本地路径。
SWAGGER_JS_URL = "https://registry.npmmirror.com/swagger-ui-dist/5/files/swagger-ui-bundle.js"
SWAGGER_CSS_URL = "https://registry.npmmirror.com/swagger-ui-dist/5/files/swagger-ui.css"
# favicon 用 FastAPI 官方图（或改为 data URI 彻底离线）
SWAGGER_FAVICON_URL = "https://fastapi.tiangolo.com/img/favicon.png"
REDOC_JS_URL = "https://registry.npmmirror.com/redoc/latest/files/bundles/redoc.standalone.js"

# 初始化日志（控制台 + 按天滚动文件 + 错误文件，级别随环境配置）
setup_logging()
logger = get_logger("main")


def load_prompt_templates_to_redis() -> None:
    """启动加载：把生效的提示词模板批量写入 Redis 缓存。

    表尚未迁移或 Redis 不可用时只记录告警，不阻断应用启动。
    """
    db = SessionLocal()
    try:
        manager = PromptTemplateManager(PromptTemplateDao(db), get_redis_cache())
        manager.load_active_templates()
    except Exception as exc:  # noqa: BLE001 启动加载失败不阻断主流程
        logger.warning("提示词模板启动加载失败，已跳过 error={}", exc)
    finally:
        db.close()


def _warmup_semantic_model() -> None:
    """后台预热语义意图模型：下载/加载失败只记告警，不影响应用启动。"""
    try:
        SemanticIntentClassifier.get().warmup()
    except Exception as exc:  # noqa: BLE001 预热失败不阻断启动
        logger.warning("语义意图模型预热失败 error={}", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时清理任务与模板缓存加载，关闭时取消定时任务。"""
    logger.info(
        "应用启动 env={} log_level={} sql_echo={}",
        settings.APP_ENV,
        settings.LOG_LEVEL,
        settings.SQL_ECHO,
    )
    # 启动加载提示词模板到 Redis（失败自动降级，不影响服务可用性）
    load_prompt_templates_to_redis()
    # 后台线程预热语义意图模型：首次使用无需等待模型下载，不阻塞启动
    threading.Thread(
        target=_warmup_semantic_model, daemon=True, name="semantic-warmup"
    ).start()
    # 每日 03:00 过期资源清理任务（睡眠等待，不到点不访问数据库/MinIO）
    cleanup_task = asyncio.create_task(daily_cleanup_loop())
    yield
    cleanup_task.cancel()
    logger.info("应用关闭 env={}", settings.APP_ENV)


def _custom_openapi() -> dict:
    """自定义 OpenAPI schema：统一 info 字段，便于 Swagger UI 展示。"""
    schema = get_openapi(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            f"## {settings.APP_NAME}\n\n"
            "基于 **FastAPI + SQLAlchemy 2.0 + MySQL** 的 AI Agent 后端。\n\n"
            "### 核心能力\n"
            "- 三层流式聊天（模型层 / 提示词层 / 记忆层）\n"
            "- 提示词版本管理 + 公共/私有模板拼接 + Redis 缓存\n"
            "- 用户画像变量注入（目标岗位 / 技能 / 薄弱点）\n"
            "- RAG 文件向量化入库（PDF / DOCX / TXT / MD）+ 语义检索\n"
            "- 三层记忆：瞬时（DB 近 N 轮）/ 工作（Redis 滑动摘要）/ 长期（画像后台抽取）\n"
            "- LangGraph 学习测评工作流（interrupt + checkpoint + 评分 JSON）\n"
            "- 流程总控路由（关键词 + 语义意图）+ A2A 信封\n"
            "- MinIO 对象存储 + 过期清理定时任务\n\n"
            "### 基础信息\n"
            "- Swagger UI：`/docs`\n"
            "- ReDoc：`/redoc`\n"
            "- OpenAPI JSON：`/openapi.json`\n"
            "- 健康检查：`/health`\n"
        ),
        routes=app.routes,
    )
    # 统一 SecurityScheme：Bearer JWT
    schema.setdefault("components", {}).setdefault("securitySchemes", {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "请在登录后复制 Access Token 填入，格式：`Bearer <token>`",
        }
    })
    return schema


app = FastAPI(
    title=settings.APP_NAME,
    description="基于 FastAPI + SQLAlchemy 2.0 + MySQL 的 AI Agent 后端",
    version="1.0.0",
    lifespan=lifespan,
    # 关闭默认 docs/redoc，下面用 unpkg CDN 手动挂载（规避 jsdelivr 在国内不可达）
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)
app.openapi = _custom_openapi  # type: ignore[method-assign]


@app.get("/docs", include_in_schema=False, summary="Swagger UI")
def swagger_ui() -> "HTMLResponse":  # type: ignore[name-defined]
    """Swagger UI：使用 unpkg CDN 加载静态资源。"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - Swagger UI",
        swagger_js_url=SWAGGER_JS_URL,
        swagger_css_url=SWAGGER_CSS_URL,
        swagger_favicon_url=SWAGGER_FAVICON_URL,
        swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    )


@app.get("/redoc", include_in_schema=False, summary="ReDoc")
def redoc_ui() -> "HTMLResponse":  # type: ignore[name-defined]
    """ReDoc API 文档页：使用 unpkg CDN 加载静态资源。"""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - ReDoc",
        redoc_js_url=REDOC_JS_URL,
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


@app.get("/", include_in_schema=False, summary="根路径 → Swagger UI")
def root() -> RedirectResponse:
    """根路径重定向到 Swagger 文档页，方便调试。"""
    return RedirectResponse(url="/docs", status_code=302)
