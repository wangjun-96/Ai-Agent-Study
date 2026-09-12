"""业务状态码枚举：统一管理接口返回码，禁止代码内硬编码数字状态。

码段约定：
- 0        ：成功
- 4xxxx    ：业务类错误，业务码前三位与 HTTP 状态码对齐
             （400xx 通用请求错误、401xx 鉴权、404xx 资源不存在、422xx 参数校验等）
- 5xxxx    ：系统类错误
"""
from enum import IntEnum


class ResponseCode(IntEnum):
    # 成功
    SUCCESS = 0

    # 鉴权相关 401xx
    UNAUTHORIZED = 40101
    INVALID_API_KEY = 40102

    # 通用请求错误 400xx
    USER_ALREADY_EXISTS = 40001
    WEAK_PASSWORD = 40002

    # 参数校验相关 422xx（与 HTTP 422 Unprocessable Entity 对齐）
    PARAM_INVALID = 42200

    # 资源不存在 404xx
    USER_NOT_FOUND = 40401

    # 限流相关 429xx（与 HTTP 429 Too Many Requests 对齐）
    RATE_LIMITED = 42901

    # 系统错误 5xxxx
    SYSTEM_ERROR = 50000
    # 健康检查 503xx（与 HTTP 503 Service Unavailable 对齐）
    HEALTH_CHECK_FAILED = 50300


# 状态码对应的中文提示，供异常类与响应体统一引用
CODE_MESSAGES: dict[ResponseCode, str] = {
    ResponseCode.SUCCESS: "操作成功",
    ResponseCode.UNAUTHORIZED: "未授权，禁止访问",
    ResponseCode.INVALID_API_KEY: "无效或缺失的 API Key",
    ResponseCode.PARAM_INVALID: "请求参数校验失败",
    ResponseCode.USER_ALREADY_EXISTS: "用户名已存在",
    ResponseCode.WEAK_PASSWORD: "密码强度不足",
    ResponseCode.USER_NOT_FOUND: "用户不存在",
    ResponseCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
    ResponseCode.SYSTEM_ERROR: "系统繁忙，请稍后再试",
    ResponseCode.HEALTH_CHECK_FAILED: "服务异常：数据库不可用",
}
