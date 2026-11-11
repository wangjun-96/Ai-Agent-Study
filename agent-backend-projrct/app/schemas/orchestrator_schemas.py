"""校验层：流程总控（智能体任务入口）的请求与响应模型。

流程总控统一收口"用户一句话该走工作流还是通用聊天"的判断：
- 入参复用会话、智能体名称、需求文本、选择模式与附件段，另含出题数量与模型提供商；
- 出参路由决策记录 mode（workflow / chat）、workflow_type 与判定置信度；
- 启动响应在工作流分支返回 run_id / status / quiz，在聊天分支仅返回 mode=chat。
"""
from typing import Any

from pydantic import BaseModel, Field

from app.enums.select_model import SelectModel
from app.schemas.message import Segment


class AgentTaskStartRequest(BaseModel):
    """流程总控启动请求模型：智能体 / 会话 / 需求文本 / 附件与出题参数。"""

    session_id: int = Field(..., ge=1, description="关联会话ID（须属于当前用户）")
    agent_name: str = Field(
        ..., max_length=64, description="智能体名称，决定启动工作流或通用聊天"
    )
    request_text: str = Field(
        ..., min_length=1, max_length=20000, description="用户需求文本"
    )
    select_model: SelectModel = Field(
        SelectModel.DEFAULT,
        description="选择模式：0=默认，1=知识精讲，2=刷题，3=简历优化，4=模拟面试，5=面试复盘",
    )
    request_segments: list[Segment] = Field(
        default_factory=list, description="用户提问附件段"
    )
    question_count: int = Field(
        5, ge=1, le=20, description="命中学习测评工作流时的出题数量"
    )
    provider: str | None = Field(
        None, max_length=32, description="模型服务商标识，为空时读取全局配置"
    )


class AgentTaskRouteDecision(BaseModel):
    """流程总控路由决策模型：记录最终模式、工作流类型与判定置信度。"""

    mode: str = Field(..., description="执行模式：workflow=工作流，chat=通用聊天")
    workflow_type: str | None = Field(
        None, description="工作流类型，聊天模式为 null"
    )
    confidence: float = Field(..., description="路由判定置信度（0-1）")


class AgentTaskStartResponse(BaseModel):
    """流程总控启动响应模型（工作流分支）。"""

    mode: str = Field(..., description="执行模式：workflow=工作流，chat=通用聊天")
    workflow_type: str | None = Field(
        None, description="工作流类型，聊天模式为 null"
    )
    run_id: str | None = Field(None, description="工作流运行ID，聊天模式为 null")
    status: str | None = Field(None, description="工作流状态，聊天模式为 null")
    quiz: dict[str, Any] | None = Field(
        None, description="结构化题目JSON（title/questions），聊天模式为 null"
    )
