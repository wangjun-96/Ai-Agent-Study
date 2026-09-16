"""资源类型枚举：resources.resource_type，统一管理文件、图片、音频。

- FILE   ：文件（文档等普通文件）
- IMAGE  ：图片
- AUDIO  ：音频
"""
from enum import IntEnum


class ResourceType(IntEnum):
    """上传资源的业务分类。"""

    FILE = 0
    IMAGE = 1
    AUDIO = 2
