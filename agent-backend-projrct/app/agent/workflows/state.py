"""学习测评工作流状态定义。

字段覆盖出题 → 作答 → 评分 → 复盘的完整链路，LangGraph 节点之间通过该
TypedDict 传递状态；业务快照最终序列化写入 workflow_runs.state_json。
"""
from typing import Any, TypedDict


class LearningWorkflowState(TypedDict, total=False):
    """学习测评工作流状态（total=False 表示各节点可按需增量更新）。"""

    run_id: str                    # 工作流运行 ID（同时作为 LangGraph thread_id）
    user_id: int                   # 发起用户 ID
    session_id: int                # 关联会话 ID
    request_text: str              # 用户原始请求文本
    provider: str | None           # 模型服务商标识
    question_count: int            # 出题数量
    quiz: dict[str, Any]           # 生成的题目 JSON
    answers: list[dict[str, Any]]  # 用户作答列表
    evaluation: dict[str, Any]     # 评分明细 JSON
    score: int                     # 总分
    weaknesses: list[str]          # 薄弱知识点列表
    review: str                    # 复盘点评文本
    status: str                    # 工作流状态
    a2a_envelope: dict[str, Any]   # A2A 消息信封（智能体间结构化结果）
