"""统一响应模型：所有接口返回固定格式 code / message / data。

- code：业务状态码（见 app.enums.response_code.ResponseCode）
- message：中文提示，前端可直接展示
- data：业务数据，成功时返回，失败时为 null
- detail：可选，调试详情，仅非成功时返回，便于后端定位
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """通用统一响应体。"""
    code: int = Field(..., description="业务状态码，0 表示成功")
    message: str = Field(..., description="中文提示信息")
    data: Any | None = Field(default=None, description="业务数据，失败时为 null")
    # exclude=True：经 response_model 序列化的成功响应不输出该字段；
    # OpenAPI schema 中仍保留，错误响应由全局处理器直接构造 dict，不受影响
    detail: Any | None = Field(
        default=None, description="调试详情，仅失败时返回", exclude=True
    )


def success(data: Any = None, message: str = "操作成功") -> dict:
    """构造成功响应体。"""
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, detail: Any | None = None) -> dict:
    """构造失败响应体。"""
    body: dict[str, Any] = {"code": code, "message": message, "data": None}
    if detail is not None:
        body["detail"] = detail
    return body
