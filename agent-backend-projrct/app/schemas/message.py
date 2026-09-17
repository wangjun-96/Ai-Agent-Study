"""校验层：聊天消息相关的响应模型。

核心语义（见 prompt.md L154-160）：
- request_text / response_text 为聊天正文主字段；
- request_segments / response_segments 只存附件段（file/image/audio），不存文本；
- 消息返回需包含 status 与 interview_id，供前端面试卡片逻辑使用。

Segment 结构约定：
{
    "type": "image" | "file" | "audio",
    "resource_id": 123,           # 资源元数据ID，级联删除时据此回收资源
    "url": "https://...",          # 附件访问URL
    "name": "image.jpg"            # 附件原始文件名
}
"""
from pydantic import BaseModel, ConfigDict, Field

from app.enums.interview_status import InterviewStatus


class Segment(BaseModel):
    """附件段：用户提问或 AI 回复中携带的 file/image/audio 附件。"""

    type: str = Field(..., description="附件类型：file / image / audio")
    resource_id: int | None = Field(None, description="资源元数据ID（级联删除回收依据）")
    url: str | None = Field(None, description="附件访问URL")
    name: str | None = Field(None, description="附件原始文件名")


class MessageResponse(BaseModel):
    """聊天消息响应模型。

    - request_text / response_text：聊天正文；
    - request_segments / response_segments：附件段列表，无附件时为 []；
    - status：关联面试的状态（0=进行中，1=已完成，2=异常终止），非面试消息为 null；
    - interview_id：关联面试记录ID，非面试消息为 null；
    - create_at：消息创建时间（Unix秒）。
    """

    id: int = Field(..., description="消息ID")
    request_text: str = Field(..., description="用户提问正文")
    response_text: str = Field(..., description="AI回复正文")
    request_segments: list[Segment] = Field(
        default_factory=list, description="用户提问附件段"
    )
    response_segments: list[Segment] = Field(
        default_factory=list, description="AI回复附件段"
    )
    status: InterviewStatus | None = Field(
        None, description="关联面试状态：0=进行中，1=已完成，2=异常终止；非面试消息为 null"
    )
    interview_id: int | None = Field(None, description="关联面试记录ID；非面试消息为 null")
    create_at: int = Field(..., description="消息创建时间（Unix秒）")

    model_config = ConfigDict(from_attributes=True)
