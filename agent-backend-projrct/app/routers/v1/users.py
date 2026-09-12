"""路由层：用户增删改查接口入口。

入口仅做参数接收、路由分发，不堆砌核心业务逻辑。
所有入参使用 Pydantic 模型校验，响应统一包装为 ApiResponse（code/message/data）。
异常由全局异常处理器统一捕获，无需在接口内 try-except。

OpenAPI 文档约定：
- 401（X-API-Key 鉴权失败）与 422（参数校验失败）为全路由公共错误，
  在 router 级 responses 统一声明，自动合并进每个接口；
- 400/404 等接口级错误在各接口 responses 中分别声明；
- 成功响应通过 response_model 声明统一响应体结构，detail 字段仅失败时出现。
"""
from fastapi import APIRouter, Depends, status

from app.core import success
from app.core.responses import ApiResponse
from app.routers.v1.deps import get_user_service
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.security import verify_api_key
from app.services.user_service import UserService

# 公共错误响应文档：422 参数校验失败，各接口复用，统一为标准响应体结构
_VALIDATION_ERROR_DOC = {
    "model": ApiResponse,
    "description": "请求参数校验失败(42200)，detail 中返回字段级错误明细",
}

router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
    # 统一挂载接口鉴权依赖，所有用户接口均校验 X-API-Key
    dependencies=[Depends(verify_api_key)],
    # router 级公共错误响应，自动合并进本路由下每个接口的 OpenAPI 文档
    responses={
        401: {
            "model": ApiResponse,
            "description": "未授权：无效或缺失的 X-API-Key(40101)",
        },
        422: _VALIDATION_ERROR_DOC,
    },
)


@router.post(
    "/",
    summary="创建用户",
    description="管理端创建用户：校验用户名唯一性，密码经 bcrypt 哈希后入库，响应不返回密码。",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserResponse],
    responses={
        400: {"model": ApiResponse, "description": "用户名已存在(40001)"},
    },
)
def create_user(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service),
) -> dict:
    """创建新用户，密码会做哈希加密后存储。"""
    user = service.create_user(user_in)
    return success(UserResponse.model_validate(user).model_dump(), "用户创建成功")


@router.get(
    "/",
    summary="查询用户列表",
    description="返回全部用户（按 id 升序），列表项不包含密码字段。",
    response_model=ApiResponse[list[UserResponse]],
)
def list_users(service: UserService = Depends(get_user_service)) -> dict:
    """返回全部用户。"""
    users = [UserResponse.model_validate(u).model_dump() for u in service.list_users()]
    return success(users)


@router.get(
    "/{user_id}",
    summary="查询单个用户",
    description="按用户 id 查询详情，用户不存在时返回 404。",
    response_model=ApiResponse[UserResponse],
    responses={
        404: {"model": ApiResponse, "description": "用户不存在(40401)"},
    },
)
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> dict:
    """按 id 查询用户详情。"""
    user = service.get_user(user_id)
    return success(UserResponse.model_validate(user).model_dump())


@router.put(
    "/{user_id}",
    summary="更新用户",
    description="更新用户信息，仅更新非空字段；用户名变更再次校验唯一性，密码变更重新哈希。",
    response_model=ApiResponse[UserResponse],
    responses={
        400: {"model": ApiResponse, "description": "用户名已存在(40001)"},
        404: {"model": ApiResponse, "description": "用户不存在(40401)"},
    },
)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> dict:
    """更新用户信息，仅更新非空字段。"""
    user = service.update_user(user_id, user_in)
    return success(UserResponse.model_validate(user).model_dump(), "用户更新成功")


@router.delete(
    "/{user_id}",
    summary="删除用户",
    description="按用户 id 删除，用户不存在时返回 404；成功响应 data 为 null。",
    response_model=ApiResponse,
    responses={
        404: {"model": ApiResponse, "description": "用户不存在(40401)"},
    },
)
def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> dict:
    """按 id 删除用户。"""
    service.delete_user(user_id)
    return success(message="用户删除成功")
