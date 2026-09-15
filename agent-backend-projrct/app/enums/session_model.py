"""会话模式枚举：区分会话的业务场景，禁止代码内硬编码数字状态。

- STUDY    ：学习
- INTERVIEW：面试
- NOTE     ：笔记
"""
from enum import IntEnum


class SessionModel(IntEnum):
    """会话模式，写入 sessions.session_model 字段。"""

    STUDY = 0       # 学习
    INTERVIEW = 1  # 面试
    NOTE = 2       # 笔记
