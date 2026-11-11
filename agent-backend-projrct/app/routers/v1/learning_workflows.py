"""路由层：学习测评工作流接口。

包含接口：
1. POST /learning-workflows/start            ：启动测评并生成题目（图停在等待作答）；
2. POST /learning-workflows/{run_id}/submit  ：提交答案，恢复图执行并完成评分；
3. GET  /learning-workflows/{run_id}         ：查询工作流运行状态与业务快照。

所有接口统一挂载 JWT 登录鉴权，用户只能操作自己发起的测评。
"""
from fastapi import APIRouter, Depends

from app.core import success
from app.core.responses import ApiResponse
from app.db.models import User
from app.routers.v1.deps import get_current_user, get_learning_workflow_service
from app.schemas.learning_workflow import (
    LearningWorkflowDetailResponse,
    LearningWorkflowStartRequest,
    LearningWorkflowStartResponse,
    LearningWorkflowSubmitRequest,
    LearningWorkflowSubmitResponse,
)
from app.services.learning_workflow_service import LearningWorkflowService

router = APIRouter(
    prefix="/learning-workflows",
    tags=["学习测评工作流"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ApiResponse, "description": "未授权：缺失/过期/伪造访问令牌(40104)"},
    },
)


@router.post(
    "/start",
    summary="启动学习测评（生成题目）",
    description=(
        "按用户需求生成结构化练习题并暂停在等待作答节点，"
        "返回 run_id 与题目 JSON；同时写入一条刷题模式消息供前端展示答题卡。"
    ),
    response_model=ApiResponse[LearningWorkflowStartResponse],
)
def start_learning_workflow(
    payload: LearningWorkflowStartRequest,
    current_user: User = Depends(get_current_user),
    service: LearningWorkflowService = Depends(get_learning_workflow_service),
) -> dict:
    """启动学习测评：校验会话归属、出题并返回答题卡数据。"""
    data = service.start(
        user_id=int(current_user.id),
        session_id=payload.session_id,
        request_text=payload.request_text,
        question_count=payload.question_count,
        provider=payload.provider,
    )
    return success(data, "出题成功")


@router.post(
    "/{run_id}/submit",
    summary="提交学习测评答案（评分与复盘）",
    description=(
        "提交作答列表后恢复图执行，调用评测智能体逐题判分，"
        "返回总分、评分明细、薄弱知识点、学习建议与 A2A 信封，并回写原出题消息。"
    ),
    response_model=ApiResponse[LearningWorkflowSubmitResponse],
)
def submit_learning_workflow(
    run_id: str,
    payload: LearningWorkflowSubmitRequest,
    current_user: User = Depends(get_current_user),
    service: LearningWorkflowService = Depends(get_learning_workflow_service),
) -> dict:
    """提交答案：完成评分并回写测评结果。"""
    data = service.submit_answer(
        user_id=int(current_user.id),
        run_id=run_id,
        answers=[item.model_dump() for item in payload.answers],
    )
    return success(data, "评分完成")


@router.get(
    "/{run_id}",
    summary="查询学习测评运行状态",
    description="按 run_id 查询工作流运行状态与业务状态快照（题目、答案、评分结果）。",
    response_model=ApiResponse[LearningWorkflowDetailResponse],
)
def get_learning_workflow(
    run_id: str,
    current_user: User = Depends(get_current_user),
    service: LearningWorkflowService = Depends(get_learning_workflow_service),
) -> dict:
    """查询工作流运行状态与业务快照。"""
    data = service.get_run(user_id=int(current_user.id), run_id=run_id)
    return success(data)
