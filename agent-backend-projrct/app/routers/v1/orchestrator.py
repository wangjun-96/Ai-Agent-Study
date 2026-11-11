"""路由层：流程总控入口。

同一入口按路由决策分流：
1. 命中工作流 → 启动对应工作流（当前为学习测评出题），返回 JSON 业务数据；
2. 未命中 → 校验会话归属后复用流式聊天服务，返回 SSE 流。

接口统一挂载 JWT 登录鉴权，用户只能操作自己的会话；两种分支响应类型不同，故不设置 response_model。
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core import success
from app.core.responses import ApiResponse
from app.db.models import User
from app.routers.v1.deps import (
    get_current_user,
    get_orchestrator_service,
    get_stream_chat_service,
)
from app.schemas.message import StreamChatRequest
from app.schemas.orchestrator_schemas import AgentTaskStartRequest
from app.services.orchestrator_service import OrchestratorService
from app.services.stream_chat_service import StreamChatService

router = APIRouter(
    prefix="/agent",
    tags=["流程总控"],
    # 统一挂载 JWT 登录鉴权：所有流程总控接口必须携带有效访问令牌
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ApiResponse, "description": "未授权：缺失/过期/伪造访问令牌(40104)"},
    },
)


@router.post(
    "/tasks/start",
    summary="流程总控入口（工作流或通用聊天）",
    description=(
        "按 agent_name 与 request_text 判定执行路径：命中工作流（如学习测评出题）"
        "返回 JSON 业务数据；未命中则校验会话归属后返回 SSE 流式聊天响应。"
    ),
)
def start_agent_task(
    payload: AgentTaskStartRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: OrchestratorService = Depends(get_orchestrator_service),
    chat_service: StreamChatService = Depends(get_stream_chat_service),
):
    """流程总控：工作流分支返回 JSON，聊天分支返回 SSE 流。"""
    user_id = int(current_user.id)
    # 路由判定只计算一次，避免工作流启动时重复语义推理
    decision = orchestrator.route(payload.agent_name, payload.request_text)

    # 分支一：命中工作流，启动后返回业务数据
    if decision["mode"] == "workflow":
        data = orchestrator.start_task(
            user_id=user_id,
            agent_name=payload.agent_name,
            session_id=payload.session_id,
            request_text=payload.request_text,
            question_count=payload.question_count,
            provider=payload.provider,
            decision=decision,
        )
        return success(data, "已启动学习测评工作流")

    # 分支二：通用聊天，先校验会话归属，再复用流式聊天服务
    chat_service.assert_session(payload.session_id, user_id)
    chat_payload = StreamChatRequest(
        request_text=payload.request_text,
        select_model=payload.select_model,
        agent_name=payload.agent_name,
        request_segments=payload.request_segments,
    )
    return StreamingResponse(
        chat_service.stream_chat(payload.session_id, user_id, chat_payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
