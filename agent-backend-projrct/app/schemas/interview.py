"""校验层：面试记录相关的响应模型。

- InterviewResponse：面试详情响应，包含 qa_object（一问一答对象）。
"""
from pydantic import BaseModel, ConfigDict, Field

from app.enums.interview_status import InterviewStatus


class InterviewResponse(BaseModel):
    """面试记录响应模型。"""

    id: int = Field(..., description="面试记录ID")
    session_id: int = Field(..., description="所属会话ID")
    message_id: int = Field(..., description="入口消息ID")
    user_id: int = Field(..., description="所属用户ID")
    qa_object: list[dict] = Field(
        ...,
        description="一问一答对象列表，每项包含 id/question/answer/created_at 等字段"
    )
    interview_duration: int = Field(..., description="累计面试时长（秒）")
    status: InterviewStatus = Field(..., description="面试状态：0=进行中，1=已完成，2=异常终止")
    create_at: int = Field(..., description="面试开始时间（Unix秒）")
    update_at: int = Field(..., description="更新面试时间（Unix秒）")

    model_config = ConfigDict(from_attributes=True)
