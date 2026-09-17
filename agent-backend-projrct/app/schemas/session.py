"""校验层：会话相关的请求/响应模型。

- SessionCreate：创建会话请求体（title + session_model）；
- SessionUpdate：编辑会话请求体（title + session_model 均可选，支持部分更新）；
- SessionResponse：会话响应模型；
- 分页结果复用 app.core.pagination.PageResult。
"""
from pydantic import BaseModel, ConfigDict, Field

from app.enums.session_model import SessionModel


class SessionCreate(BaseModel):
    """创建会话请求体。"""

    title: str = Field(..., min_length=1, max_length=255, description="会话标题")
    session_model: SessionModel = Field(..., description="会话模式：0=学习，1=面试，2=笔记")


class SessionUpdate(BaseModel):
    """编辑会话请求体：title 与 session_model 均可选，支持部分更新。

    不传或传空的字段视为"不修改"，由 Service 层统一处理。
    """

    title: str | None = Field(None, min_length=1, max_length=255, description="会话标题（不传表示不修改）")
    session_model: SessionModel | None = Field(None, description="会话模式（不传表示不修改）")


class SessionResponse(BaseModel):
    """会话响应模型。"""

    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="所属用户ID")
    session_model: SessionModel = Field(..., description="会话模式")
    title: str = Field(..., description="会话标题")
    create_at: int = Field(..., description="创建时间（Unix秒）")

    model_config = ConfigDict(from_attributes=True)
