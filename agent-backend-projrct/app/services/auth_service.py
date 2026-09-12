"""业务层：认证模块业务逻辑。

- Service 只处理业务逻辑，数据操作复用 UserService（进而走 DAO 层），不直接操作 Session。
- 注册流程：先做弱密码校验，再复用 UserService.create_user 完成唯一性校验与入库，
  密码哈希、用户名重复等逻辑无需重复实现。
- 业务错误统一抛 BusinessException，由全局异常处理器捕获。
"""
from app.core import BusinessException, get_logger
from app.db.models import User
from app.enums.response_code import ResponseCode
from app.schemas.auth import RegisterRequest
from app.security import validate_password_strength
from app.services.user_service import UserService

logger = get_logger("auth_service")


class AuthService:
    """认证业务服务：通过构造函数注入 UserService，复用其用户数据能力。"""

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    def register(self, user_in: RegisterRequest) -> User:
        """用户注册：弱密码校验通过后，复用 UserService.create_user 入库。

        :param user_in: 注册请求（username/password 已通过 Pydantic 结构校验）
        :return: 新创建的用户 ORM 实例（密码为 bcrypt 哈希，不含明文）
        """
        # 弱密码业务校验：黑名单 / 字母+数字 / 禁止包含用户名
        try:
            validate_password_strength(user_in.password, user_in.username)
        except ValueError as exc:
            logger.info("注册失败：弱密码 username={} reason={}", user_in.username, exc)
            raise BusinessException(
                ResponseCode.WEAK_PASSWORD,
                message=str(exc),
                detail=f"username={user_in.username}",
            ) from exc

        # 复用用户服务：内部完成用户名唯一性校验与 bcrypt 哈希入库
        return self.user_service.create_user(user_in)
