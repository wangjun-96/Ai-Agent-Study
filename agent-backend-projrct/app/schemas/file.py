"""校验层：文件上传相关的响应模型。

- FileUploadResult：旧本地存储逻辑（file_service.py，教学保留）的响应模型；
- ResourceUploadResult：MinIO 对象存储运行逻辑（upload_service_minio.py）的响应模型，
  前端通过 resource_type / storage_scene / is_avatar 区分本次上传的处理结果。
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.enums.file_type import FileType
from app.enums.resource_type import ResourceType
from app.enums.storage_scene import StorageScene
from app.enums.upload_purpose import UploadPurpose


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


class ResourceUploadResult(BaseModel):
    """MinIO 资源上传成功响应数据。"""

    # 资源元数据 ID；storage_scene=2（只提取内容）时不落元数据，为 null
    resource_id: int | None = Field(None, description="资源元数据ID")
    # 资源类型：0=文件，1=图片，2=音频
    resource_type: ResourceType = Field(..., description="资源类型：0=文件，1=图片，2=音频")
    # 存储场景：0=长过期（1个月），1=短过期（2小时），2=只提取内容
    storage_scene: StorageScene = Field(..., description="存储场景：0/1/2")
    # 上传用途：0=普通资源，1=用户头像
    upload_purpose: UploadPurpose = Field(..., description="上传用途：0=普通资源，1=头像")
    # 客户端上传原始文件名
    file_name: str = Field(..., description="原始文件名")
    # 文件内容 MD5（去重核心字段）
    file_hash: str = Field(..., description="文件 MD5")
    # MinIO 对象存储路径：minio://{bucket}/{object_key}；只提取场景为空串
    storage_path: str = Field("", description="MinIO 存储路径")
    # 预签名下载 URL（前端临时访问私有桶对象）；只提取场景为 null
    url: str | None = Field(None, description="预签名下载 URL")
    # 资源过期时间；只提取场景为 null
    expire_time: datetime | None = Field(None, description="资源过期时间")
    # 本次上传是否更新了 users.avatar（upload_purpose=1 且图片为 true）
    is_avatar: bool = Field(False, description="是否更新用户头像")
    # 从文件中提取的完整文本：仅 storage_scene=2 且文本类文件时有值
    extracted_text: str | None = Field(None, description="提取的文件文本")
    # 文件 MIME 类型，取自上传请求
    content_type: str | None = Field(None, description="文件 MIME 类型")
    # 文件大小（字节）
    size: int = Field(..., description="文件大小（字节）")
    # 是否命中用户级去重（同一 MD5 此前已上传，直接复用元数据）
    duplicated: bool = Field(False, description="是否命中去重复用")
