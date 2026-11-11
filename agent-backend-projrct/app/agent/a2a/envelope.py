"""A2A 消息信封（最小契约）。

供智能体之间传递结构化结果：由 from_agent 产出 payload_type 类型的 payload，
可指定 next_agent 交由下游智能体继续处理，confidence 表示本次结果的置信度。
"""
from typing import Any

from pydantic import BaseModel, Field


class A2AEnvelope(BaseModel):
    """最小 A2A 契约信封，智能体间通信用。"""

    from_agent: str = Field(..., description="产出结果的智能体名称")
    payload_type: str = Field(..., description="载荷类型标识（如 quiz / evaluation）")
    payload: dict[str, Any] = Field(default_factory=dict)
    next_agent: str | None = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)
