"""消息选择模式枚举：区分消息的业务处理模式，禁止代码内硬编码数字状态。

- DEFAULT         ：默认
- KNOWLEDGE       ：知识精讲
- PRACTICE        ：刷题
- RESUME_OPTIMIZE ：简历优化
- MOCK_INTERVIEW  ：模拟面试
- INTERVIEW_REVIEW：面试复盘
"""
from enum import IntEnum


class SelectModel(IntEnum):
    """消息选择模式，写入 chat_messages.select_model 字段。"""

    DEFAULT = 0            # 默认
    KNOWLEDGE = 1          # 知识精讲
    PRACTICE = 2           # 刷题
    RESUME_OPTIMIZE = 3    # 简历优化
    MOCK_INTERVIEW = 4     # 模拟面试
    INTERVIEW_REVIEW = 5   # 面试复盘
