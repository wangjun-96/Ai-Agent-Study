"""校验层：用户画像的请求/响应模型。"""
from pydantic import BaseModel, Field


class UserProfileUpsert(BaseModel):
    """用户画像新增/更新入参：全部字段可选，未传字段保持原值。"""

    target_job: str | None = Field(None, max_length=128, description="目标岗位")
    years_experience: str | None = Field(None, max_length=64, description="工作经验")
    target_level: str | None = Field(None, max_length=64, description="目标等级")
    target_skills: list[str] | None = Field(None, description="已掌握技能")
    weak_topics: list[str] | None = Field(None, description="薄弱点")
    learning_goal: str | None = Field(None, max_length=255, description="学习目标")
    learning_style: str | None = Field(None, max_length=128, description="学习风格/偏好")
    interview_focus: list[str] | None = Field(None, description="面试关注方向")
    long_term_summary: str | None = Field(None, description="长期记忆摘要")


class UserProfileResponse(BaseModel):
    """用户画像响应模型。"""

    id: int = Field(..., description="画像ID")
    user_id: int = Field(..., description="用户ID")
    target_job: str | None = Field(None, description="目标岗位")
    years_experience: str | None = Field(None, description="工作经验")
    target_level: str | None = Field(None, description="目标等级")
    target_skills: list[str] | None = Field(None, description="已掌握技能")
    weak_topics: list[str] | None = Field(None, description="薄弱点")
    learning_goal: str | None = Field(None, description="学习目标")
    learning_style: str | None = Field(None, description="学习风格/偏好")
    interview_focus: list[str] | None = Field(None, description="面试关注方向")
    long_term_summary: str | None = Field(None, description="长期记忆摘要")
    created_at: int = Field(..., description="创建时间（Unix秒）")
