"""业务层：流程总控路由。

流程总控只做两件事：
1. 判断用户需求该走工作流还是通用聊天——先关键词快筛（廉价、确定性高），
   再以本地语义向量兜底（模型不可用时自动降级为聊天，不影响可用性）；
2. 命中工作流则委托对应业务服务启动（当前为学习测评出题），否则交回聊天服务。

本层不实现聊天逻辑，也不直接读写数据库/SQL。
"""
from dataclasses import dataclass

from app.agent.config import AGENT_CONFIG
from app.core import BusinessException, get_logger, settings
from app.enums.response_code import ResponseCode
from app.services.learning_workflow_service import LearningWorkflowService
from app.services.semantic_intent_service import SemanticIntentClassifier

logger = get_logger("orchestrator_service")


@dataclass(frozen=True)
class WorkflowRouteRule:
    """单个智能体的工作流路由规则。

    :param agent_name: 智能体名称（须存在于 AGENT_CONFIG）
    :param workflow_type: 命中的工作流类型，写入路由决策
    :param required_keywords: 关键词快筛词表，任意命中即直接走工作流
    :param intent_examples: 语义兜底示例句，与用户需求计算相似度
    :param similarity_threshold: 语义判定阈值，低于阈值走通用聊天
    """

    agent_name: str
    workflow_type: str
    required_keywords: tuple[str, ...]
    intent_examples: tuple[str, ...]
    similarity_threshold: float = settings.LONG_TERM_SIMILARITY_THRESHOLD


# 工作流路由规则表：新增工作流只需追加一条规则
WORKFLOW_ROUTE_RULES: tuple[WorkflowRouteRule, ...] = (
    WorkflowRouteRule(
        agent_name="quiz_generate_workflow",
        workflow_type="learning_quiz",
        required_keywords=("题", "出题", "刷题", "练习", "测验", "测评", "小测", "面试题"),
        intent_examples=(
            "帮我出几道练习题",
            "我想刷题巩固知识点",
            "给我来一套测验题",
            "针对我的薄弱点出一些题目",
            "我想做一个小测试",
            "给我出几道面试题",
        ),
    ),
)


def _get_rule(agent_name: str) -> WorkflowRouteRule | None:
    """按智能体名称获取工作流规则，无对应规则返回 None。"""
    for rule in WORKFLOW_ROUTE_RULES:
        if rule.agent_name == agent_name:
            return rule
    return None


class OrchestratorService:
    """流程总控服务：路由判定 + 工作流启动。"""

    def __init__(self, learning_service: LearningWorkflowService) -> None:
        self.learning_service = learning_service

    def route(self, agent_name: str, request_text: str) -> dict:
        """判定需求该走工作流还是通用聊天。

        :param agent_name: 智能体名称，须存在于 AGENT_CONFIG
        :param request_text: 用户需求文本
        :return: {"mode": workflow/chat, "workflow_type": 类型或 None, "confidence": 置信度}
        """
        # 1. 智能体白名单校验：未知名称直接拒绝，避免提示词模板定位失败
        if agent_name not in AGENT_CONFIG:
            raise BusinessException(
                ResponseCode.PARAM_INVALID,
                detail=f"未知智能体 agent_name={agent_name}",
            )

        # 2. 无工作流规则：该智能体只支持通用聊天
        rule = _get_rule(agent_name)
        if rule is None:
            return {"mode": "chat", "workflow_type": None, "confidence": 1.0}

        # 3. 关键词快筛：任意关键词命中即走工作流，无需语义推理
        keyword = next(
            (item for item in rule.required_keywords if item in request_text), None
        )
        if keyword is not None:
            logger.info(
                "流程总控命中工作流（关键词） agent_name={} keyword={} workflow_type={}",
                agent_name,
                keyword,
                rule.workflow_type,
            )
            return {
                "mode": "workflow",
                "workflow_type": rule.workflow_type,
                "confidence": 1.0,
            }

        # 4. 语义兜底：模型不可用时 similarity 返回 None，自动降级为通用聊天
        score = SemanticIntentClassifier.get().similarity(
            request_text, list(rule.intent_examples)
        )
        if score is not None and score >= rule.similarity_threshold:
            logger.info(
                "流程总控命中工作流（语义） agent_name={} score={} threshold={}",
                agent_name,
                round(score, 4),
                rule.similarity_threshold,
            )
            return {
                "mode": "workflow",
                "workflow_type": rule.workflow_type,
                "confidence": round(score, 4),
            }

        logger.info(
            "流程总控降级为通用聊天 agent_name={} score={}",
            agent_name,
            round(score, 4) if score is not None else None,
        )
        return {
            "mode": "chat",
            "workflow_type": None,
            "confidence": round(score, 4) if score is not None else 1.0,
        }

    def start_task(
        self,
        *,
        user_id: int,
        agent_name: str,
        session_id: int,
        request_text: str,
        question_count: int = 5,
        provider: str | None = None,
        decision: dict | None = None,
    ) -> dict:
        """按路由决策启动任务：工作流分支委托业务服务，聊天分支直接返回。

        :param user_id: 当前用户 ID
        :param agent_name: 智能体名称
        :param session_id: 关联会话 ID（须属于当前用户）
        :param request_text: 用户需求文本
        :param question_count: 命中学习测评工作流时的出题数量
        :param provider: 模型服务商标识
        :param decision: 路由层已计算好的决策，为空时重新判定
        :return: 工作流分支返回 mode/workflow_type/run_id/status/quiz；聊天分支返回 mode/workflow_type
        """
        decision = decision or self.route(agent_name, request_text)
        if decision["mode"] != "workflow":
            return {"mode": "chat", "workflow_type": None}

        result = self.learning_service.start(
            user_id=user_id,
            session_id=session_id,
            request_text=request_text,
            question_count=question_count,
            provider=provider,
        )
        return {
            "mode": "workflow",
            "workflow_type": decision["workflow_type"],
            **result,
        }
