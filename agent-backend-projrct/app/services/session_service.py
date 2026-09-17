"""业务层：会话业务逻辑（创建 / 列表 / 编辑 / 级联删除）。

Service 只处理业务逻辑，不直接操作 Session、写 SQL 语句（调用 DAO 层）。
级联删除流程（见 prompt.md L167-172）：
1. 校验会话归属当前用户；
2. 拉取会话下全部消息，解析 request_segments / response_segments 收集 resource_id；
3. 先删 MinIO 对象，再由 SessionDao 单事务删除面试记录 / 消息 / 资源元数据 / 会话。
"""
from app.core import BusinessException, get_logger
from app.core.pagination import PageParams
from app.dao.message_dao import MessageDao
from app.dao.resource_dao import ResourceDao
from app.dao.session_dao import SessionDao
from app.db.models import ChatMessage, Session as SessionModel
from app.enums.response_code import ResponseCode
from app.integrations.minio_client import MinioStorage
from app.enums.session_model import SessionModel as SessionModelEnum
from app.schemas.session import SessionCreate, SessionUpdate

logger = get_logger("session_service")


class SessionService:
    """会话业务服务：注入会话/消息/资源 DAO 与 MinIO 工具。"""

    def __init__(
        self,
        session_dao: SessionDao,
        message_dao: MessageDao,
        resource_dao: ResourceDao,
        minio_storage: MinioStorage,
    ) -> None:
        self.session_dao = session_dao
        self.message_dao = message_dao
        self.resource_dao = resource_dao
        self.minio_storage = minio_storage

    # ------------------------------------------------------------------
    # 创建 / 列表 / 编辑
    # ------------------------------------------------------------------

    def create_session(self, user_id: int, session_in: SessionCreate) -> SessionModel:
        """创建会话：title + session_model，归属当前用户。"""
        session = SessionModel(
            user_id=user_id,
            title=session_in.title,
            session_model=session_in.session_model.value,
        )
        created = self.session_dao.insert(session)
        logger.info("会话创建成功 id={} user_id={}", created.id, user_id)
        return created

    def list_sessions(
        self,
        user_id: int,
        page: PageParams,
        session_model: int | None = None,
    ) -> tuple[list[SessionModel], int]:
        """分页查询当前用户的会话列表，可按 session_model 过滤，返回 (items, total)。"""
        total = self.session_dao.count_by_user(user_id, session_model)
        items = self.session_dao.list_by_user(
            user_id, offset=page.offset, limit=page.limit, session_model=session_model
        )
        return items, total

    def update_session(
        self, session_id: int, user_id: int, update_in: SessionUpdate
    ) -> SessionModel:
        """编辑会话：支持修改 title 与 session_model，仅更新传入的非空字段。"""
        session = self.session_dao.get_session_by_user(session_id, user_id)
        if session is None:
            raise BusinessException(
                ResponseCode.SESSION_NOT_FOUND, detail=f"session_id={session_id}"
            )

        update_data: dict = {}
        if update_in.title is not None:
            update_data["title"] = update_in.title
        if update_in.session_model is not None:
            update_data["session_model"] = update_in.session_model.value

        if update_data:
            self.session_dao.update_session(session, update_data)
        logger.info("会话更新成功 id={} fields={}", session_id, list(update_data.keys()))
        return session

    # ------------------------------------------------------------------
    # 级联删除
    # ------------------------------------------------------------------

    def delete_session(
        self, session_id: int, user_id: int, session_model: SessionModelEnum
    ) -> None:
        """级联删除会话：面试记录 → 消息 → 资源（MinIO + 元数据）→ 会话。

        需校验 session_model 匹配，类型不匹配统一返回 404。
        越权访问（会话不属于当前用户）统一返回 404，避免会话 ID 被枚举。
        """
        # 1. 校验会话归属当前用户 + session_model 匹配
        session = self.session_dao.get_session_by_user(session_id, user_id)
        if session is None or session.session_model != session_model.value:
            raise BusinessException(
                ResponseCode.SESSION_NOT_FOUND, detail=f"session_id={session_id}"
            )

        # 2. 拉取会话下全部消息，解析 segments 收集 resource_id
        messages = self.message_dao.list_all_by_session(session_id)
        resource_ids = self._collect_resource_ids(messages)

        # 3. 先删 MinIO 对象（幂等，对象不存在视为成功）
        if resource_ids:
            resources = self.resource_dao.list_by_ids(resource_ids)
            self._delete_minio_objects(resources)

        # 4. 单事务删除：面试记录 → 消息 → 资源元数据 → 会话
        self.session_dao.delete_cascade(session_id, resource_ids)
        logger.info(
            "会话级联删除成功 session_id={} messages={} resources={}",
            session_id,
            len(messages),
            len(resource_ids),
        )

    @staticmethod
    def _collect_resource_ids(messages: list[ChatMessage]) -> list[int]:
        """从消息的 request_segments / response_segments 中收集全部 resource_id。

        去重后返回，避免同一资源被重复删除。
        """
        ids: set[int] = set()
        for msg in messages:
            for seg in (msg.request_segments or []) + (msg.response_segments or []):
                rid = seg.get("resource_id") if isinstance(seg, dict) else None
                if isinstance(rid, int):
                    ids.add(rid)
        return list(ids)

    def _delete_minio_objects(self, resources) -> None:
        """批量删除 MinIO 对象；路径非法或对象不存在时跳过，不阻断删除流程。"""
        for resource in resources:
            try:
                parsed = self.minio_storage.parse_storage_path(resource.storage_path)
                if parsed is not None:
                    bucket, object_key = parsed
                    self.minio_storage.delete_object(object_key, bucket)
            except Exception:
                # 单条对象删除失败只记录日志，元数据仍会被级联删除
                logger.exception(
                    "MinIO 对象删除失败 resource_id={} path={}",
                    resource.id,
                    resource.storage_path,
                )
