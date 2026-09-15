"""路由层：认证模块接口入口（注册、登录、令牌刷新、当前登录用户）。

- 注册 / 登录 / 刷新为匿名公开接口（鉴权白名单），供未登录用户调用；
- 注册接口为 multipart/form-data：username/password 文本字段 + 可选 avatar 头像文件，
  建号与头像保存一个请求完成，无需先登录再二次上传；
- /api/v1/auth/me 挂载 get_current_user 依赖，是 JWT 保护接口的标准用法；
- 注册接口统一挂载固定窗口限流依赖（IP 维度，默认 5 次/分钟），防止被刷；
- 入口仅做参数接收、路由分发，认证与令牌逻辑均在业务层 AuthService 完成。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core import success
from app.core.rate_limit import rate_limit_register
from app.core.responses import ApiResponse
from app.db.models import User
from app.routers.v1.deps import (
    get_current_user,
    get_file_service,
    get_user_service,
)
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["认证鉴权"])

# 公共错误响应文档：422 参数校验失败，各接口复用
_VALIDATION_ERROR_DOC = {
    "model": ApiResponse,
    "description": "请求参数校验失败(42200)，detail 中返回字段级错误明细",
}


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    file_service: FileService = Depends(get_file_service),
) -> AuthService:
    """构造认证业务服务，复用用户/文件服务依赖链（DAO/Session 注入）。"""
    return AuthService(user_service, file_service)


@router.post(
    "/register",
    summary="用户注册",
    description=(
        "外部用户自助注册，无需鉴权，请求体为 **multipart/form-data**。\n\n"
        "- 表单字段 `username`、`password` 为必填文本，`avatar` 为**可选**头像图片文件；\n"
        "- 头像仅接受图片（jpg/jpeg/png/gif/webp/bmp），随注册请求一并保存并写入 "
        "users.avatar，不传头像也可正常注册；\n"
        "- 弱密码校验：命中常见弱密码黑名单 / 必须同时包含字母和数字 / 禁止包含用户名；\n"
        "- 密码经 bcrypt 哈希后入库，响应不返回密码；\n"
        "- 接口限流：固定窗口按客户端 IP 计数，默认 5 次/分钟，超限返回 429。"
    ),
    status_code=status.HTTP_201_CREATED,
    # 声明统一响应体结构；detail 已在 ApiResponse 模型层标记 exclude，成功响应不输出
    response_model=ApiResponse[UserResponse],
    responses={
        400: {
            "model": ApiResponse,
            "description": (
                "业务失败：密码强度不足(40002) / 用户名已存在(40001) / "
                "头像类型不支持(40003) / 头像超 10MB(40004) / 头像为空文件(40005)"
            ),
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
async def register(
    # 表单文本字段：长度约束与 UserCreate（Pydantic 模型）保持一致
    username: Annotated[
        str,
        Form(min_length=2, max_length=50, description="用户名"),
    ],
    password: Annotated[
        str,
        Form(min_length=6, max_length=128, description="密码（明文传输，依赖 HTTPS 保护）"),
    ],
    # 可选头像：不传 / 传空字符串时为 None，仅创建文本账号；传文件时随注册一并保存
    avatar: Annotated[
        UploadFile | None,
        File(description="可选头像图片（jpg/jpeg/png/gif/webp/bmp，≤10MB）"),
    ] = None,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """用户注册：multipart 表单提交用户名、密码与可选头像。

    - 弱密码校验：黑名单 + 必须同时包含字母和数字 + 禁止包含用户名；
    - 密码经 bcrypt 哈希后入库，禁止明文存储；
    - 头像文件先校验后落盘，文件非法（类型/大小/空）时不会创建用户；
    - 用户名重复返回 400，头像不合法返回 400(40003~40005)，触发限流返回 429。
    """
    user = await service.register(username, password, avatar)
    return success(UserResponse.model_validate(user).model_dump(), "注册成功")


@router.post(
    "/login",
    summary="用户登录",
    description=(
        "用户名 + 密码登录，校验通过后签发 JWT 双令牌，无需鉴权。\n\n"
        "- access_token：访问令牌，放入请求头 `Authorization: Bearer <token>` 访问受保护接口；\n"
        "- refresh_token：刷新令牌，access_token 过期后调用 /api/v1/auth/refresh 静默换取新令牌；\n"
        "- 用户名不存在与密码错误统一返回 401(40103)，避免用户名被枚举。"
    ),
    response_model=ApiResponse[TokenResponse],
    responses={
        401: {"model": ApiResponse, "description": "用户名或密码错误(40103)"},
        422: _VALIDATION_ERROR_DOC,
    },
)
def login(
    login_in: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """用户登录：校验凭证并返回 Access/Refresh 双令牌。"""
    tokens = service.login(login_in.username, login_in.password)
    return success(tokens.model_dump(), "登录成功")


@router.post(
    "/refresh",
    summary="刷新访问令牌",
    description=(
        "访问令牌过期后，使用刷新令牌换取新的访问令牌，供前端静默续期。\n\n"
        "- 仅接受 type=refresh 的令牌，访问令牌调用本接口返回 401(40105)；\n"
        "- 刷新令牌过期/伪造/对应用户不存在时返回 401(40105)，需重新登录。"
    ),
    response_model=ApiResponse[AccessTokenResponse],
    responses={
        401: {"model": ApiResponse, "description": "刷新令牌无效或已过期(40105)"},
        422: _VALIDATION_ERROR_DOC,
    },
)
def refresh_token(
    refresh_in: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """刷新令牌：校验 Refresh Token 后下发新的 Access Token。"""
    tokens = service.refresh_access_token(refresh_in.refresh_token)
    return success(tokens.model_dump(), "令牌刷新成功")


@router.get(
    "/me",
    summary="获取当前登录用户",
    description=(
        "JWT 保护接口示例：携带有效访问令牌返回当前登录用户信息。\n\n"
        "- 请求头携带 `Authorization: Bearer <access_token>`；\n"
        "- 访问令牌缺失/过期/伪造返回 401(40104)，前端应静默刷新后重试。"
    ),
    response_model=ApiResponse[UserResponse],
    responses={
        401: {"model": ApiResponse, "description": "访问令牌无效或已过期(40104)"},
    },
)
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """获取当前登录用户信息（受 JWT 鉴权保护）。"""
    return success(UserResponse.model_validate(current_user).model_dump())
