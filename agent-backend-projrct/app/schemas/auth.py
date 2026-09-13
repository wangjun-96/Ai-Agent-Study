"""校验层：认证模块的请求/响应模型。

- 注册请求复用 UserCreate 的字段结构与长度约束，注册专属的弱密码业务规则
  （黑名单、字母+数字、禁止包含用户名）在业务层 AuthService 中校验。
- 登录/刷新请求体全部结构化定义，禁止裸参接收。
- 令牌响应只返回令牌字符串与有效期等非敏感信息，绝不返回用户密码。
"""
from pydantic import BaseModel, Field

from app.schemas.user import UserCreate


class RegisterRequest(UserCreate):
    """注册请求体：字段同用户创建（username/password），复用其 Pydantic 约束。

    继承 UserCreate 后可直接传入 UserService.create_user，无需重复定义字段；
    独立类型便于注册接口在 Swagger 中语义化展示及后续扩展注册专属字段。
    """


class LoginRequest(BaseModel):
    """登录请求体：用户名 + 密码。

    登录场景不做密码强度/长度（6 位）限制，只要求非空：
    用户可能是历史数据，强度规则只在注册/改密时约束，凭证错误统一由业务层返回 401。
    """

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码（明文传输，依赖 HTTPS 保护）")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求体：仅携带登录时签发的 Refresh Token。"""

    refresh_token: str = Field(..., min_length=1, description="登录时获取的刷新令牌")


class TokenResponse(BaseModel):
    """登录成功响应：访问令牌 + 刷新令牌令牌对。"""

    access_token: str = Field(..., description="访问令牌，访问受保护接口时放入 Authorization: Bearer 头")
    refresh_token: str = Field(..., description="刷新令牌，访问令牌过期后用于静默换取新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型，固定为 bearer")
    expires_in: int = Field(..., description="访问令牌有效期（秒），过期前可主动刷新")


class AccessTokenResponse(BaseModel):
    """刷新成功响应：仅下发新的访问令牌，刷新令牌本身保持不变。"""

    access_token: str = Field(..., description="新签发的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型，固定为 bearer")
    expires_in: int = Field(..., description="访问令牌有效期（秒）")
