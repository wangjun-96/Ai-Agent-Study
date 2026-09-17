"""业务层：面试记录业务逻辑（按 ID 查询详情）。

查询规则（见 prompt.md L160、L175）：
- interviews 表含 user_id 字段，获取面试记录需按 interview_id + user_id 联合查询；
- 越权访问（面试不属于当前用户）统一返回 404，避免面试 ID 被枚举。
"""
from app.core import BusinessException, get_logger
from app.dao.interview_dao import InterviewDao
from app.db.models import Interview
from app.enums.response_code import ResponseCode

logger = get_logger("interview_service")


class InterviewService:
    """面试记录业务服务：注入面试 DAO。"""

    def __init__(self, interview_dao: InterviewDao) -> None:
        self.interview_dao = interview_dao

    def get_interview(self, interview_id: int, user_id: int) -> Interview:
        """按面试 ID + 用户 ID 查询面试详情（含 qa_object）。

        越权访问统一返回 404，不向前端暴露"存在但不属于你"的语义。
        """
        interview = self.interview_dao.get_interview_by_user(interview_id, user_id)
        if interview is None:
            raise BusinessException(
                ResponseCode.INTERVIEW_NOT_FOUND,
                detail=f"interview_id={interview_id}",
            )
        logger.info("面试详情查询成功 interview_id={} user_id={}", interview_id, user_id)
        return interview
