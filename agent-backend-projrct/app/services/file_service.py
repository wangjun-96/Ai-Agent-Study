"""业务层：通用文件上传。

业务规则（见 prompt.md）：
1. 接口必须登录后调用，文件按当前登录用户 ID 分目录存储：uploads/{user_id}/；
2. 存储文件名使用文件内容的 MD5 哈希值，相同内容天然去重，不重复落盘；
3. 自动判断文件类型：
   - 图片：保存文件，并更新 users.avatar 字段；
   - 文档：只保存文件。

注册接口（匿名、尚未有用户实体）复用本服务时采用两阶段调用：
prepare_avatar 先读入并校验头像（不落盘、不写库）→ 注册业务创建用户成功后
再 commit_avatar 落盘并回写头像，保证「头像非法」时不会残留已创建的孤儿账号。

类型判断以文件扩展名白名单为准，并与请求声明的 content_type 做一致性校验，
防止篡改扩展名绕过限制；存储路径只含数字用户目录与 MD5 文件名，无路径穿越风险。
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core import BusinessException, get_logger, settings
from app.db.models import User
from app.enums.file_type import FileType
from app.enums.response_code import ResponseCode
from app.schemas.file import FileUploadResult
from app.services.user_service import UserService

logger = get_logger("file_service")

# 允许上传的扩展名白名单：扩展名（小写，含点）→ 业务分类
ALLOWED_EXTENSIONS: dict[str, FileType] = {
    # 图片：上传成功后回写用户头像
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".png": FileType.IMAGE,
    ".gif": FileType.IMAGE,
    ".webp": FileType.IMAGE,
    ".bmp": FileType.IMAGE,
    # 文档：仅保存文件
    ".pdf": FileType.DOCUMENT,
    ".doc": FileType.DOCUMENT,
    ".docx": FileType.DOCUMENT,
    ".xls": FileType.DOCUMENT,
    ".xlsx": FileType.DOCUMENT,
    ".ppt": FileType.DOCUMENT,
    ".pptx": FileType.DOCUMENT,
    ".txt": FileType.DOCUMENT,
    ".md": FileType.DOCUMENT,
    ".csv": FileType.DOCUMENT,
}


@dataclass
class PreparedUpload:
    """已读入内存并通过校验、等待落盘的上传文件（注册两阶段流程的中间产物）。"""

    content: bytes
    ext: str
    file_type: FileType
    original_name: str
    content_type: str | None


class FileService:
    """文件上传业务服务：类型校验、MD5 去重落盘、图片回写头像。"""

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    # ------------------------------------------------------------------
    # 已认证通用上传：图片回写头像，文档仅保存
    # ------------------------------------------------------------------

    async def upload(self, user: User, upload_file: UploadFile) -> FileUploadResult:
        """保存上传文件，并按类型决定是否更新用户头像。

        :param user: 当前登录用户（由 JWT 鉴权依赖解析）
        :param upload_file: FastAPI 上传文件对象（multipart 表单字段 file）
        :return: 上传结果（访问 URL、文件类型、大小等）
        """
        # expect_type=None：图片 / 文档均允许，按扩展名自动分类
        prepared = await self._prepare(upload_file, expect_type=None, user_id=user.id)
        return self._commit(user, prepared)

    # ------------------------------------------------------------------
    # 注册场景两阶段接口：先校验头像，建号成功后再落盘
    # ------------------------------------------------------------------

    async def prepare_avatar(
        self, upload_file: UploadFile, *, user_id: int | None = None
    ) -> PreparedUpload:
        """注册第一阶段：读入并校验头像图片（仅图片），不落盘、不写库。

        :param upload_file: 注册表单中的 avatar 文件
        :param user_id: 日志用用户标识（注册成功前可能还没有用户 ID）
        :return: 校验通过的待落盘文件内容
        """
        return await self._prepare(
            upload_file, expect_type=FileType.IMAGE, user_id=user_id
        )

    def commit_avatar(self, user: User, prepared: PreparedUpload) -> FileUploadResult:
        """注册第二阶段：用户创建成功后落盘头像并回写 users.avatar。"""
        return self._commit(user, prepared)

    # ------------------------------------------------------------------
    # 内部共用：校验准备 / 落盘提交
    # ------------------------------------------------------------------

    async def _prepare(
        self,
        upload_file: UploadFile,
        *,
        expect_type: FileType | None,
        user_id: int | None,
    ) -> PreparedUpload:
        """读入文件并完成空文件 / 大小 / 类型全部校验，返回待落盘内容。

        :param expect_type: 限定文件分类；None 表示图片与文档均允许（通用上传），
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
        file_type = ALLOWED_EXTENSIONS.get(ext)
        # 扩展名不在白名单 / 与声明的 MIME 分类不一致 / 与调用方限定类型不符，统一拒绝
        if (
            file_type is None
            or (expect_type is not None and file_type != expect_type)
            or not self._content_type_matches(file_type, upload_file.content_type)
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

        return PreparedUpload(
            content=content,
            ext=ext,
            file_type=file_type,
            original_name=original_name,
            content_type=upload_file.content_type,
        )

    def _commit(self, user: User, prepared: PreparedUpload) -> FileUploadResult:
        """把校验通过的文件按 MD5 去重落盘；图片同步回写用户 avatar 字段。"""
        # 以内容 MD5 作为存储文件名：内容相同则路径相同，实现去重
        digest = hashlib.md5(prepared.content).hexdigest()  # noqa: S324  # MD5 仅用于去重，非安全场景
        user_dir = settings.upload_root / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{digest}{prepared.ext}"
        target_path = user_dir / stored_name
        # 文件已存在说明同内容此前已上传，直接复用，不重复写盘
        if not target_path.exists():
            target_path.write_bytes(prepared.content)

        # 访问 URL：/uploads/{user_id}/{md5}.ext，由 StaticFiles 挂载提供服务
        url = (
            f"{settings.UPLOAD_URL_PREFIX.rstrip('/')}"
            f"/{user.id}/{stored_name}"
        )

        # 图片：保存成功后回写用户 avatar 字段；文档：仅保存
        is_avatar = prepared.file_type == FileType.IMAGE
        if is_avatar:
            self.user_service.update_avatar(user, url)

        logger.info(
            "文件上传成功 user_id={} type={} size={} stored={}",
            user.id,
            prepared.file_type.value,
            len(prepared.content),
            url,
        )
        return FileUploadResult(
            url=url,
            file_type=prepared.file_type,
            is_avatar=is_avatar,
            original_name=prepared.original_name,
            stored_name=stored_name,
            content_type=prepared.content_type,
            size=len(prepared.content),
        )

    @staticmethod
    def _content_type_matches(
        file_type: FileType, content_type: str | None
    ) -> bool:
        """校验扩展名分类与请求声明的 MIME 类型是否一致；未声明 MIME 时放行。"""
        if not content_type:
            return True
        if file_type == FileType.IMAGE:
            return content_type.startswith("image/")
        # 文档类型 MIME 较分散（pdf/office/text），仅拦截明显伪装成图片的情况
        return not content_type.startswith("image/")
