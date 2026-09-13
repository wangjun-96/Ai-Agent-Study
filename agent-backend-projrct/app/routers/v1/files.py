"""路由层：通用文件上传接口入口。

- 路由级统一挂载 JWT 鉴权依赖，所有接口必须携带有效访问令牌（登录后可访问）；
- 入口仅接收 multipart 表单文件并分发到 FileService，类型判断、MD5 去重落盘、
  图片回写头像等业务规则均在业务层完成；
- 异常由全局异常处理器统一捕获，接口内不写 try-except。
"""
from fastapi import APIRouter, Depends, File, UploadFile

from app.core import success
from app.core.responses import ApiResponse
from app.db.models import User
from app.routers.v1.deps import (
    get_current_user,
    get_file_service,
)
from app.schemas.file import FileUploadResult
from app.services.file_service import FileService

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
    summary="通用文件上传",
    description=(
        "需登录后调用（请求头携带 `Authorization: Bearer <access_token>`），"
        "以 multipart/form-data 上传单个文件（表单字段名 `file`）。\n\n"
        "- 接口自动判断文件类型：**图片**保存后更新当前用户 avatar 字段；"
        "**文档**仅保存文件；\n"
        "- 文件保存在按用户 ID 划分的目录 `uploads/{user_id}/` 中，"
        "文件名取文件内容的 MD5 哈希值，相同文件自动去重；\n"
        "- 允许的图片类型：jpg/jpeg/png/gif/webp/bmp；"
        "文档类型：pdf/doc/docx/xls/xlsx/ppt/pptx/txt/md/csv；\n"
        "- 空文件返回 400(40005)，文件超 10MB 返回 400(40004)，"
        "类型不支持返回 400(40003)。"
    ),
    response_model=ApiResponse[FileUploadResult],
    responses={
        400: {
            "model": ApiResponse,
            "description": "文件为空(40005) / 超出大小限制(40004) / 类型不支持(40003)",
        },
        422: {
            "model": ApiResponse,
            "description": "请求缺少 file 表单字段等参数校验失败(42200)",
        },
    },
)
async def upload_file(
    file: UploadFile = File(..., description="待上传的单个文件"),
    current_user: User = Depends(get_current_user),
    service: FileService = Depends(get_file_service),
) -> dict:
    """通用文件上传：图片更新头像，文档仅保存。"""
    result = await service.upload(current_user, file)
    message = "头像上传成功" if result.is_avatar else "文件上传成功"
    return success(result.model_dump(), message)
