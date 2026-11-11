"""用户画像 DAO：封装 user_profiles 表的全部数据库操作。

一人一条画像：insert_or_update 先按 user_id 查询，存在则更新非空字段，不存在则新建。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserProfile


class UserProfileDao:
    """用户画像数据访问对象：每个实例绑定一个 Session。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user(self, user_id: int) -> UserProfile | None:
        """按用户 ID 查询画像，不存在返回 None。"""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        return self.db.scalars(stmt).first()

    def insert(self, profile: UserProfile) -> UserProfile:
        """新建画像，自带事务。"""
        try:
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            return profile
        except Exception:
            self.db.rollback()
            raise

    def update(self, profile: UserProfile, update_data: dict) -> UserProfile:
        """更新画像字段（仅更新传入的非空字段），自带事务。"""
        try:
            for key, value in update_data.items():
                setattr(profile, key, value)
            self.db.commit()
            self.db.refresh(profile)
            return profile
        except Exception:
            self.db.rollback()
            raise
