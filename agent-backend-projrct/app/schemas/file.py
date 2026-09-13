"""校验层：文件上传相关的响应模型。

通用文件上传接口统一返回 FileUploadResult，前端通过 file_type 与 is_avatar
区分本次上传是图片（已更新头像）还是普通文档（仅保存）。
"""
from pydantic import BaseModel, Field

from app.enums.file_type import FileType


class FileUploadResult(BaseModel):
    """文件上传成功响应数据。"""

    # 文件可访问 URL（相对路径，走 /uploads 静态资源服务）
    url: str = Field(..., description="文件访问 URL")
    # 文件业务分类：image=图片（已更新头像），document=文档（仅保存）
    file_type: FileType = Field(..., description="文件类型：image / document")
    # 本次上传是否更新了当前用户头像（图片类型恒为 true）
    is_avatar: bool = Field(..., description="是否为头像图片")
    # 客户端上传时的原始文件名（仅展示用，不作为存储路径）
    original_name: str = Field(..., description="原始文件名")
    # 实际存储文件名：内容 MD5 + 扩展名，天然去重
    stored_name: str = Field(..., description="存储文件名（MD5）")
    # 文件 MIME 类型，取自上传请求
    content_type: str | None = Field(None, description="文件 MIME 类型")
    # 文件大小（字节）
    size: int = Field(..., description="文件大小（字节）")
