"""路由层：通用文件上传接口入口。

- 路由级统一挂载 JWT 鉴权依赖，所有接口必须携带有效访问令牌（登录后可访问）；
- 入口仅接收 multipart 表单（file + storage_scene + upload_purpose）并分发到
  MinioUploadService，MD5 去重、MinIO 上传、场景分流、头像回写均在业务层完成；
- 异常由全局异常处理器统一捕获，接口内不写 try-except。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core import success
from app.core.responses import ApiResponse
from app.db.models import User
from app.routers.v1.deps import (
    get_current_user,
    get_upload_service_minio,
)
from app.schemas.file import ResourceUploadResult
from app.services.upload_service_minio import MinioUploadService
from app.enums.storage_scene import StorageScene
from app.enums.upload_purpose import UploadPurpose

router = APIRouter(
    prefix="/files",
    tags=["文件管理"],
    # 统一挂载 JWT 登录鉴权：未登录/令牌过期或伪造统一返回 401(40104)
    dependencies=[Depends(get_current_user)],
    responses={
        401: {
            "model": ApiResponse,
            "description": "未授权：缺失/过期/伪造访问令牌(40104)，需登录后上传",
        },
    },
)


@router.post(
    "/upload",
    summary="通用文件上传（MinIO 对象存储）",
    description=(
        "需登录后调用（请求头携带 `Authorization: Bearer <access_token>`），"
        "以 multipart/form-data 上传单个文件（表单字段名 `file`）。\n\n"
        "- 自动识别资源类型：**文件**（0）/**图片**（1）/**音频**（2）；\n"
        "- `storage_scene`：0=长过期（1 个月），1=短过期（2 小时），"
        "2=只提取内容不上传原文件；\n"
        "- `upload_purpose`：0=普通资源，1=头像；仅当 1 且资源为图片时"
        "更新 users.avatar；\n"
        "- 用户级去重：同一用户上传相同 MD5 文件直接复用，不重复存储；\n"
        "- 允许的图片：jpg/jpeg/png/gif/webp/bmp；音频：mp3/wav/m4a/aac/ogg/flac；"
        "文件：pdf/doc/docx/xls/xlsx/ppt/pptx/txt/md/csv；\n"
        "- 空文件返回 400(40005)，超 10MB 返回 400(40004)，"
        "类型不支持返回 400(40003)。"
    ),
    response_model=ApiResponse[ResourceUploadResult],
    responses={
        400: {
            "model": ApiResponse,
            "description": "文件为空(40005) / 超出大小限制(40004) / 类型不支持(40003)",
        },
        422: {
            "model": ApiResponse,
            "description": "缺少 file 字段 / storage_scene、upload_purpose 取值非法(42200)",
        },
    },
)
async def upload_file(
    file: UploadFile = File(..., description="待上传的单个文件"),
    storage_scene: Annotated[
        StorageScene,
        Form(description="存储场景：0=长过期(1个月)，1=短过期(2小时)，2=只提取内容"),
    ] = StorageScene.LONG,
    upload_purpose: Annotated[
        UploadPurpose,
        Form(description="上传用途：0=普通资源，1=用户头像"),
    ] = UploadPurpose.GENERAL,
    current_user: User = Depends(get_current_user),
    service: MinioUploadService = Depends(get_upload_service_minio),
) -> dict:
    """通用文件上传：MinIO 存原文件，MySQL 存元数据，按场景与用途分流。"""
    result = await service.upload(
        current_user, file, storage_scene, upload_purpose
    )
    message = "头像上传成功" if result.is_avatar else "文件上传成功"
    return success(result.model_dump(mode="json"), message)
