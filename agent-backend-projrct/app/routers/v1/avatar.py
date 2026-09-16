"""路由层：头像公开代理接口。

头像通过 MinIO 私有桶存储，users.avatar 字段存的是 minio:// 存储路径而非
浏览器可直接访问的 URL。本路由提供 307 重定向代理：

    前端 <img src="/api/v1/avatar/{user_id}">
    → 后端查用户 avatar 字段
    → 解析 minio:// 存储路径
    → 生成预签名下载 URL
    → 307 重定向到 MinIO

接口为**公开访问**（无 JWT 鉴权），因为 <img> 标签无法携带 Authorization 头。
预签名 URL 有有效期（默认 2 小时），过期后浏览器再次请求本接口即可获取新 URL。
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core import BusinessException, settings
from app.core.responses import ApiResponse
from app.db.database import get_db
from app.enums.response_code import ResponseCode
from app.integrations.minio_client import MinioStorage, get_minio_storage
from app.services.user_service import UserService
from app.routers.v1.deps import get_user_service

router = APIRouter(
    prefix="/avatar",
    tags=["头像代理"],
    responses={
        404: {
            "model": ApiResponse,
            "description": "用户不存在(40401) / 用户未设置头像(40402)",
        },
    },
)


@router.get(
    "/{user_id}",
    summary="头像代理（307 重定向到 MinIO 预签名 URL）",
    description=(
        "公开接口，无需鉴权。前端直接用作 `<img src>` 地址：\n\n"
        "```html\n<img src=\"/api/v1/avatar/{user_id}\" />\n```\n\n"
        "- 后端查询 users.avatar 存储路径（minio://...）；\n"
        "- 生成 MinIO 预签名下载 URL（有效期默认 2 小时）；\n"
        "- 返回 307 重定向，浏览器自动跟随下载图片；\n"
        "- 用户不存在返回 404(40401)，未设置头像返回 404(40402)。"
    ),
    response_class=RedirectResponse,
)
def get_avatar(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    minio_storage: MinioStorage = Depends(get_minio_storage),
) -> RedirectResponse:
    """头像代理：查用户 → 解析存储路径 → 307 重定向到预签名 URL。"""
    # 查询用户，不存在抛 40401
    user = user_service.get_user(user_id)

    # 头像为空或格式非法，抛 40402
    if not user.avatar:
        raise BusinessException(
            ResponseCode.AVATAR_NOT_FOUND,
            detail=f"user_id={user_id}, avatar is empty",
        )

    url = minio_storage.presigned_url_from_path(
        user.avatar, settings.MINIO_PRESIGN_EXPIRY_SECONDS
    )
    if url is None:
        raise BusinessException(
            ResponseCode.AVATAR_NOT_FOUND,
            detail=f"user_id={user_id}, invalid storage_path={user.avatar}",
        )

    # 307 保持 GET 方法语义，浏览器缓存可正常工作
    return RedirectResponse(url=url, status_code=307)
