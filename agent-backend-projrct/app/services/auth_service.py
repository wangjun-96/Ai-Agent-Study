"""业务层：认证模块业务逻辑。

- Service 只处理业务逻辑，数据操作复用 UserService（进而走 DAO 层），不直接操作 Session。
- 注册流程：先做弱密码校验，再复用 UserService.create_user 完成唯一性校验与入库，
  密码哈希、用户名重复等逻辑无需重复实现。
- 登录流程：按用户名查库 + bcrypt 校验密码，通过后用 PyJWT 签发 Access/Refresh 双令牌。
- 刷新流程：校验 Refresh Token 合法后重新签发 Access Token，实现访问令牌过期无感续期。
- 业务错误统一抛 BusinessException，由全局异常处理器捕获。
"""
from app.core import BusinessException, get_logger, settings
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.models import User
from app.enums.response_code import ResponseCode
from app.enums.token_type import TokenType
from app.schemas.auth import (
    AccessTokenResponse,
    RegisterRequest,
    TokenResponse,
)
from app.security import validate_password_strength, verify_password
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

    def login(self, username: str, password: str) -> TokenResponse:
        """用户登录：校验用户名与密码，通过后签发 Access/Refresh 双令牌。

        安全约定：
        - 用户名不存在与密码错误返回完全相同的错误（40103），避免用户名被枚举；
        - 密码比对使用 passlib bcrypt，库中只存哈希，不留明文。

        :param username: 用户名
        :param password: 明文密码
        :return: 访问令牌 + 刷新令牌令牌对
        """
        user = self.user_service.get_user_by_username(username)
        # 短路写法保证用户不存在时不执行密码校验；对外提示保持一致，不区分失败原因
        if user is None or not verify_password(password, user.password):
            logger.info("登录失败：用户名或密码错误 username={}", username)
            raise BusinessException(
                ResponseCode.INVALID_CREDENTIALS,
                detail=f"username={username}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 签发双令牌：访问令牌短期有效保护接口，刷新令牌长期有效仅用于换新
        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id, user.username)
        logger.info("用户登录成功 id={} username={}", user.id, user.username)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh_access_token(self, refresh_token: str) -> AccessTokenResponse:
        """使用刷新令牌换取新的访问令牌。

        校验失败（过期/伪造/令牌类型不符/用户已不存在）统一抛 40105，
        前端收到该错误码后无法再静默续期，应引导用户重新登录。

        :param refresh_token: 登录时签发的刷新令牌
        :return: 新签发的访问令牌（刷新令牌本身不变）
        """
        payload = decode_token(refresh_token, TokenType.REFRESH)
        user_id = int(payload["sub"])

        # 刷新时再次确认用户仍然存在（可能已被注销/删除）；
        # 用户不存在对令牌接口而言属于凭证失效，统一转成 40105，不暴露 404 语义
        try:
            user = self.user_service.get_user(user_id)
        except BusinessException as exc:
            if exc.code == int(ResponseCode.USER_NOT_FOUND):
                logger.info("刷新令牌失败：用户不存在 user_id={}", user_id)
                raise BusinessException(
                    ResponseCode.REFRESH_TOKEN_INVALID,
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            raise

        access_token = create_access_token(user.id, user.username)
        logger.info("访问令牌刷新成功 id={} username={}", user.id, user.username)
        return AccessTokenResponse(
            access_token=access_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
