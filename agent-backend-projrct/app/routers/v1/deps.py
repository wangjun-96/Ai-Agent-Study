"""公共依赖项：统一使用 FastAPI Depends 注入，便于后续扩展鉴权、分页等依赖。

依赖链：get_db(Session) → get_user_dao(UserDao) → get_user_service(UserService)
Session 按请求生命周期管理，DAO/Service 随之实例化，避免全局变量存储临时业务数据。

JWT 鉴权依赖 get_current_user 同样在此统一定义，受保护接口通过 Depends 挂载，
解析 Authorization: Bearer <access_token> 并加载当前登录用户。
"""
from fastapi import Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core import BusinessException
from app.core.jwt import decode_token
from app.dao.user_dao import UserDao
from app.db.database import get_db
from app.db.models import User
from app.enums.response_code import ResponseCode
from app.enums.token_type import TokenType
from app.services.file_service import FileService
from app.services.user_service import UserService

# Bearer 令牌提取器：从 Authorization 头解析 access token。
# 使用 HTTPBearer（而非 OAuth2PasswordBearer）：登录接口为 JSON 入参而非 OAuth2 表单规范，
# Swagger 的 Authorize 对话框只需粘贴登录返回的 access_token 即可，无需重复输入账密；
# auto_error=False：缺失/格式错误时返回 None，由 get_current_user 统一抛 40104，
# 保证"缺失令牌"与"令牌过期/伪造"错误码一致，前端拦截器逻辑无需分叉
bearer_scheme = HTTPBearer(auto_error=False)


def get_user_dao(db: Session = Depends(get_db)) -> UserDao:
    """构造用户 DAO，注入当前请求的 Session。"""
    return UserDao(db)


def get_user_service(user_dao: UserDao = Depends(get_user_dao)) -> UserService:
    """构造用户业务服务，注入 DAO。"""
    return UserService(user_dao)


def get_file_service(
    user_service: UserService = Depends(get_user_service),
) -> FileService:
    """构造文件上传业务服务，复用用户服务依赖链（头像回写共用 DAO/事务）。"""
    return FileService(user_service)


def get_current_user(
    credentials=Depends(bearer_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """JWT 鉴权依赖：校验访问令牌并返回当前登录用户，受保护接口统一挂载。

    - 令牌缺失/格式错误（含非 Bearer 方案）、过期/伪造/类型错误统一返回 40104；
    - 令牌合法但用户已被删除时同样转成 40104，不向前端暴露 404 语义。

    :param credentials: Authorization 头解析结果，取 credentials.token 即访问令牌
    :param user_service: 用户业务服务（依赖注入）
    :return: 当前登录用户 ORM 实例
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise BusinessException(
            ResponseCode.ACCESS_TOKEN_INVALID,
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token, TokenType.ACCESS)
    user_id = int(payload["sub"])
    try:
        return user_service.get_user(user_id)
    except BusinessException as exc:
        if exc.code == int(ResponseCode.USER_NOT_FOUND):
            raise BusinessException(
                ResponseCode.ACCESS_TOKEN_INVALID,
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise


# 便于在路由函数签名中直接声明依赖（也可写为 Depends(get_user_service)）
UserServiceDep = Depends(get_user_service)
