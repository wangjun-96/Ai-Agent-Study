"""业务层：长期记忆（用户画像摘要与语义写入判断）。

能力：
1. load_memory_context：把用户画像拼成 SystemMessage 文本，供每轮对话注入；
2. should_write：语义相似度 + 关键词兜底，判断用户是否在表达“需要记住”的个人信息；
3. submit_profile_update_async：后台线程调用 LLM 抽取画像字段并落库，不阻塞对话。
"""
import threading

from sqlalchemy.orm import Session

from app.agent.config import get_agent_scene
from app.core import get_logger, settings
from app.dao.prompt_template_dao import PromptTemplateDao
from app.dao.user_profile_dao import UserProfileDao
from app.db.database import SessionLocal
from app.integrations.redis_client import get_redis_cache
from app.llm.llm import get_llm
from app.schemas.user_profile import UserProfileUpsert
from app.services.prompt_template_service import PromptTemplateManager
from app.services.semantic_intent_service import SemanticIntentClassifier
from app.services.user_profile_service import UserProfileService
from app.utils.json_utils import parse_json_object

logger = get_logger("long_term_memory")

# 画像写入意图示例：用于语义相似度判断
PROFILE_WRITE_EXAMPLES = [
    "我的目标岗位是后端开发工程师",
    "我有三年 Java 开发经验",
    "我准备面试前端岗位",
    "我比较薄弱的知识点是算法和数据库",
    "我的学习目标是三个月内掌握 Python",
    "我喜欢通过做题来学习",
    "请记住我的这些信息",
    "我擅长使用 Vue 和 TypeScript",
    "我是转行学习软件开发的",
    "我最近在准备秋招面试",
]

# 关键词兜底：语义模型不可用时使用
PROFILE_WRITE_KEYWORDS = (
    "我的目标", "目标岗位", "经验", "擅长", "薄弱", "学习目标",
    "学习计划", "面试", "记住", "转行", "零基础", "偏好", "准备",
)

# 允许 LLM 抽取并写回画像的字段
EXTRACT_FIELDS = (
    "target_job",
    "years_experience",
    "target_level",
    "target_skills",
    "weak_topics",
    "learning_goal",
    "learning_style",
    "interview_focus",
    "long_term_summary",
)

# 画像抽取默认提示词（数据库无生效模板时兜底）
DEFAULT_EXTRACT_PROMPT = """你是用户画像抽取助手。请从下面的对话中抽取用户的个人学习/求职信息，
只保留有明确依据的内容，无法判断的字段返回 null。只输出 JSON 对象，不要解释。
字段：
- target_job：目标岗位
- years_experience：工作经验
- target_level：目标等级
- target_skills：已掌握技能（字符串数组）
- weak_topics：薄弱点（字符串数组）
- learning_goal：学习目标
- learning_style：学习风格/偏好
- interview_focus：面试关注方向（字符串数组）
- long_term_summary：用户长期信息摘要（不超过 300 字）

对话上下文：
{conversation_context}

本轮用户消息：
{request_text}"""


class LongTermMemory:
    """长期记忆工具类：画像上下文读取、写入意图判断、异步画像更新。"""

    @staticmethod
    def load_memory_context(user_id: int, db: Session) -> str:
        """把用户画像拼成注入提示词的文本，无有效画像时返回空串。"""
        profile = UserProfileService(UserProfileDao(db)).get_profile_dict(user_id)
        if not profile:
            return ""
        labels = {
            "target_job": "目标岗位",
            "years_experience": "工作经验",
            "target_level": "目标等级",
            "target_skills": "已掌握技能",
            "weak_topics": "薄弱点",
            "learning_goal": "学习目标",
            "learning_style": "学习风格",
            "interview_focus": "面试关注方向",
            "long_term_summary": "长期摘要",
        }
        lines: list[str] = ["【用户长期画像】"]
        for field, label in labels.items():
            value = profile.get(field)
            if isinstance(value, (list, tuple)):
                value = "、".join(str(item) for item in value if item)
            if value is None or value == "" or value == []:
                continue
            lines.append(f"- {label}：{value}")
        if len(lines) == 1:
            return ""
        return "\n".join(lines)[: settings.PROMPT_VARS_TOTAL_MAX_LENGTH]

    @staticmethod
    def should_write(request_text: str) -> bool:
        """判断本轮用户消息是否包含需要写入长期画像的个人信息。

        语义模型可用时按相似度阈值判断；不可用或相似度不足时用关键词兜底。
        """
        text = (request_text or "").strip()
        if not text:
            return False
        # 明确要求记住时直接命中，避免语义模型漏判
        if "记住" in text or "记一下" in text:
            return True
        similarity = SemanticIntentClassifier.get().similarity(
            text, PROFILE_WRITE_EXAMPLES
        )
        if similarity is None:
            return any(keyword in text for keyword in PROFILE_WRITE_KEYWORDS)
        return similarity >= settings.LONG_TERM_SIMILARITY_THRESHOLD

    @classmethod
    def submit_profile_update_async(
        cls,
        user_id: int,
        request_text: str,
        conversation_context: str,
    ) -> None:
        """后台线程抽取并更新画像，失败只记日志，不影响主对话。

        调用方需先通过 should_write 判断，避免同一轮重复做语义分类。
        """
        thread = threading.Thread(
            target=cls._update_profile_worker,
            args=(user_id, request_text, conversation_context),
            daemon=True,
            name=f"long-term-memory-{user_id}",
        )
        thread.start()

    @classmethod
    def _update_profile_worker(
        cls, user_id: int, request_text: str, conversation_context: str
    ) -> None:
        """后台线程任务：LLM 抽取画像 JSON → 字段校验 → 落库。"""
        db = SessionLocal()
        try:
            manager = PromptTemplateManager(PromptTemplateDao(db), get_redis_cache())
            # 画像抽取智能体未注册到 AGENT_CONFIG 时直接使用默认抽取提示词
            scene = get_agent_scene("long_term_memory_extractor")
            template = manager.get_full_prompt("long_term_memory_extractor", db) if scene else ""
            prompt = (template or DEFAULT_EXTRACT_PROMPT).replace(
                "{conversation_context}", conversation_context
            ).replace("{request_text}", request_text)
            llm = get_llm(streaming=False, temperature=0.1)
            response = llm.invoke(prompt)
            content = getattr(response, "content", "") or ""
            payload = parse_json_object(content)
            if not payload:
                logger.warning("长期记忆抽取未返回有效 JSON user_id={}", user_id)
                return

            data: dict = {}
            for field in EXTRACT_FIELDS:
                value = payload.get(field)
                if value is None or value == "":
                    continue
                if field in ("target_skills", "weak_topics", "interview_focus"):
                    if isinstance(value, list):
                        data[field] = [str(item)[:128] for item in value if item][:20]
                elif field == "long_term_summary":
                    data[field] = str(value)[:1000]
                else:
                    data[field] = str(value)[:128]
            if not data:
                return
            UserProfileService(UserProfileDao(db)).create_or_update(
                user_id, UserProfileUpsert(**data)
            )
            logger.info(
                "长期记忆画像已更新 user_id={} fields={}", user_id, list(data)
            )
        except Exception as exc:  # noqa: BLE001 后台任务异常只记录，不影响对话
            logger.warning("长期记忆画像更新失败 user_id={} error={}", user_id, exc)
            db.rollback()
        finally:
            db.close()
