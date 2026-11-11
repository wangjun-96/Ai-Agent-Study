"""业务层：提示词模板版本管理与 Redis 缓存。

核心能力（见 prompt.md「提示词版本管理」）：
1. 计算下一版本：同 (agent_name, scene) 分组内版本独立递增；
2. 启动加载：把全部生效模板写入 Redis Hash（prompt:templates:active），
   私有字段为 ``{agent}:{scene}``，公共字段为 ``__common__:{scene}``；
3. 读取模板：Redis 命中优先，未命中回落数据库并回填缓存；
4. 拼接提示词：公共模板（通用规则）+ 私有模板（Agent 指令）；
5. 一键回滚：把历史版本重新置为生效，并同步刷新 Redis。

Redis 不可用时全部自动降级为数据库直读，不影响主流程。
"""
import json

from sqlalchemy.orm import Session

from app.agent.config import get_agent_scene
from app.core import BusinessException, get_logger, settings
from app.dao.prompt_template_dao import PromptTemplateDao
from app.db.models import PromptTemplate
from app.enums.response_code import ResponseCode
from app.enums.template_type import TemplateType
from app.integrations.redis_client import RedisCache

logger = get_logger("prompt_template_service")

# 公共模板在缓存中的字段前缀（agent_name 为空时使用）
COMMON_AGENT_KEY = "__common__"


def _cache_field(agent_name: str | None, scene: str) -> str:
    """缓存字段名：私有模板 {agent}:{scene}，公共模板 __common__:{scene}。"""
    return f"{agent_name or COMMON_AGENT_KEY}:{scene}"


def _parse_variables(raw: str | None) -> list[str]:
    """把数据库中的 JSON 字符串变量列表解析为列表，非法内容返回空列表。"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(item) for item in data] if isinstance(data, list) else []
    except json.JSONDecodeError:
        logger.warning("模板变量解析失败 raw={}", raw)
        return []


def to_cache_payload(template: PromptTemplate) -> dict:
    """模板 ORM -> 缓存字典（版本、内容、变量全部保留，便于回滚后直接刷新）。"""
    return {
        "id": template.id,
        "agent_name": template.agent_name,
        "scene": template.scene,
        "template_type": template.template_type,
        "template_content": template.template_content,
        "variables": _parse_variables(template.variables),
        "version": template.version,
        "is_active": template.is_active,
        "description": template.description,
        "created_at": template.created_at,
    }


class PromptTemplateManager:
    """提示词模板管理器：版本管理 + Redis 缓存 + 公共/私有模板拼接。"""

    def __init__(
        self,
        dao: PromptTemplateDao,
        cache: RedisCache | None,
    ) -> None:
        self.dao = dao
        self.cache = cache

    # ------------------------------ 版本管理 ------------------------------

    def next_version(self, agent_name: str | None, scene: str) -> int:
        """计算指定分组的下一个版本号（最大版本 + 1）。"""
        return self.dao.max_version(agent_name, scene) + 1

    def create_template(
        self,
        *,
        scene: str,
        template_content: str,
        template_type: TemplateType,
        agent_name: str | None = None,
        variables: list[str] | None = None,
        description: str | None = None,
        is_active: bool = False,
    ) -> PromptTemplate:
        """新建模板版本：自动计算版本号，按需置为生效版本并刷新缓存。

        :param scene: 业务场景
        :param template_content: 模板正文
        :param template_type: 模板类型（私有/公共）
        :param agent_name: 智能体名称，公共模板必须为空
        :param variables: 变量名列表
        :param description: 版本说明
        :param is_active: 是否设为生效版本（同组已有生效版本时不会被强制切换）
        """
        if template_type == TemplateType.PUBLIC and agent_name:
            raise BusinessException(
                ResponseCode.PARAM_INVALID,
                detail="公共模板的 agent_name 必须为空",
            )
        if template_type == TemplateType.PRIVATE and not agent_name:
            raise BusinessException(
                ResponseCode.PARAM_INVALID,
                detail="私有模板必须指定 agent_name",
            )

        version = self.next_version(agent_name, scene)
        # 同组已有生效版本时，新版本默认不生效，保持「仅一条 is_active=1」
        has_active = self.dao.get_active(agent_name, scene) is not None
        template = PromptTemplate(
            agent_name=agent_name,
            scene=scene,
            template_type=int(template_type),
            template_content=template_content,
            variables=json.dumps(variables or [], ensure_ascii=False),
            version=version,
            is_active=1 if (is_active and not has_active) else 0,
            description=description,
        )
        template = self.dao.insert(template)
        logger.info(
            "创建模板模板 id={} agent={} scene={} version={} active={}",
            template.id,
            agent_name,
            scene,
            version,
            template.is_active,
        )
        if template.is_active == 1:
            self._cache_template(template)
        return template

    def rollback(self, template_id: int) -> PromptTemplate:
        """一键回滚：把指定历史版本重新置为生效版本，并同步刷新 Redis。"""
        template = self.dao.get_by_id(template_id)
        if template is None:
            raise BusinessException(
                ResponseCode.PARAM_INVALID, detail=f"模板不存在 template_id={template_id}"
            )
        template = self.dao.activate(template)
        self._cache_template(template)
        logger.info(
            "模板回滚生效 id={} agent={} scene={} version={}",
            template.id,
            template.agent_name,
            template.scene,
            template.version,
        )
        return template

    # ------------------------------ 缓存管理 ------------------------------

    def load_active_templates(self) -> int:
        """启动加载：把全部生效模板批量写入 Redis（覆盖旧缓存），返回加载条数。"""
        templates = self.dao.list_active()
        if self.cache is None:
            logger.info("Redis 不可用，跳过模板缓存加载 count={}", len(templates))
            return 0

        # 先清空旧的生效版本缓存，避免已下线版本残留
        self.cache.delete(settings.PROMPT_CACHE_KEY)
        for template in templates:
            self.cache.hset_json(
                settings.PROMPT_CACHE_KEY,
                _cache_field(template.agent_name, template.scene),
                to_cache_payload(template),
            )
        logger.info("提示词模板已加载到 Redis count={}", len(templates))
        return len(templates)

    def _cache_template(self, template: PromptTemplate) -> None:
        """把单个模板写入 Redis（回滚、新建生效版本后调用）。"""
        if self.cache is None:
            return
        self.cache.hset_json(
            settings.PROMPT_CACHE_KEY,
            _cache_field(template.agent_name, template.scene),
            to_cache_payload(template),
        )

    def get_cached_template(self, agent_name: str | None, scene: str) -> dict | None:
        """从 Redis 读取模板，未命中返回 None。"""
        if self.cache is None:
            return None
        return self.cache.hget_json(
            settings.PROMPT_CACHE_KEY, _cache_field(agent_name, scene)
        )

    def get_active_template(
        self, agent_name: str | None, scene: str, db: Session | None = None
    ) -> dict | None:
        """读取生效模板：Redis 命中优先，未命中回落数据库并回填缓存。"""
        cached = self.get_cached_template(agent_name, scene)
        if cached is not None:
            return cached

        dao = PromptTemplateDao(db) if db is not None else self.dao
        template = dao.get_active(agent_name, scene)
        if template is None:
            return None
        payload = to_cache_payload(template)
        self._cache_template(template)
        return payload

    def list_templates(
        self, agent_name: str | None, scene: str, db: Session | None = None
    ) -> list[PromptTemplate]:
        """查询分组下的全部历史版本（按版本号倒序）。"""
        dao = PromptTemplateDao(db) if db is not None else self.dao
        return dao.list_by_group(agent_name, scene)

    # ------------------------------ 提示词拼接 ------------------------------

    def get_full_prompt(self, agent_name: str, db: Session | None = None) -> str:
        """拼接完整提示词：公共模板（通用规则）+ 私有模板（Agent 指令）。

        :param agent_name: 智能体名称
        :param db: 可选的独立 Session（流式/异步场景使用，缺省用当前 DAO）
        :return: 拼接后的提示词，两类模板都缺失时返回空串（由调用方使用默认提示词）
        """
        scene = get_agent_scene(agent_name)
        if not scene:
            raise BusinessException(
                ResponseCode.PARAM_INVALID, detail=f"未知智能体 agent_name={agent_name}"
            )

        public_payload = self.get_active_template(None, scene, db)
        private_payload = self.get_active_template(agent_name, scene, db)

        parts: list[str] = []
        if public_payload:
            parts.append(public_payload["template_content"].strip())
        if private_payload:
            parts.append(private_payload["template_content"].strip())
        full_prompt = "\n\n".join(part for part in parts if part)
        logger.info(
            "拼接提示词 agent={} scene={} public={} private={} chars={}",
            agent_name,
            scene,
            bool(public_payload),
            bool(private_payload),
            len(full_prompt),
        )
        return full_prompt
