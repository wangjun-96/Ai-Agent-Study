"""路由层：认证模块接口入口（注册等公开接口）。

- 注册接口路径为 /auth/register，不挂载 X-API-Key 鉴权，供外部用户自助注册。
- 统一挂载固定窗口限流依赖（IP 维度，默认 5 次/分钟），防止注册接口被刷。
- 入口仅做参数接收、路由分发，弱密码校验与入库逻辑均在业务层完成。
"""
from fastapi import APIRouter, Depends, status

from app.core import success
from app.core.rate_limit import rate_limit_register
from app.core.responses import ApiResponse
from app.routers.v1.deps import get_user_service
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["认证鉴权"])


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    """构造认证业务服务，复用用户服务依赖链（DAO/Session 注入）。"""
    return AuthService(user_service)


@router.post(
    "/register",
    summary="用户注册",
    description=(
        "外部用户自助注册，无需 X-API-Key。\n\n"
        "- 弱密码校验：命中常见弱密码黑名单 / 必须同时包含字母和数字 / 禁止包含用户名；\n"
        "- 密码经 bcrypt 哈希后入库，响应不返回密码；\n"
        "- 接口限流：固定窗口按客户端 IP 计数，默认 5 次/分钟，超限返回 429。"
    ),
    status_code=status.HTTP_201_CREATED,
    # 声明统一响应体结构，exclude_none 保证成功响应不输出 detail: null，保持现有报文不变
    response_model=ApiResponse[UserResponse],
    response_model_exclude_none=True,
    responses={
        400: {
            "model": ApiResponse,
            "description": "业务失败：密码强度不足(40002) 或 用户名已存在(40001)",
        },
        422: {"model": ApiResponse, "description": "请求参数校验失败(42200)"},
        429: {
            "model": ApiResponse,
            "description": "触发限流(42901)：单 IP 5 次/分钟，响应头携带 Retry-After",
        },
    },
    # 接口限流：固定窗口 + IP 维度，默认 5 次/分钟，超限返回 429
    dependencies=[Depends(rate_limit_register)],
)
def register(
    user_in: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """用户注册。

    - 弱密码校验：黑名单 + 必须同时包含字母和数字 + 禁止包含用户名；
    - 密码经 bcrypt 哈希后入库，禁止明文存储；
    - 用户名重复返回 400，触发限流返回 429。
    """
    user = service.register(user_in)
    return success(UserResponse.model_validate(user).model_dump(), "注册成功")
