"""自定义异常类：区分业务异常与系统异常。

- BusinessException：业务可预期的错误（用户不存在、用户名重复等），
  由业务层主动抛出，全局处理器捕获后返回中文提示。
- SystemException：系统级异常（数据库连接失败、第三方服务异常等），
  全局处理器捕获后记录完整堆栈，对外只返回通用提示，避免泄露内部细节。

状态码分两层：
- http_status：HTTP 协议层状态码（400/401/404/500），默认由业务码前三位推导。
- code：响应体业务状态码（如 40401），用于前端区分具体业务错误。
"""
from app.enums.response_code import ResponseCode, CODE_MESSAGES


def resolve_http_status(code: int) -> int:
    """由 5 位业务码推导 HTTP 状态码：取前三位（code // 100）。

    例：40001→400，40101→401，40401→404，50000→500。
    若推导结果不在标准错误区间 400-599，则兜底为 400。
    """
    http_status = code // 100
    return http_status if 400 <= http_status <= 599 else 400


class BusinessException(Exception):
    """业务异常：由业务层主动抛出，前端可直接展示 message。"""

    def __init__(
        self,
        code: ResponseCode | int,
        message: str | None = None,
        detail: str | None = None,
        http_status: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        # 若传入枚举，取其整数值；否则直接使用传入值
        self.code = int(code) if isinstance(code, ResponseCode) else code
        # 未显式传 message 时，从枚举映射表取默认中文提示
        self.message = message or (
            CODE_MESSAGES.get(ResponseCode(self.code))
            if self.code in [c.value for c in ResponseCode]
            else None
        ) or "业务处理失败"
        # detail 仅用于后端定位，不直接展示给前端
        self.detail = detail
        # HTTP 状态码：未显式指定时由业务码推导
        self.http_status = http_status or resolve_http_status(self.code)
        # 附加响应头（如限流场景的 Retry-After），由全局处理器透传
        self.headers = headers
        super().__init__(self.message)


class SystemException(Exception):
    """系统异常：非预期的内部错误，对外隐藏细节，内部记录堆栈。"""

    def __init__(
        self,
        code: ResponseCode | int = ResponseCode.SYSTEM_ERROR,
        message: str | None = None,
        detail: str | None = None,
        http_status: int = 500,
    ) -> None:
        self.code = int(code) if isinstance(code, ResponseCode) else code
        self.message = message or CODE_MESSAGES.get(ResponseCode.SYSTEM_ERROR, "系统繁忙，请稍后再试")
        self.detail = detail
        # 系统异常统一返回 HTTP 500
        self.http_status = http_status
        super().__init__(self.message)
