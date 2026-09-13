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
    # 40101 预留给框架级未授权（路由处理器中 Starlette 原生 401 统一映射）
    UNAUTHORIZED = 40101
    # 登录凭证错误：用户名或密码不正确（不区分具体哪一项，避免用户名被枚举）
    INVALID_CREDENTIALS = 40103
    # 访问令牌无效或已过期：前端收到后应使用刷新令牌静默换新并重试原请求
    ACCESS_TOKEN_INVALID = 40104
    # 刷新令牌无效或已过期：前端无法静默续期，应跳转重新登录
    REFRESH_TOKEN_INVALID = 40105

    # 通用请求错误 400xx
    USER_ALREADY_EXISTS = 40001
    WEAK_PASSWORD = 40002
    # 文件上传相关
    FILE_TYPE_NOT_ALLOWED = 40003  # 文件类型不在允许列表
    FILE_TOO_LARGE = 40004  # 文件大小超过上限
    FILE_EMPTY = 40005  # 上传文件为空

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
    ResponseCode.INVALID_CREDENTIALS: "用户名或密码错误",
    ResponseCode.ACCESS_TOKEN_INVALID: "访问令牌无效或已过期",
    ResponseCode.REFRESH_TOKEN_INVALID: "刷新令牌无效或已过期",
    ResponseCode.PARAM_INVALID: "请求参数校验失败",
    ResponseCode.USER_ALREADY_EXISTS: "用户名已存在",
    ResponseCode.WEAK_PASSWORD: "密码强度不足",
    ResponseCode.FILE_TYPE_NOT_ALLOWED: "不支持的文件类型",
    ResponseCode.FILE_TOO_LARGE: "上传文件大小超出限制",
    ResponseCode.FILE_EMPTY: "上传文件不能为空",
    ResponseCode.USER_NOT_FOUND: "用户不存在",
    ResponseCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
    ResponseCode.SYSTEM_ERROR: "系统繁忙，请稍后再试",
    ResponseCode.HEALTH_CHECK_FAILED: "服务异常：数据库不可用",
}
