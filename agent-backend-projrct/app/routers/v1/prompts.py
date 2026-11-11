"""路由层：提示词模板管理与智能体配置接口。

包含接口（见 prompt.md「提示词版本管理」）：
1. GET  /prompt/templates/{agent_name}/{scene} ：查询生效模板（公共 + 私有 + 拼接结果）
2. POST /prompt/rollback                        ：一键回滚到指定历史版本
3. GET  /prompt/config/agents                   ：智能体映射配置

所有接口统一挂载 JWT 登录鉴权。
"""
from fastapi import APIRouter, Depends

from app.agent.config import AGENT_CONFIG
from app.core import success
from app.core.responses import ApiResponse
from app.routers.v1.deps import get_current_user, get_prompt_template_manager
from app.schemas.prompt import (
    AgentConfigItemResponse,
    PromptRollbackRequest,
    PromptTemplateDetail,
    PromptTemplateItem,
)
from app.services.prompt_template_service import PromptTemplateManager, to_cache_payload

router = APIRouter(
    prefix="/prompt",
    tags=["提示词管理"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {
            "model": ApiResponse,
            "description": "未授权：缺失/过期/伪造访问令牌(40104)",
        },
    },
)


def _to_item(payload: dict) -> PromptTemplateItem:
    """缓存/数据库模板字典 -> 响应模型。"""
    return PromptTemplateItem(**payload)


@router.get(
    "/templates/{agent_name}/{scene}",
    summary="查询生效提示词模板",
    description=(
        "返回指定智能体与场景下当前生效的公共模板、私有模板，"
        "以及两者拼接后的完整提示词。Redis 命中优先，未命中回落数据库。"
    ),
    response_model=ApiResponse[PromptTemplateDetail],
)
def get_prompt_template(
    agent_name: str,
    scene: str,
    service: PromptTemplateManager = Depends(get_prompt_template_manager),
) -> dict:
    """查询生效模板：公共模板（通用规则）+ 私有模板（Agent 指令）。"""
    public_payload = service.get_active_template(None, scene)
    private_payload = service.get_active_template(agent_name, scene)
    full_prompt = "\n\n".join(
        payload["template_content"].strip()
        for payload in (public_payload, private_payload)
        if payload and payload.get("template_content")
    )
    detail = PromptTemplateDetail(
        agent_name=agent_name,
        scene=scene,
        public_template=_to_item(public_payload) if public_payload else None,
        private_template=_to_item(private_payload) if private_payload else None,
        full_prompt=full_prompt,
    )
    return success(detail.model_dump())


@router.post(
    "/rollback",
    summary="一键回滚提示词版本",
    description=(
        "把指定历史版本重新置为生效版本：同一 (agent_name, scene) 下其余版本自动下线，"
        "并同步刷新 Redis 缓存。"
    ),
    response_model=ApiResponse[PromptTemplateItem],
)
def rollback_prompt_template(
    payload: PromptRollbackRequest,
    service: PromptTemplateManager = Depends(get_prompt_template_manager),
) -> dict:
    """一键回滚：历史版本重新生效并刷新缓存。"""
    template = service.rollback(payload.template_id)
    return success(
        _to_item(to_cache_payload(template)), "模板回滚成功"
    )


@router.get(
    "/config/agents",
    summary="智能体配置列表",
    description="返回 7 个智能体的名称、中文标签、默认场景与职责说明。",
    response_model=ApiResponse[list[AgentConfigItemResponse]],
)
def list_agents() -> dict:
    """返回智能体映射配置。"""
    items = [
        AgentConfigItemResponse(
            agent_name=name,
            label=config["label"],
            scene=config["scene"],
            description=config["description"],
        )
        for name, config in AGENT_CONFIG.items()
    ]
    return success([item.model_dump() for item in items])
