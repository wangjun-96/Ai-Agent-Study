"""路由聚合层：v1 版本统一出口。

所有 v1 子路由在此统一注册，main.py 只需挂载本模块的 api_router 即可。
新增业务模块时只需在此文件追加一行 include_router，无需改动 main.py。

职责划分：
- auth    ：认证鉴权（注册/登录/令牌刷新/当前用户），内部按接口分别决定是否鉴权
- users   ：用户管理 CRUD，路由组统一挂载 JWT 鉴权
- files   ：文件上传，路由组统一挂载 JWT 鉴权
- avatar  ：头像公开代理，无鉴权（供 <img> 标签直接访问）
"""
from fastapi import APIRouter

from app.routers.v1 import auth, avatar, files, users

# v1 统一聚合路由：main.py 只挂载这一个
api_router = APIRouter()

# 认证路由：注册/登录/令牌刷新为匿名公开接口，/auth/me 内部挂载 JWT
api_router.include_router(auth.router)

# 业务路由：各路由组内部通过 dependencies 统一挂载 JWT 登录鉴权
api_router.include_router(users.router)
api_router.include_router(files.router)

# 头像公开代理路由：无 JWT 鉴权，供前端 <img src="/api/v1/avatar/{user_id}"> 直接使用
api_router.include_router(avatar.router)
