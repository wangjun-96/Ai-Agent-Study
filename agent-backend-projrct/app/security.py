"""安全工具集合：密码哈希与密码强度策略。

- 密码哈希：基于 passlib + bcrypt，业务层在用户创建/更新时调用。
- 密码强度：注册等场景的弱密码校验（黑名单 + 字母数字组合 + 禁止包含用户名）。

接口登录鉴权（JWT 令牌校验）统一封装在 app/routers/v1/deps.py 的 get_current_user
依赖与 app/core/jwt.py 中，业务路由通过 Depends 统一挂载，本模块不再承担接口鉴权。
"""
import re

from passlib.context import CryptContext

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
