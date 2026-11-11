"""校验层：学习测评工作流的请求与响应模型。

- 请求模型约束会话、需求文本、出题数量与作答列表；
- 响应模型输出运行状态、题目 JSON、评分明细、薄弱点与 A2A 信封。
"""
from typing import Any

from pydantic import BaseModel, Field


class LearningWorkflowStartRequest(BaseModel):
    """启动学习测评请求模型。"""

    session_id: int = Field(..., ge=1, description="关联会话ID（须属于当前用户）")
    request_text: str = Field(
        ..., min_length=1, max_length=20000, description="用户需求文本"
    )
    question_count: int = Field(5, ge=1, le=20, description="出题数量（1-20 题）")
    provider: str | None = Field(
        None, max_length=32, description="模型服务商标识，为空时读取全局配置"
    )


class LearningAnswerItem(BaseModel):
    """单题作答项：单选/主观题为字符串，多选为字符串数组。"""

    question_id: str = Field(..., max_length=64, description="题目编号，如 q1")
    value: str | list[str] | None = Field(
        None, description="作答值：单选/主观题为字符串，多选为字符串数组"
    )


class LearningWorkflowSubmitRequest(BaseModel):
    """提交答题请求模型。"""

    answers: list[LearningAnswerItem] = Field(
        default_factory=list, description="作答列表"
    )


class LearningWorkflowStartResponse(BaseModel):
    """启动学习测评响应模型。"""

    run_id: str = Field(..., description="工作流运行ID")
    status: str = Field(..., description="工作流状态，出题后为 waiting_answer")
    quiz: dict[str, Any] = Field(..., description="结构化题目JSON（title/questions）")


class LearningWorkflowSubmitResponse(BaseModel):
    """提交答题响应模型。"""

    run_id: str = Field(..., description="工作流运行ID")
    status: str = Field(..., description="工作流状态，评分后为 completed")
    score: int = Field(..., description="总分（0-100）")
    evaluation: dict[str, Any] = Field(..., description="评分明细JSON")
    weaknesses: list[str] = Field(..., description="薄弱知识点列表")
    review: str = Field(..., description="整体学习建议")
    a2a_envelope: dict[str, Any] = Field(..., description="A2A 消息信封")


class LearningWorkflowDetailResponse(BaseModel):
    """查询工作流运行详情响应模型。"""

    run_id: str = Field(..., description="工作流运行ID")
    status: str = Field(..., description="工作流状态")
    state: dict[str, Any] | None = Field(
        None, description="业务状态快照（题目、答案、评分结果）"
    )
