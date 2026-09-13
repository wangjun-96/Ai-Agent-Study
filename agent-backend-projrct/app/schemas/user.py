"""校验层：使用 Pydantic v2 定义用户相关的请求/响应模型。

路径参数、查询参数、请求体全部结构化定义，禁止裸参接收。
响应模型中不暴露 password 字段，避免敏感信息泄露。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """用户公共字段：用户名。"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")


class UserCreate(UserBase):
    """创建用户请求体。"""
    password: str = Field(..., min_length=6, max_length=128, description="密码（明文，存储前会哈希）")


class UserUpdate(BaseModel):
    """更新用户请求体，所有字段可选。"""
    username: str | None = Field(None, min_length=2, max_length=50, description="用户名")
    password: str | None = Field(None, min_length=6, max_length=128, description="新密码")


class UserResponse(BaseModel):
    """用户响应模型，仅暴露 id、username、头像与创建时间，不返回密码。"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    avatar: str | None = Field(None, description="头像访问 URL，未设置时为 null")
    create_time: datetime = Field(..., description="创建时间")

    # 允许从 ORM/字典对象的属性直接构造
    model_config = ConfigDict(from_attributes=True)
