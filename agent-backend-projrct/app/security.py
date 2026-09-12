"""安全工具集合：合并密码哈希、密码强度策略与接口鉴权三部分能力。

- 密码哈希：基于 passlib + bcrypt，业务层在用户创建/更新时调用。
- 密码强度：注册等场景的弱密码校验（黑名单 + 字母数字组合 + 禁止包含用户名）。
- 接口鉴权：基于请求头 X-API-Key 的轻量鉴权，路由层统一挂载。
"""
import re

from fastapi import Depends, Header, HTTPException, status
from passlib.context import CryptContext

from app.core.config import settings

# ===========================================================================
# 一、密码哈希（passlib + bcrypt）
# ===========================================================================

# 使用 bcrypt 算法，自动识别 deprecated 版本
# 注意：bcrypt 是安全的，建议在生产环境中使用。
# bcrypt 是目前最安全的哈希算法，支持自适应成本调整。
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码做哈希加密，返回哈希字符串。"""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    return _pwd_context.verify(plain_password, hashed_password)


# ===========================================================================
# 二、密码强度策略（注册场景弱密码校验）
# ===========================================================================

# 常见弱密码黑名单（统一小写匹配），全局复用，禁止在业务代码内散落硬编码
WEAK_PASSWORD_BLACKLIST: frozenset[str] = frozenset(
    {
        "123456",
        "12345678",
        "123456789",
        "111111",
        "000000",
        "123123",
        "admin",
        "admin123",
        "password",
        "password123",
        "qwerty",
        "abc123",
        "iloveyou",
    }
)


def validate_password_strength(password: str, username: str) -> None:
    """弱密码校验，不通过时抛 ValueError（中文原因，由业务层转业务异常）。

    规则：
    1. 黑名单：命中常见弱密码（大小写不敏感）直接拒绝；
    2. 组合复杂度：必须同时包含字母与数字；
    3. 关联性：禁止密码包含用户名（大小写不敏感）。

    :param password: 明文密码
    :param username: 用户名，用于关联性校验
    """
    if password.lower() in WEAK_PASSWORD_BLACKLIST:
        raise ValueError("密码为常见弱密码，请勿使用")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise ValueError("密码必须同时包含字母和数字")
    if username and username.lower() in password.lower():
        raise ValueError("密码不能包含用户名")


# ===========================================================================
# 三、接口鉴权（X-API-Key）
#      接口鉴权的作用是：
#      1. 验证请求头 X-API-Key 是否存在且正确。
#      2. 保护 API 接口不被未授权访问，防止未授权访问。
#      3. 提供一种简单而有效的方式来验证客户端身份，避免使用复杂的认证机制。
#      4. 可以根据需要扩展到其他认证机制，如 JWT、OAuth 等。
# ===========================================================================

def get_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """从请求头 X-API-Key 提取并校验 API Key，失败返回 401。

    API Key 只从配置层（.env.development / .env.production 或系统环境变量）读取，
    业务层不写死任何密钥。
    """
    if not x_api_key or x_api_key != settings.APP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或缺失的 API Key",
            headers={"WWW-Authenticate": 'ApiKey realm="API"'},
        )
    return x_api_key


def verify_api_key(_: str = Depends(get_api_key)) -> None:
    """接口鉴权依赖，便于在路由 dependencies 中统一挂载。"""
    return None
