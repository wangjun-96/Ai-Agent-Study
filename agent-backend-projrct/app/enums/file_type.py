"""文件类型枚举：通用上传接口按类型分流处理。

- IMAGE    ：图片，保存文件并回写用户 avatar 字段
- DOCUMENT ：文档，仅保存文件
"""
from enum import Enum


class FileType(str, Enum):
    """上传文件的业务分类。"""

    IMAGE = "image"
    DOCUMENT = "document"
