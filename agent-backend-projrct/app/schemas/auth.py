"""校验层：认证模块的请求/响应模型。

复用用户模块已有的字段结构与长度约束，注册专属的弱密码业务规则
（黑名单、字母+数字、禁止包含用户名）在业务层 AuthService 中校验，
失败抛业务异常返回 400，与参数格式错误（422）区分语义。
"""
from app.schemas.user import UserCreate


class RegisterRequest(UserCreate):
    """注册请求体：字段同用户创建（username/password），复用其 Pydantic 约束。

    继承 UserCreate 后可直接传入 UserService.create_user，无需重复定义字段；
    独立类型便于注册接口在 Swagger 中语义化展示及后续扩展注册专属字段。
    """
