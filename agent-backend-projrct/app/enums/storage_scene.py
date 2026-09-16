"""存储场景枚举：resources.storage_scene，决定过期策略与是否保留原文件。

- LONG          ：长过期时间（默认 1 个月）
- SHORT         ：短过期时间（默认 2 小时）
- EXTRACT_ONLY  ：只提取内容，不存储原文件/音频
"""
from enum import IntEnum


class StorageScene(IntEnum):
    """资源存储场景。"""

    LONG = 0
    SHORT = 1
    EXTRACT_ONLY = 2
