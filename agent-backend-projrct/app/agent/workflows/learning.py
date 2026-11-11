"""学习测评工作流：LangGraph 编排、checkpoint 保存执行现场。

编排链路：generate_quiz → wait_user_answer → evaluate_answer → finalize_result → END。

- 出题节点调用出题智能体生成结构化题目 JSON；
- 作答节点通过 interrupt 暂停图执行，等待前端提交答案后由 Command(resume=...) 恢复；
- 评分节点调用评测智能体逐题判分，产出总分、薄弱点、复盘建议与 A2A 信封；
- 执行现场由全局 MemorySaver checkpoint 保存，业务快照由服务层写入 workflow_runs。
"""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from sqlalchemy.orm import Session

from app.agent.a2a import A2AEnvelope
from app.agent.workflows.checkpoint import get_workflow_checkpointer
from app.agent.workflows.state import LearningWorkflowState
from app.core import SystemException, get_logger
from app.dao.prompt_template_dao import PromptTemplateDao
from app.dao.user_profile_dao import UserProfileDao
from app.db.database import SessionLocal
from app.enums.response_code import ResponseCode
from app.integrations.redis_client import get_redis_cache
from app.llm.llm import get_llm
from app.services.prompt_template_service import PromptTemplateManager
from app.services.prompt_variable_service import PromptVariableService
from app.utils.json_utils import parse_json_object

logger = get_logger("learning_workflow")

# 工作流类型标识，与服务层、workflow_runs.workflow_type 保持一致
WORKFLOW_TYPE = "learning_quiz"

# 出题/评分默认提示词：数据库未配置模板时兜底使用
DEFAULT_QUIZ_PROMPT = (
    "你是学习测评出题助手。请围绕用户需求生成结构化的单项/多项/主观练习题，"
    "题目要有明确考查点，避免重复与歧义，用简洁中文表述。"
)
DEFAULT_EVALUATE_PROMPT = (
    "你是学习测评评分助手。请根据题目、标准答案与用户作答逐题判分，"
    "给出总分、逐题点评、薄弱知识点与学习建议，用简洁中文表述。"
)

# 出题输出格式约束：只输出 JSON 对象，前端按结构渲染答题卡
QUIZ_OUTPUT_FORMAT = """输出要求：
1. 只输出一个 JSON 对象，不要输出 Markdown 代码围栏或任何解释文字；
2. 结构为 {"title": "测评标题", "questions": [{"question_id": "q1", "type": "radio", "question": "题干", "options": [{"label": "A", "value": "A", "text": "选项内容"}], "answer": "A", "explanation": "解析"}]}；
3. type 只能是 radio（单选）、checkbox（多选）、textarea（主观题）；
4. radio / checkbox 必须提供 2-4 个 options，textarea 不需要 options；
5. 题号从 q1 开始连续递增。"""

# 评分输出格式约束：只输出 JSON 对象，服务层从中取 display_text / score 等字段
EVALUATE_OUTPUT_FORMAT = """输出要求：
1. 只输出一个 JSON 对象，不要输出 Markdown 代码围栏或任何解释文字；
2. 结构为 {"display_text": "面向用户的中文点评文本", "score": 0-100 的整数, "items": [{"question_id": "q1", "correct": true, "comment": "逐题点评"}], "weaknesses": ["薄弱知识点"], "review": "整体学习建议"}。"""


def _build_prompt(agent_name: str, user_id: int, db: Session, fallback: str) -> str:
    """构建系统提示词：模板 + 用户画像变量注入，模板缺失时使用兜底提示词。

    :param agent_name: 智能体名称（须存在于 AGENT_CONFIG）
    :param user_id: 用户 ID，用于注入画像变量
    :param db: 数据库 Session
    :param fallback: 模板缺失时的默认提示词
    :return: 最终系统提示词
    """
    manager = PromptTemplateManager(PromptTemplateDao(db), get_redis_cache())
    prompt = PromptVariableService(UserProfileDao(db)).build_system_prompt(
        manager, agent_name, user_id
    )
    return prompt or fallback


def prepare_learning_context(state: LearningWorkflowState) -> dict[str, Any]:
    """准备节点：只做轻量状态标记，实际数据装载由后续节点完成。"""
    logger.info("学习测评工作流开始 run_id={} user_id={}", state.get("run_id"), state.get("user_id"))
    return {"status": "preparing"}


def generate_quiz(state: LearningWorkflowState) -> dict[str, Any]:
    """出题节点：调用出题智能体生成结构化题目 JSON，解析失败抛系统异常。"""
    user_id = int(state.get("user_id") or 0)
    question_count = int(state.get("question_count") or 5)
    request_text = str(state.get("request_text") or "")

    db = SessionLocal()
    try:
        system_prompt = (
            _build_prompt("quiz_generate_workflow", user_id, db, DEFAULT_QUIZ_PROMPT)
            + "\n\n"
            + QUIZ_OUTPUT_FORMAT
        )
    finally:
        db.close()

    user_content = f"出题数量：{question_count}\n用户需求：{request_text}"
    llm = get_llm(provider=state.get("provider"), streaming=False, temperature=0.3)
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]
    )

    quiz = parse_json_object(getattr(response, "content", "") or "")
    if (
        not isinstance(quiz, dict)
        or not isinstance(quiz.get("questions"), list)
        or not quiz.get("questions")
    ):
        logger.warning("出题结果解析失败 run_id={}", state.get("run_id"))
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="出题结果解析失败，请稍后重试",
            detail="quiz json invalid",
        )

    logger.info(
        "出题完成 run_id={} questions={}",
        state.get("run_id"),
        len(quiz.get("questions") or []),
    )
    return {"quiz": quiz, "status": "waiting_answer"}


def _normalize_answers(raw: Any) -> list[dict[str, Any]]:
    """规范化作答数据：兼容 {answers: [...]} 字典、列表两种输入，其余返回空列表。"""
    if isinstance(raw, dict) and isinstance(raw.get("answers"), list):
        return list(raw["answers"])
    if isinstance(raw, list):
        return list(raw)
    return []


def wait_user_answer(state: LearningWorkflowState) -> dict[str, Any]:
    """等待作答节点：通过 interrupt 暂停图执行，恢复时接收前端提交的答案列表。"""
    answers = interrupt({"quiz": state.get("quiz", {})})
    normalized = _normalize_answers(answers)
    logger.info("收到用户作答 run_id={} answers={}", state.get("run_id"), len(normalized))
    return {"answers": normalized, "status": "grading"}


def create_evaluate_and_review_node(state: LearningWorkflowState) -> dict[str, Any]:
    """评分节点：调用评测智能体逐题判分，产出总分、薄弱点、复盘建议与 A2A 信封。"""
    user_id = int(state.get("user_id") or 0)

    db = SessionLocal()
    try:
        system_prompt = (
            _build_prompt("learning_evaluator", user_id, db, DEFAULT_EVALUATE_PROMPT)
            + "\n\n"
            + EVALUATE_OUTPUT_FORMAT
        )
    finally:
        db.close()

    user_content = json.dumps(
        {"quiz": state.get("quiz", {}), "answers": state.get("answers", [])},
        ensure_ascii=False,
    )
    llm = get_llm(provider=state.get("provider"), streaming=False, temperature=0.3)
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]
    )

    payload = parse_json_object(getattr(response, "content", "") or "")
    if not isinstance(payload, dict):
        logger.warning("评分结果解析失败 run_id={}", state.get("run_id"))
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="评分结果解析失败，请稍后重试",
            detail="evaluation json invalid",
        )

    score = int(payload.get("score") or 0)
    score = max(0, min(100, score))
    weaknesses = [
        str(item)[:128] for item in (payload.get("weaknesses") or []) if item
    ][:5]
    review = str(payload.get("review") or "").strip()
    evaluation = payload

    # A2A 信封：存在薄弱点时交由 difficulty_learner 继续生成专项练习
    has_weakness = bool(weaknesses)
    envelope = A2AEnvelope(
        from_agent="learning_evaluator",
        payload_type="weak_points",
        payload={"score": score, "weaknesses": weaknesses, "review": review},
        next_agent="difficulty_learner" if has_weakness else None,
        confidence=0.9 if has_weakness else 0.4,
    )

    logger.info(
        "评分完成 run_id={} score={} weaknesses={}",
        state.get("run_id"),
        score,
        len(weaknesses),
    )
    return {
        "evaluation": evaluation,
        "score": score,
        "weaknesses": weaknesses,
        "review": review,
        "a2a_envelope": envelope.model_dump(),
    }


# 兼容别名：图节点注册名为 evaluate_answer，业务/测试可直接引用该名称
evaluate_answer = create_evaluate_and_review_node


def finalize_result(state: LearningWorkflowState) -> dict[str, Any]:
    """收尾节点：标记工作流完成。"""
    logger.info("学习测评工作流完成 run_id={} score={}", state.get("run_id"), state.get("score"))
    return {"status": "completed"}


def build_learning_workflow():
    """构建并编译学习测评工作流图（checkpoint 保存执行现场）。"""
    graph = StateGraph(LearningWorkflowState)
    graph.add_node("prepare_learning_context", prepare_learning_context)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("wait_user_answer", wait_user_answer)
    graph.add_node("evaluate_answer", create_evaluate_and_review_node)
    graph.add_node("finalize_result", finalize_result)
    graph.set_entry_point("prepare_learning_context")
    graph.add_edge("prepare_learning_context", "generate_quiz")
    graph.add_edge("generate_quiz", "wait_user_answer")
    graph.add_edge("wait_user_answer", "evaluate_answer")
    graph.add_edge("evaluate_answer", "finalize_result")
    graph.add_edge("finalize_result", END)
    return graph.compile(checkpointer=get_workflow_checkpointer())


# 模块级图实例：服务层直接 import 复用，避免每次请求重复编译
learning_workflow_graph = build_learning_workflow()
