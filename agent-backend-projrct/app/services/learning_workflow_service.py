"""业务层：学习测评工作流服务。

职责：把 LangGraph 图编排与业务数据读写串起来——
1. 启动测评：校验会话归属、创建运行记录、执行图至 interrupt 暂停、回写出题消息；
2. 提交答案：校验运行归属与状态、恢复图执行、写入评分快照并回写原出题消息；
3. 查询运行：按用户归属校验后返回运行状态与业务快照。

图节点负责 LLM 调用与状态流转，DAO 负责持久化，本层不直接写 SQL。
"""
import uuid

from langgraph.types import Command

from app.agent.workflows.checkpoint import build_thread_config
from app.agent.workflows.learning import learning_workflow_graph
from app.core import BusinessException, get_logger
from app.db.models import ChatMessage, WorkflowRun
from app.enums.response_code import ResponseCode
from app.enums.select_model import SelectModel

logger = get_logger("learning_workflow_service")


class LearningWorkflowService:
    """学习测评工作流业务服务：出题 → 作答 → 评分 → 复盘。"""

    WORKFLOW_TYPE = "learning_quiz"

    def __init__(self, session_dao, workflow_run_dao, message_dao) -> None:
        self.session_dao = session_dao
        self.workflow_run_dao = workflow_run_dao
        self.message_dao = message_dao

    def start(
        self,
        *,
        user_id: int,
        session_id: int,
        request_text: str,
        question_count: int,
        provider: str | None,
    ) -> dict:
        """启动学习测评：生成题目并暂停在等待作答节点。

        :param user_id: 当前用户 ID
        :param session_id: 关联会话 ID（须属于当前用户）
        :param request_text: 用户需求文本
        :param question_count: 出题数量
        :param provider: 模型服务商标识
        :return: run_id、状态与题目 JSON
        """
        # 1. 会话归属校验：非本人会话统一按不存在处理，避免越权枚举
        session = self.session_dao.get_session_by_user(session_id, user_id)
        if session is None:
            raise BusinessException(
                ResponseCode.SESSION_NOT_FOUND, detail=f"session_id={session_id}"
            )

        # 2. 创建运行记录：run_id 同时作为 LangGraph thread_id
        run_id = uuid.uuid4().hex
        run = WorkflowRun(
            run_id=run_id,
            user_id=user_id,
            session_id=session_id,
            workflow_type=self.WORKFLOW_TYPE,
            status="created",
            state_json=None,
        )
        self.workflow_run_dao.insert(run)
        logger.info(
            "启动学习测评 run_id={} user_id={} session_id={} count={}",
            run_id,
            user_id,
            session_id,
            question_count,
        )

        # 3. 执行图：生成题目后停在 interrupt（wait_user_answer）
        config = build_thread_config(run_id)
        initial = {
            "run_id": run_id,
            "user_id": user_id,
            "session_id": session_id,
            "request_text": request_text,
            "provider": provider,
            "question_count": question_count,
            "status": "created",
        }
        try:
            learning_workflow_graph.invoke(initial, config)
        except Exception as exc:
            logger.error("学习测评出题失败 run_id={} error={}", run_id, exc)
            self.workflow_run_dao.update_status(
                run, "failed", error_message=str(exc)[:512]
            )
            raise

        # 4. 读取暂停时的状态快照并落库
        snapshot = dict(learning_workflow_graph.get_state(config).values)
        self.workflow_run_dao.update_status(
            run, "waiting_answer", state_json=snapshot
        )

        # 5. 写出题消息：前端据此渲染答题卡，request_id 约定为 {run_id}:quiz
        self.message_dao.insert_message(
            ChatMessage(
                user_id=user_id,
                session_id=session_id,
                select_model=int(SelectModel.PRACTICE),
                request_id=f"{run_id}:quiz",
                request_text=request_text,
                response_text="已完成出题，请完成后提交答案。",
                request_segments=[],
                response_payload=snapshot.get("quiz"),
            )
        )
        logger.info("学习测评出题完成 run_id={} status=waiting_answer", run_id)
        return {
            "run_id": run_id,
            "status": "waiting_answer",
            "quiz": snapshot.get("quiz", {}),
        }

    def submit_answer(self, *, user_id: int, run_id: str, answers: list[dict]) -> dict:
        """提交答案：恢复图执行，完成评分与复盘。

        :param user_id: 当前用户 ID
        :param run_id: 工作流运行 ID
        :param answers: 作答列表，每项含 question_id / value
        :return: 得分、评分明细、薄弱点、复盘建议与 A2A 信封
        """
        # 1. 运行记录归属校验
        run = self.workflow_run_dao.get_by_run_id(run_id)
        if run is None or run.user_id != user_id:
            raise BusinessException(
                ResponseCode.PARAM_INVALID, detail=f"工作流不存在 run_id={run_id}"
            )

        # 2. 类型与状态校验：仅等待作答状态可提交
        if run.workflow_type != self.WORKFLOW_TYPE or run.status != "waiting_answer":
            raise BusinessException(
                ResponseCode.PARAM_INVALID, detail="当前工作流状态不可提交答案"
            )

        # 3. 标记评分中并恢复图执行（resume 值即 interrupt 的返回值）
        self.workflow_run_dao.update_status(run, "grading")
        config = build_thread_config(run_id)
        logger.info("提交学习测评答案 run_id={} answers={}", run_id, len(answers))
        try:
            learning_workflow_graph.invoke(Command(resume=answers), config)
        except Exception as exc:
            logger.error("学习测评评分失败 run_id={} error={}", run_id, exc)
            self.workflow_run_dao.update_status(
                run, "failed", error_message=str(exc)[:512]
            )
            raise

        # 4. 读取最终状态快照并落库
        snapshot = dict(learning_workflow_graph.get_state(config).values)
        self.workflow_run_dao.update_status(
            run, "completed", state_json=snapshot, completed=True
        )

        # 5. 回写原出题消息：用评分点评文本替换答题卡提示
        message = self.message_dao.get_by_request_id(f"{run_id}:quiz")
        if message is not None:
            evaluation = snapshot.get("evaluation") or {}
            display_text = str(evaluation.get("display_text") or "").strip()
            if len(display_text) < 20:
                display_text = (
                    f"本次测评得分 {snapshot.get('score', 0)} 分。\n"
                    f"{snapshot.get('review', '')}"
                ).strip()
            self.message_dao.update_response(
                message,
                response_text=display_text or "测评已完成",
                response_payload=None,
            )

        logger.info(
            "学习测评评分完成 run_id={} score={}", run_id, snapshot.get("score", 0)
        )
        return {
            "run_id": run_id,
            "status": "completed",
            "score": snapshot.get("score", 0),
            "evaluation": snapshot.get("evaluation", {}),
            "weaknesses": snapshot.get("weaknesses", []),
            "review": snapshot.get("review", ""),
            "a2a_envelope": snapshot.get("a2a_envelope", {}),
        }

    def get_run(self, *, user_id: int, run_id: str) -> dict:
        """查询运行状态与业务快照（含归属校验）。

        :param user_id: 当前用户 ID
        :param run_id: 工作流运行 ID
        :return: run_id、状态与状态快照
        """
        run = self.workflow_run_dao.get_by_run_id(run_id)
        if run is None or run.user_id != user_id:
            raise BusinessException(
                ResponseCode.PARAM_INVALID, detail=f"工作流不存在 run_id={run_id}"
            )
        return {
            "run_id": run.run_id,
            "status": run.status,
            "state": run.state_json,
        }
