"""全局异常处理器：统一捕获异常并返回标准化响应体。

状态码采用双层设计：
- HTTP 状态码：按真实语义返回（400/401/404/422/500）
- 响应体 code：5 位业务码（如 40401），前三位与 HTTP 状态码对齐，后两位做业务细分

处理顺序：
1. BusinessException → 业务错误（HTTP 状态由业务码推导），记录 warn 日志
2. SystemException   → 系统错误（HTTP 500），记录 error 日志（含堆栈）
3. HTTPException     → 兼容 FastAPI 原生鉴权异常（HTTP 401 等），转为统一响应
4. RequestValidationError → Pydantic 参数校验失败（HTTP 422）
5. Exception         → 兜底（HTTP 500），记录完整堆栈，对外返回通用系统错误

所有接口无需单独 try-except，异常由本模块统一处理。
"""
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
# 注册 Starlette 原生 HTTPException：路由未匹配（404）、方法不允许（405）
# 等框架级错误抛的是该父类，fastapi.HTTPException 是其子类，注册父类可一并捕获
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import BusinessException, SystemException
from app.core.logger import get_logger
from app.core.responses import fail
from app.enums.response_code import ResponseCode

logger = get_logger("handlers")

# Pydantic 校验错误类型 → 前端可读中文文案
VALIDATION_MESSAGE_MAP: dict[str, str] = {
    "missing": "该字段为必填项",
    "string_too_short": "字段长度不能小于限制值",
    "string_too_long": "字段长度超过限制值",
    "string_type": "字段类型必须为字符串",
    "int_parsing": "字段必须为整数",
    "int_type": "字段必须为整数",
    "float_parsing": "字段必须为浮点数",
    "float_type": "字段必须为浮点数",
    "bool_parsing": "字段必须为布尔值",
    "bool_type": "字段必须为布尔值",
    "greater_than": "字段必须大于限制值",
    "greater_than_equal": "字段必须大于等于限制值",
    "less_than": "字段必须小于限制值",
    "less_than_equal": "字段必须小于等于限制值",
    "value_error": "字段值不合法",
    "json_decode": "请求体不是合法的 JSON",
    "json_invalid": "请求体不是合法的 JSON",
    "model_type": "请求体格式不正确",
}


def _json_error_response(
    *,
    code: int,
    message: str,
    http_status: int,
    detail: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """统一错误响应出口：把标准响应体包装为 JSONResponse。

    HTTP 状态码按真实语义返回（400/401/404/422/500），
    业务细分错误码放在响应体 code 字段中；
    headers 用于透传 Retry-After 等标准响应头。
    """
    return JSONResponse(
        status_code=http_status, content=fail(code, message, detail), headers=headers
    )


def _build_detail(request: Request, detail: Any = None) -> dict[str, Any]:
    """将请求基础信息注入 detail，便于前端快速定位出错接口。"""
    base_detail: dict[str, Any] = {
        "path": request.url.path,
        "method": request.method,
        # QueryParams 需显式转 dict，否则无法被 JSON 序列化
        "query_params": dict(request.query_params),
    }
    if detail is None:
        return base_detail
    if isinstance(detail, dict):
        return {**base_detail, **detail}
    # 字符串等非 dict 详情统一放到 reason 字段，避免被丢弃
    return {**base_detail, "reason": str(detail)}


def _build_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """将 Pydantic 校验错误转换为前端友好的中文结构。"""
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        error_type = str(error.get("type", "validation_error"))
        # 去掉 loc 中的 body/query/path 定位前缀及行号（非法 JSON 时 loc 为行号），只保留字段名
        location = [
            str(item)
            for item in error.get("loc", [])
            if item not in ("body", "query", "path") and not str(item).isdigit()
        ]
        field = ".".join(location) if location else "unknown"
        mapped = VALIDATION_MESSAGE_MAP.get(error_type, "参数格式不正确")
        errors.append(
            {
                "field": field,
                "message": f"字段【{field}】{mapped}" if field != "unknown" else mapped,
                "type": error_type,
            }
        )
    return errors


def register_exception_handlers(app: FastAPI) -> None:
    """在应用入口注册所有全局异常处理器。"""

    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
        """业务异常：前端中文可读，记录 warn 日志（含请求定位信息，便于排障）。"""
        detail = _build_detail(request, exc.detail)
        logger.warning(
            "[业务异常] code={} message={} detail={} path={} method={}",
            exc.code, exc.message, exc.detail, request.url.path, request.method,
        )
        return _json_error_response(
            code=exc.code, message=exc.message, detail=detail,
            http_status=exc.http_status, headers=exc.headers,
        )

    @app.exception_handler(SystemException)
    async def system_exception_handler(request: Request, exc: SystemException) -> JSONResponse:
        """系统异常：对外隐藏内部细节，记录 error 日志（含请求定位与完整堆栈）。"""
        logger.error(
            "[系统异常] code={} message={} detail={} path={} method={}\n{}",
            exc.code, exc.message, exc.detail, request.url.path, request.method,
            traceback.format_exc(),
        )
        # 仅回传请求定位信息，exc.detail 只进日志，不对外暴露
        detail = _build_detail(request)
        return _json_error_response(
            code=exc.code, message=exc.message, detail=detail, http_status=exc.http_status
        )

    # 框架默认英文提示中文化（路由不存在、方法不允许等）
    _FRAMEWORK_MESSAGES = {
        404: "请求的资源不存在",
        405: "请求方法不被允许",
        403: "拒绝访问",
    }

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """处理框架/FastAPI 原生 HTTPException（鉴权 401、路由 404、405 等）。"""
        # detail 为业务自定义中文时直接使用；框架默认英文（Not Found 等）则中文化
        if isinstance(exc.detail, str) and exc.detail not in ("Not Found", "Method Not Allowed", "Forbidden"):
            message = exc.detail
        else:
            message = _FRAMEWORK_MESSAGES.get(exc.status_code, "请求处理失败")
        logger.warning("[HTTP异常] status={} message={}", exc.status_code, message)
        # 401 映射为未授权业务码，其他直接沿用 HTTP 状态码作为 code
        code = ResponseCode.UNAUTHORIZED.value if exc.status_code == 401 else exc.status_code
        detail = _build_detail(request)
        return _json_error_response(
            code=code, message=message, detail=detail, http_status=exc.status_code
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Pydantic 参数校验失败：返回中文可读错误及字段级明细。"""
        errors = _build_validation_errors(exc)
        first_msg = errors[0]["message"] if errors else "参数格式不正确"
        logger.warning("[参数校验失败] path={} errors={}", request.url.path, errors)
        detail = _build_detail(request, {"errors": errors})
        return _json_error_response(
            code=ResponseCode.PARAM_INVALID.value,
            message=first_msg,
            detail=detail,
            http_status=422,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """兜底异常：完整堆栈只记录日志，对外仅返回通用系统错误与请求定位信息。"""
        logger.error("[未捕获异常] {}\n{}", exc, traceback.format_exc())
        detail = _build_detail(request)
        return _json_error_response(
            code=ResponseCode.SYSTEM_ERROR.value,
            message="系统繁忙，请稍后再试",
            detail=detail,
            http_status=500,
        )
