"""业务层：处理用户业务逻辑，密码哈希在此层完成。

Service 只处理业务逻辑，不直接操作 Session、写 SQL 语句（调用 DAO 层）。
密码使用 passlib[bcrypt] 哈希，存储时不保留明文。
业务错误统一抛出 BusinessException，由全局异常处理器捕获。
"""
from app.core import BusinessException, get_logger
from app.dao.user_dao import UserDao
from app.db.models import User
from app.enums.response_code import ResponseCode
from app.schemas.user import UserCreate, UserUpdate
from app.security import hash_password

logger = get_logger("user_service")


class UserService:
    """用户业务服务：通过构造函数注入 DAO，方法内调用 DAO 完成数据操作。"""

    def __init__(self, user_dao: UserDao) -> None:
        self.user_dao = user_dao

    def create_user(self, user_in: UserCreate) -> User:
        """创建用户：校验用户名唯一性后，对密码哈希并入库。"""
        # 用户名唯一性校验
        if self.user_dao.find_by_username(user_in.username) is not None:
            logger.info("创建用户失败：用户名已存在 username={}", user_in.username)
            raise BusinessException(
                ResponseCode.USER_ALREADY_EXISTS,
                detail=f"username={user_in.username}",
            )

        # 构造 ORM 实例，密码哈希存储不保留明文
        user = User(
            username=user_in.username,
            password=hash_password(user_in.password),
        )
        created = self.user_dao.insert_user(user)
        logger.info("用户创建成功 id={} username={}", created.id, created.username)
        return created

    def get_user(self, user_id: int) -> User:
        """查询单个用户，不存在抛业务异常。"""
        user = self.user_dao.get_user(user_id)
        if user is None:
            raise BusinessException(
                ResponseCode.USER_NOT_FOUND, detail=f"user_id={user_id}"
            )
        return user

    def get_user_by_username(self, username: str) -> User | None:
        """按用户名查询用户，不存在返回 None（供登录认证场景使用）。"""
        return self.user_dao.find_by_username(username)

    def list_users(self) -> list[User]:
        """查询全部用户。"""
        return self.user_dao.list_users()

    def update_user(self, user_id: int, user_in: UserUpdate) -> User:
        """更新用户：仅更新非空字段，密码变更需重新哈希。"""
        existing = self.user_dao.get_user(user_id)
        if existing is None:
            raise BusinessException(
                ResponseCode.USER_NOT_FOUND, detail=f"user_id={user_id}"
            )

        update_data: dict = {}
        # 用户名变更需再次校验唯一性
        if user_in.username is not None and user_in.username != existing.username:
            if self.user_dao.find_by_username(user_in.username) is not None:
                raise BusinessException(
                    ResponseCode.USER_ALREADY_EXISTS,
                    detail=f"username={user_in.username}",
                )
            update_data["username"] = user_in.username
        # 密码变更需重新哈希
        if user_in.password is not None:
            update_data["password"] = hash_password(user_in.password)

        if update_data:
            self.user_dao.update_user(existing, update_data)
        return self.user_dao.get_user(user_id)  # type: ignore[return-value]

    def delete_user(self, user_id: int) -> None:
        """删除用户，不存在抛业务异常。"""
        user = self.user_dao.get_user(user_id)
        if user is None:
            raise BusinessException(
                ResponseCode.USER_NOT_FOUND, detail=f"user_id={user_id}"
            )
        self.user_dao.delete_user(user)
        logger.info("用户删除成功 id={}", user_id)
