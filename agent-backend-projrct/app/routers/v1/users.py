"""路由层：用户增删改查接口入口。

入口仅做参数接收、路由分发，不堆砌核心业务逻辑。
所有入参使用 Pydantic 模型校验，响应统一包装为 ApiResponse（code/message/data）。
异常由全局异常处理器统一捕获，无需在接口内 try-except。
"""
from fastapi import APIRouter, Depends, status

from app.core import success
from app.routers.v1.deps import get_user_service
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.security import verify_api_key
from app.services.user_service import UserService

router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
    # 统一挂载接口鉴权依赖，所有用户接口均校验 X-API-Key
    dependencies=[Depends(verify_api_key)],
)


@router.post("/", summary="创建用户", status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service),
) -> dict:
    """创建新用户，密码会做哈希加密后存储。"""
    user = service.create_user(user_in)
    return success(UserResponse.model_validate(user).model_dump(), "用户创建成功")


@router.get("/", summary="查询用户列表")
def list_users(service: UserService = Depends(get_user_service)) -> dict:
    """返回全部用户。"""
    users = [UserResponse.model_validate(u).model_dump() for u in service.list_users()]
    return success(users)


@router.get("/{user_id}", summary="查询单个用户")
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> dict:
    """按 id 查询用户详情。"""
    user = service.get_user(user_id)
    return success(UserResponse.model_validate(user).model_dump())


@router.put("/{user_id}", summary="更新用户")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> dict:
    """更新用户信息，仅更新非空字段。"""
    user = service.update_user(user_id, user_in)
    return success(UserResponse.model_validate(user).model_dump(), "用户更新成功")


@router.delete("/{user_id}", summary="删除用户")
def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> dict:
    """按 id 删除用户。"""
    service.delete_user(user_id)
    return success(message="用户删除成功")
