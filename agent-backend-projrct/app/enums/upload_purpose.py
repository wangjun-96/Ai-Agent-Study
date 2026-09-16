"""上传用途枚举：resources.update_purpose。

- GENERAL ：普通资源
- AVATAR  ：用户头像（仅图片类型时回写 users.avatar）
"""
from enum import IntEnum


class UploadPurpose(IntEnum):
    """资源上传用途。"""

    GENERAL = 0
    AVATAR = 1
