"""健康检查路由：校验服务存活及数据库连通性。

设计要点：
1. /health 接口不挂载鉴权依赖，供负载均衡、监控系统无凭证调用。
2. 服务存活：接口可响应即代表服务存活。
3. 数据库连通性：执行 SELECT 1 校验数据库是否可达，异常时返回 503。
4. 响应体保持统一格式 code/message/data，便于监控平台解析。
5. 异常原始信息（连接串、驱动报错等）只写入日志，不回传给调用方，
   避免敏感信息外泄；响应体只暴露健康的布尔状态。
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.db.database import get_db
from app.enums.response_code import ResponseCode

router = APIRouter(tags=["健康检查"])
logger = get_logger("health")


@router.get("/health", summary="健康检查")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """健康检查：校验服务存活及数据库连通性，异常返回 503。

    - 服务存活：接口能响应即代表服务正常。
    - 数据库连通性：执行 ``SELECT 1``，失败则标记为不健康并返回 503。
    - 异常详情仅写入日志，响应体只暴露 healthy/unhealthy 状态，
      避免数据库连接串、底层驱动报错等敏感信息外泄。
    """
    checks: dict[str, str] = {"service": "ok"}
    is_healthy = True

    # 数据库连通性校验：执行 SELECT 1，异常时标记不健康
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        # 异常原始信息只进日志，不进响应体，避免敏感信息外泄
        logger.error("[健康检查] 数据库连通性校验失败：{}", exc)
        checks["database"] = "fail"
        is_healthy = False

    if is_healthy:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": ResponseCode.SUCCESS,
                "message": "服务正常",
                "data": {
                    "status": "healthy",
                    "checks": checks,
                    "env": settings.APP_ENV,
                },
            },
        )

    # 数据库不可用：返回 503，监控平台可据此告警
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "code": ResponseCode.HEALTH_CHECK_FAILED,
            "message": "服务异常：数据库不可用",
            "data": {
                "status": "unhealthy",
                "checks": checks,
                "env": settings.APP_ENV,
            },
        },
    )
