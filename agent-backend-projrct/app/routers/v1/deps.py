"""公共依赖项：统一使用 FastAPI Depends 注入，便于后续扩展鉴权、分页等依赖。

依赖链：get_db(Session) → get_user_dao(UserDao) → get_user_service(UserService)
Session 按请求生命周期管理，DAO/Service 随之实例化，避免全局变量存储临时业务数据。
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.dao.user_dao import UserDao
from app.db.database import get_db
from app.services.user_service import UserService


def get_user_dao(db: Session = Depends(get_db)) -> UserDao:
    """构造用户 DAO，注入当前请求的 Session。"""
    return UserDao(db)


def get_user_service(user_dao: UserDao = Depends(get_user_dao)) -> UserService:
    """构造用户业务服务，注入 DAO。"""
    return UserService(user_dao)


# 便于在路由函数签名中直接声明依赖（也可写为 Depends(get_user_service)）
UserServiceDep = Depends(get_user_service)
