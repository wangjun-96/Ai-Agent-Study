"""业务层：MinIO 对象存储上传（当前运行逻辑）。

架构：元数据与文件解耦——
- 原文件通过 MinioStorage.put_object 存入 MinIO；
- 资源元数据写入 MySQL resources 表（经 ResourceDao）；
- 同一用户下相同内容（MD5）只存一份：代码层预查，数据库唯一键兜底。

业务规则（见 prompt.md L112-149）：
1. storage_scene=2：只提取文件内容，不上传原文件、不写元数据，
   提取文本由调用方写入 chat_messages.file_extracted_text；
2. storage_scene=0/1：上传 MinIO 并按场景计算 expire_time（1 个月 / 2 小时）；
3. upload_purpose=1 且资源为图片时，回写 users.avatar；
4. storage_path 格式：minio://{bucket}/{object_key}。

注册场景（用户尚未创建）采用两阶段调用：
prepare_avatar 先校验图片（不上传、不写库）→ 建号成功后 commit_avatar
完成 MinIO 上传、元数据落库与头像回写，保证「头像非法」不产生孤儿账号；
头像被 users.avatar 永久引用，expire_time=None（不参与过期清理）。
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.core import BusinessException, get_logger, settings
from app.dao.resource_dao import ResourceDao
from app.db.models import Resource, User
from app.enums.resource_type import ResourceType
from app.enums.response_code import ResponseCode
from app.enums.storage_scene import StorageScene
from app.enums.upload_purpose import UploadPurpose
from app.integrations.minio_client import MinioStorage
from app.schemas.file import ResourceUploadResult
from app.services.user_service import UserService

logger = get_logger("upload_service_minio")

# 允许上传的扩展名白名单：扩展名（小写，含点）→ 资源类型
ALLOWED_EXTENSIONS: dict[str, ResourceType] = {
    # 图片
    ".jpg": ResourceType.IMAGE,
    ".jpeg": ResourceType.IMAGE,
    ".png": ResourceType.IMAGE,
    ".gif": ResourceType.IMAGE,
    ".webp": ResourceType.IMAGE,
    ".bmp": ResourceType.IMAGE,
    # 音频
    ".mp3": ResourceType.AUDIO,
    ".wav": ResourceType.AUDIO,
    ".m4a": ResourceType.AUDIO,
    ".aac": ResourceType.AUDIO,
    ".ogg": ResourceType.AUDIO,
    ".flac": ResourceType.AUDIO,
    # 文件（文档）
    ".pdf": ResourceType.FILE,
    ".doc": ResourceType.FILE,
    ".docx": ResourceType.FILE,
    ".xls": ResourceType.FILE,
    ".xlsx": ResourceType.FILE,
    ".ppt": ResourceType.FILE,
    ".pptx": ResourceType.FILE,
    ".txt": ResourceType.FILE,
    ".md": ResourceType.FILE,
    ".csv": ResourceType.FILE,
}

# 可直接按文本解码提取内容的扩展名（storage_scene=2 时使用）
TEXT_EXTRACT_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".csv"})


@dataclass
class PreparedResource:
    """已读入内存并通过校验、等待存储的资源（注册两阶段流程的中间产物）。"""

    content: bytes
    ext: str
    resource_type: ResourceType
    original_name: str
    content_type: str | None


class MinioUploadService:
    """MinIO 上传业务服务：校验、MD5 去重、场景分流、头像回写。"""

    def __init__(
        self,
        user_service: UserService,
        resource_dao: ResourceDao,
        minio_storage: MinioStorage,
    ) -> None:
        self.user_service = user_service
        self.resource_dao = resource_dao
        self.minio_storage = minio_storage

    # ------------------------------------------------------------------
    # 已认证通用上传：按场景分流
    # ------------------------------------------------------------------

    async def upload(
        self,
        user: User,
        upload_file: UploadFile,
        storage_scene: StorageScene,
        upload_purpose: UploadPurpose,
    ) -> ResourceUploadResult:
        """上传入口：校验后按存储场景分流。

        :param user: 当前登录用户（JWT 鉴权依赖解析）
        :param upload_file: multipart 表单字段 file
        :param storage_scene: 存储场景（0 长过期 / 1 短过期 / 2 只提取内容）
        :param upload_purpose: 上传用途（0 普通资源 / 1 头像）
        :return: 上传结果（元数据、预签名 URL、提取文本等）
        """
        # expect_type=None：文件 / 图片 / 音频均允许
        prepared = await self._prepare(
            upload_file, expect_type=None, user_id=user.id
        )
        # 是否触发头像回写：用途为头像且资源为图片
        is_avatar = (
            upload_purpose == UploadPurpose.AVATAR
            and prepared.resource_type == ResourceType.IMAGE
        )

        # 场景 2：只提取内容，不上传原文件、不写元数据
        if storage_scene == StorageScene.EXTRACT_ONLY:
            logger.info(
                "只提取内容 user_id={} type={} size={}",
                user.id,
                prepared.resource_type.value,
                len(prepared.content),
            )
            return ResourceUploadResult(
                resource_id=None,
                resource_type=prepared.resource_type,
                storage_scene=storage_scene,
                upload_purpose=upload_purpose,
                file_name=prepared.original_name,
                file_hash=hashlib.md5(prepared.content).hexdigest(),  # noqa: S324
                storage_path="",
                url=None,
                expire_time=None,
                is_avatar=False,
                extracted_text=self._extract_text(prepared.content, prepared.ext),
                content_type=prepared.content_type,
                size=len(prepared.content),
                duplicated=False,
            )

        # 场景 0/1：上传 MinIO 并按场景计算过期时间
        expire_time = self._calc_expire_time(storage_scene)
        return self._persist(
            user,
            prepared,
            storage_scene=storage_scene,
            upload_purpose=upload_purpose,
            expire_time=expire_time,
            is_avatar=is_avatar,
        )

    # ------------------------------------------------------------------
    # 注册场景两阶段接口：先校验头像，建号成功后再上传
    # ------------------------------------------------------------------

    async def prepare_avatar(
        self, upload_file: UploadFile, *, user_id: int | None = None
    ) -> PreparedResource:
        """注册第一阶段：读入并校验头像图片（仅图片），不上传、不写库。

        :param upload_file: 注册表单中的 avatar 文件
        :param user_id: 日志用用户标识（注册成功前可能还没有用户 ID）
        :return: 校验通过的待存储资源
        """
        return await self._prepare(
            upload_file, expect_type=ResourceType.IMAGE, user_id=user_id
        )

    def commit_avatar(
        self, user: User, prepared: PreparedResource
    ) -> ResourceUploadResult:
        """注册第二阶段：建号成功后上传 MinIO、落元数据并回写 users.avatar。

        头像被 users.avatar 永久引用：storage_scene=LONG 表示存储层级，
        expire_time=None 使其不参与过期清理（否则到期删除会导致头像失效）。
        """
        return self._persist(
            user,
            prepared,
            storage_scene=StorageScene.LONG,
            upload_purpose=UploadPurpose.AVATAR,
            expire_time=None,
            is_avatar=True,
        )

    # ------------------------------------------------------------------
    # 内部共用：校验准备 / 存储提交
    # ------------------------------------------------------------------

    async def _prepare(
        self,
        upload_file: UploadFile,
        *,
        expect_type: ResourceType | None,
        user_id: int | None,
    ) -> PreparedResource:
        """读入文件并完成空文件 / 大小 / 类型全部校验，返回待存储资源。

        :param expect_type: 限定资源分类；None 表示全部允许（通用上传），
                            传入 IMAGE 表示仅接受图片（注册头像）
        """
        content = await upload_file.read()
        # 空文件拦截
        if not content:
            raise BusinessException(ResponseCode.FILE_EMPTY)
        # 大小限制
        if len(content) > settings.UPLOAD_MAX_SIZE:
            logger.warning(
                "上传文件超大小限制 user_id={} size={} limit={}",
                user_id,
                len(content),
                settings.UPLOAD_MAX_SIZE,
            )
            raise BusinessException(
                ResponseCode.FILE_TOO_LARGE,
                detail=f"size={len(content)}, limit={settings.UPLOAD_MAX_SIZE}",
            )

        original_name = upload_file.filename or ""
        ext = Path(original_name).suffix.lower()
        resource_type = ALLOWED_EXTENSIONS.get(ext)
        # 扩展名不在白名单 / 与调用方限定类型不符 / 与声明 MIME 不一致，统一拒绝
        if (
            resource_type is None
            or (expect_type is not None and resource_type != expect_type)
            or not self._content_type_matches(resource_type, upload_file.content_type)
        ):
            logger.info(
                "上传文件类型不允许 user_id={} filename={} content_type={} expect={}",
                user_id,
                original_name,
                upload_file.content_type,
                expect_type,
            )
            raise BusinessException(
                ResponseCode.FILE_TYPE_NOT_ALLOWED,
                detail=f"filename={original_name}, content_type={upload_file.content_type}",
            )

        return PreparedResource(
            content=content,
            ext=ext,
            resource_type=resource_type,
            original_name=original_name,
            content_type=upload_file.content_type,
        )

    def _persist(
        self,
        user: User,
        prepared: PreparedResource,
        *,
        storage_scene: StorageScene,
        upload_purpose: UploadPurpose,
        expire_time: datetime | None,
        is_avatar: bool,
    ) -> ResourceUploadResult:
        """去重预查 → put_object 上传 MinIO → 元数据落库 → 组装结果。"""
        # MD5 仅用于内容去重，非安全场景
        file_hash = hashlib.md5(prepared.content).hexdigest()  # noqa: S324

        # 代码层预查去重：同用户 + 同 MD5 已存在则直接复用
        existing = self.resource_dao.get_by_hash(file_hash, user.id)
        if existing is not None:
            return self._build_result(
                existing,
                prepared=prepared,
                storage_scene=storage_scene,
                upload_purpose=upload_purpose,
                duplicated=True,
                is_avatar=is_avatar,
                user=user,
            )

        # 上传对象到 MinIO：object_key 按用户分目录，内容 MD5 命名
        object_key = f"{user.id}/{file_hash}{prepared.ext}"
        self.minio_storage.put_object(
            object_key,
            prepared.content,
            content_type=prepared.content_type or "application/octet-stream",
        )
        storage_path = self.minio_storage.build_storage_path(object_key)

        resource = Resource(
            resource_type=prepared.resource_type.value,
            storage_scene=storage_scene.value,
            update_purpose=upload_purpose.value,
            file_name=prepared.original_name,
            file_hash=file_hash,
            storage_path=storage_path,
            user_id=user.id,
            expire_time=expire_time,
        )
        try:
            self.resource_dao.insert(resource)
        except IntegrityError as exc:
            # 并发兜底：唯一键冲突说明他请求已写入，回查复用已有元数据
            winner = self.resource_dao.get_by_hash(file_hash, user.id)
            if winner is None:
                raise BusinessException(
                    ResponseCode.RESOURCE_DUPLICATE,
                    detail=f"file_hash={file_hash}",
                ) from exc
            return self._build_result(
                winner,
                prepared=prepared,
                storage_scene=storage_scene,
                upload_purpose=upload_purpose,
                duplicated=True,
                is_avatar=is_avatar,
                user=user,
            )

        logger.info(
            "MinIO 上传成功 user_id={} type={} purpose={} size={} path={}",
            user.id,
            prepared.resource_type.value,
            upload_purpose.value,
            len(prepared.content),
            storage_path,
        )
        return self._build_result(
            resource,
            prepared=prepared,
            storage_scene=storage_scene,
            upload_purpose=upload_purpose,
            duplicated=False,
            is_avatar=is_avatar,
            user=user,
        )

    @staticmethod
    def _content_type_matches(
        resource_type: ResourceType, content_type: str | None
    ) -> bool:
        """校验扩展名分类与请求声明 MIME 是否一致；未声明 MIME 时放行。"""
        if not content_type:
            return True
        if resource_type == ResourceType.IMAGE:
            return content_type.startswith("image/")
        if resource_type == ResourceType.AUDIO:
            return content_type.startswith("audio/")
        # 文件：拦截伪装成图片/音频的情况
        return not content_type.startswith(("image/", "audio/"))

    @staticmethod
    def _extract_text(content: bytes, ext: str) -> str | None:
        """提取文件文本：纯文本类扩展名按 UTF-8 解码，其余类型暂不支持返回 None。"""
        if ext not in TEXT_EXTRACT_EXTENSIONS:
            # PDF/Office 等二进制文档需 pypdf、python-docx 等专用库，暂不提取
            return None
        return content.decode("utf-8", errors="ignore")

    @staticmethod
    def _calc_expire_time(storage_scene: StorageScene) -> datetime:
        """按存储场景计算过期时间：长过期 1 个月，短过期 2 小时。"""
        now = datetime.now()
        if storage_scene == StorageScene.LONG:
            return now + timedelta(days=settings.RESOURCE_LONG_EXPIRE_DAYS)
        return now + timedelta(hours=settings.RESOURCE_SHORT_EXPIRE_HOURS)

    def _build_result(
        self,
        resource: Resource,
        *,
        prepared: PreparedResource,
        storage_scene: StorageScene,
        upload_purpose: UploadPurpose,
        duplicated: bool,
        is_avatar: bool,
        user: User,
    ) -> ResourceUploadResult:
        """组装上传结果；按需回写头像并生成预签名下载 URL。"""
        storage_path = resource.storage_path
        # 头像回写：仅当前请求用途为头像且资源为图片时执行
        if is_avatar:
            self.user_service.update_avatar(user, storage_path)

        # 从存储路径直接生成预签名下载 URL；路径非法时不下发 URL
        url = self.minio_storage.presigned_url_from_path(
            storage_path, settings.MINIO_PRESIGN_EXPIRY_SECONDS
        )
        return ResourceUploadResult(
            resource_id=resource.id,
            resource_type=prepared.resource_type,
            storage_scene=storage_scene,
            upload_purpose=upload_purpose,
            file_name=prepared.original_name,
            file_hash=resource.file_hash,
            storage_path=storage_path,
            url=url,
            expire_time=resource.expire_time,
            is_avatar=is_avatar,
            extracted_text=None,
            content_type=prepared.content_type,
            size=len(prepared.content),
            duplicated=duplicated,
        )
