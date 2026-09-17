"""路由层：会话与聊天消息接口入口。

包含接口（见 prompt.md L162-175）：
1. GET  /sessions                       ：会话列表分页（按当前用户）
2. POST /sessions                       ：创建会话（title + session_model）
3. PUT  /sessions/{session_id}          ：编辑会话标题
4. DELETE /sessions/{session_id}        ：删除会话（级联删除消息/面试/资源）
5. GET  /sessions/{session_id}/messages ：分页获取聊天消息

所有接口统一挂载 JWT 登录鉴权，越权访问（非本人会话）统一返回 404。
"""
from fastapi import APIRouter, Depends, Query, status

from app.core import success
from app.core.pagination import PageParams, PageResult
from app.core.responses import ApiResponse
from app.db.models import User
from app.enums.session_model import SessionModel
from app.routers.v1.deps import (
    get_current_user,
    get_message_service,
    get_session_service,
)
from app.schemas.message import MessageResponse, Segment
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate
from app.services.message_service import MessageService
from app.services.session_service import SessionService

# 公共错误响应文档：422 参数校验失败，各接口复用
_VALIDATION_ERROR_DOC = {
    "model": ApiResponse,
    "description": "请求参数校验失败(42200)，detail 中返回字段级错误明细",
}

router = APIRouter(
    prefix="/sessions",
    tags=["会话与聊天"],
    # 统一挂载 JWT 登录鉴权：所有会话接口必须携带有效访问令牌
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
    "/",
    summary="会话列表分页",
    description=(
        "返回当前用户的会话列表，按创建时间倒序，支持 page / page_size 分页。"
        "可选传 session_model 按模式过滤（0=学习，1=面试，2=笔记）。"
    ),
    response_model=ApiResponse[PageResult[SessionResponse]],
)
def list_sessions(
    page: PageParams = Depends(),
    session_model: SessionModel | None = Query(None, description="按会话模式过滤：0=学习，1=面试，2=笔记"),
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict:
    """分页查询当前用户的会话列表，可按 session_model 过滤。"""
    items, total = service.list_sessions(current_user.id, page, session_model)
    data = PageResult[SessionResponse](
        items=[SessionResponse.model_validate(s).model_dump() for s in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )
    return success(data.model_dump())


@router.post(
    "/",
    summary="创建会话",
    description="创建会话主题，需传入 title（标题）与 session_model（0=学习，1=面试，2=笔记）。",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[SessionResponse],
)
def create_session(
    session_in: SessionCreate,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict:
    """创建新会话。"""
    session = service.create_session(current_user.id, session_in)
    return success(
        SessionResponse.model_validate(session).model_dump(), "会话创建成功"
    )


@router.put(
    "/{session_id}",
    summary="编辑会话",
    description=(
        "按会话 ID 编辑会话，支持修改 title 与 session_model，"
        "仅更新传入的非空字段，仅会话归属用户可操作，越权返回 404。"
    ),
    response_model=ApiResponse[SessionResponse],
    responses={
        404: {"model": ApiResponse, "description": "会话不存在(40403)"},
    },
)
def update_session(
    session_id: int,
    session_in: SessionUpdate,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict:
    """编辑会话（标题 / 模式），仅更新传入的非空字段。"""
    session = service.update_session(session_id, current_user.id, session_in)
    return success(
        SessionResponse.model_validate(session).model_dump(), "会话更新成功"
    )


@router.delete(
    "/{session_id}",
    summary="删除会话（级联）",
    description=(
        "级联删除会话：删除会话下全部聊天消息、关联面试记录，"
        "并解析消息 segments 收集 resource_id，删除关联资源的 MinIO 对象与元数据。"
        "需传入 session_model 查询参数校验会话类型，类型不匹配返回 404。"
    ),
    response_model=ApiResponse,
    responses={
        404: {"model": ApiResponse, "description": "会话不存在(40403)"},
    },
)
def delete_session(
    session_id: int,
    session_model: SessionModel = Query(..., description="会话模式：0=学习，1=面试，2=笔记（校验会话类型匹配）"),
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
) -> dict:
    """级联删除会话及其全部关联数据，需校验 session_model 匹配。"""
    service.delete_session(session_id, current_user.id, session_model)
    return success(message="会话删除成功")


@router.get(
    "/{session_id}/messages",
    summary="分页获取聊天消息",
    description=(
        "按会话分页获取聊天消息，返回 request_text / response_text + "
        "request_segments / response_segments + status / interview_id / create_at。"
        "status 取自关联面试状态，非面试消息为 null。"
    ),
    response_model=ApiResponse[PageResult[MessageResponse]],
    responses={
        404: {"model": ApiResponse, "description": "会话不存在(40403)"},
    },
)
def list_messages(
    session_id: int,
    page: PageParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
) -> dict:
    """分页查询会话下的聊天消息。"""
    messages, total, status_map = service.list_messages(
        session_id, current_user.id, page
    )
    items = [
        MessageResponse(
            id=msg.id,
            request_text=msg.request_text,
            response_text=msg.response_text,
            request_segments=[Segment(**s) for s in (msg.request_segments or [])],
            response_segments=[Segment(**s) for s in (msg.response_segments or [])],
            status=status_map.get(msg.interview_id) if msg.interview_id else None,
            interview_id=msg.interview_id,
            create_at=msg.create_at,
        ).model_dump()
        for msg in messages
    ]
    data = PageResult[MessageResponse](
        items=items,
        total=total,
        page=page.page,
        page_size=page.page_size,
    )
    return success(data.model_dump())
