"""业务层：聊天消息业务逻辑（分页查询）。

核心语义（见 prompt.md L154-160）：
- request_text / response_text 为聊天正文主字段；
- request_segments / response_segments 只存附件段；
- 消息返回需包含 status 与 interview_id，供前端面试卡片逻辑使用。

status 取自关联面试记录（interviews.status），非面试消息为 null。
"""
from app.core import BusinessException, get_logger
from app.core.pagination import PageParams
from app.dao.interview_dao import InterviewDao
from app.dao.message_dao import MessageDao
from app.dao.session_dao import SessionDao
from app.db.models import ChatMessage
from app.enums.response_code import ResponseCode

logger = get_logger("message_service")


class MessageService:
    """消息业务服务：注入会话/消息/面试 DAO。"""

    def __init__(
        self,
        session_dao: SessionDao,
        message_dao: MessageDao,
        interview_dao: InterviewDao,
    ) -> None:
        self.session_dao = session_dao
        self.message_dao = message_dao
        self.interview_dao = interview_dao

    def list_messages(
        self, session_id: int, user_id: int, page: PageParams
    ) -> tuple[list[ChatMessage], int, dict[int, int]]:
        """分页查询会话下的消息，并回填关联面试的 status。

        :return: (messages, total, interview_status_map)
                 interview_status_map: {interview_id: status}
        """
        # 校验会话归属当前用户（越权统一返回 404）
        session = self.session_dao.get_session_by_user(session_id, user_id)
        if session is None:
            raise BusinessException(
                ResponseCode.SESSION_NOT_FOUND, detail=f"session_id={session_id}"
            )

        total = self.message_dao.count_by_session(session_id)
        messages = self.message_dao.list_by_session(
            session_id, offset=page.offset, limit=page.limit
        )

        # 收集本页消息涉及的 interview_id，批量回填面试状态
        interview_ids = [
            msg.interview_id for msg in messages if msg.interview_id is not None
        ]
        status_map = self.interview_dao.list_status_by_ids(interview_ids)

        logger.info(
            "消息列表查询 session_id={} page={} page_size={} total={}",
            session_id,
            page.page,
            page.page_size,
            total,
        )
        return messages, total, status_map
