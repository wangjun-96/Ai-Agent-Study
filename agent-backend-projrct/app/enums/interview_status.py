"""面试状态枚举：标识面试记录的生命周期状态，禁止代码内硬编码数字状态。

- IN_PROGRESS ：进行中
- COMPLETED   ：已完成
- ABNORMAL_END ：异常终止
"""
from enum import IntEnum


class InterviewStatus(IntEnum):
    """面试记录状态，写入 interviews.status 字段。"""

    IN_PROGRESS = 0   # 进行中
    COMPLETED = 1     # 已完成
    ABNORMAL_END = 2  # 异常终止
