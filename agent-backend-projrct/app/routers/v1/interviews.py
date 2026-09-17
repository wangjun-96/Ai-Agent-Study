"""路由层：面试记录接口入口。

包含接口（见 prompt.md L175）：
1. GET /interviews/{interview_id} ：按 interview_id 获取面试详情（含 qa_object）

查询规则：interviews 表含 user_id 字段，需按 interview_id + user_id 联合查询，
越权访问统一返回 404，避免面试 ID 被枚举。
"""
from fastapi import APIRouter, Depends

from app.core import success
from app.core.responses import ApiResponse
from app.db.models import User
from app.routers.v1.deps import get_current_user, get_interview_service
from app.schemas.interview import InterviewResponse
from app.services.interview_service import InterviewService

# 公共错误响应文档：422 参数校验失败，各接口复用
_VALIDATION_ERROR_DOC = {
    "model": ApiResponse,
    "description": "请求参数校验失败(42200)，detail 中返回字段级错误明细",
}

router = APIRouter(
    prefix="/interviews",
    tags=["面试记录"],
    # 统一挂载 JWT 登录鉴权
    dependencies=[Depends(get_current_user)],
    responses={
        401: {
            "model": ApiResponse,
            "description": "未授权：缺失/过期/伪造访问令牌(40104)，需登录或静默刷新后重试",
        },
        422: _VALIDATION_ERROR_DOC,
    },
)


@router.get(
    "/{interview_id}",
    summary="获取面试详情",
    description=(
        "按面试 ID 获取面试详情文本，包含 qa_object（一问一答对象）。"
        "需面试归属当前用户，越权访问统一返回 404。"
    ),
    response_model=ApiResponse[InterviewResponse],
    responses={
        404: {"model": ApiResponse, "description": "面试记录不存在(40404)"},
    },
)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    """按 interview_id + user_id 查询面试详情。"""
    interview = service.get_interview(interview_id, current_user.id)
    return success(InterviewResponse.model_validate(interview).model_dump())
