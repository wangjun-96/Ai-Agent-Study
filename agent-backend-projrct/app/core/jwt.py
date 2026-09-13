"""JWT 令牌工具：基于 PyJWT 签发与校验 Access Token / Refresh Token。

设计要点：
1. 密钥、算法、有效期全部从配置层（settings）读取，禁止在代码中硬编码密钥。
2. 两类令牌通过载荷 type 声明严格区分：访问令牌只用于鉴权，刷新令牌只用于换新，
   防止拿刷新令牌直接访问业务接口，或拿访问令牌调用刷新接口。
3. 标准声明：sub（用户ID）、iat（签发时间）、exp（过期时间）、jti（令牌唯一ID），
   业务声明：username（用户名）、type（令牌类型）。
4. 校验失败（过期 / 伪造 / 类型不符）统一抛 BusinessException，
   访问令牌失败码 40104、刷新令牌失败码 40105，由全局异常处理器返回标准响应，
   前端据此决定"静默刷新重试"还是"跳转重新登录"。
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core import BusinessException, get_logger, settings
from app.enums.response_code import ResponseCode
from app.enums.token_type import TokenType

logger = get_logger("jwt")

# 受保护接口要求的认证响应头，401 时通过 WWW-Authenticate 告知前端认证方案
_BEARER_AUTH_HEADER = {"WWW-Authenticate": "Bearer"}


def create_token(
    user_id: int,
    username: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    """签发 JWT 的通用方法。

    :param user_id: 用户ID，写入 sub 声明（JWT 规范要求 sub 为字符串）
    :param username: 用户名，写入业务声明，减少接口查库次数
    :param token_type: 令牌类型（access / refresh）
    :param expires_delta: 有效期时间增量
    :return: 编码后的 JWT 字符串
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, str | int] = {
        "sub": str(user_id),
        "username": username,
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        # 令牌唯一标识，便于后续做黑名单/单点登录等扩展
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, username: str) -> str:
    """签发访问令牌（Access Token）：短期有效，用于访问受保护接口。"""
    return create_token(
        user_id=user_id,
        username=username,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int, username: str) -> str:
    """签发刷新令牌（Refresh Token）：长期有效，仅用于换取新的访问令牌。"""
    return create_token(
        user_id=user_id,
        username=username,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: TokenType) -> dict:
    """校验并解码 JWT，失败统一抛业务异常（HTTP 401）。

    :param token: 待校验的 JWT 字符串
    :param expected_type: 期望的令牌类型，类型不符直接拒绝，防止两类令牌混用
    :return: 解码后的载荷字典
    """
    # 访问令牌与刷新令牌使用各自独立的错误码，前端按错误码决定续期或重新登录
    error_code = (
        ResponseCode.ACCESS_TOKEN_INVALID
        if expected_type == TokenType.ACCESS
        else ResponseCode.REFRESH_TOKEN_INVALID
    )
    try:
        payload: dict = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError as exc:
        logger.info("令牌已过期 type={}", expected_type.value)
        raise BusinessException(
            error_code, headers=_BEARER_AUTH_HEADER
        ) from exc
    except InvalidTokenError as exc:
        # 伪造、签名错误、格式非法等统一归为无效令牌，不向前端暴露具体原因
        logger.info("令牌校验失败 type={} reason={}", expected_type.value, exc)
        raise BusinessException(
            error_code, headers=_BEARER_AUTH_HEADER
        ) from exc

    # 类型声明缺失或与期望不符（如拿 refresh 令牌访问业务接口）一律拒绝
    if payload.get("type") != expected_type.value:
        logger.info(
            "令牌类型不匹配 expected={} actual={}",
            expected_type.value,
            payload.get("type"),
        )
        raise BusinessException(error_code, headers=_BEARER_AUTH_HEADER)

    return payload
