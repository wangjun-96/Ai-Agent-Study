"""业务层：用户画像读写。

提供两个统一入口，供提示词变量注入与长期记忆更新复用：
- create_or_update：不存在则新建，存在则仅更新传入的非空字段；
- get_profile_dict：返回可直接用于提示词变量的字典（数组保持列表形态）。
"""
from sqlalchemy.orm import Session

from app.dao.user_profile_dao import UserProfileDao
from app.db.models import UserProfile
from app.schemas.user_profile import UserProfileUpsert

# 允许写入画像的业务字段（防止越权写入 id / user_id 等系统字段）
PROFILE_FIELDS = (
    "target_job",
    "years_experience",
    "target_level",
    "target_skills",
    "weak_topics",
    "learning_goal",
    "learning_style",
    "interview_focus",
    "long_term_summary",
)


class UserProfileService:
    """用户画像业务服务。"""

    def __init__(self, dao: UserProfileDao) -> None:
        self.dao = dao

    def create_or_update(
        self, user_id: int, payload: UserProfileUpsert
    ) -> UserProfile:
        """新增或更新用户画像：只覆盖显式传入的字段。

        :param user_id: 用户ID
        :param payload: 画像入参
        :return: 最新画像实体
        """
        update_data = {
            field: getattr(payload, field)
            for field in PROFILE_FIELDS
            if getattr(payload, field) is not None
        }
        existing = self.dao.get_by_user(user_id)
        if existing is None:
            return self.dao.insert(
                UserProfile(
                    user_id=user_id,
                    **update_data,
                )
            )
        if not update_data:
            return existing
        return self.dao.update(existing, update_data)

    def get_profile(self, user_id: int) -> UserProfile | None:
        """查询用户画像，不存在返回 None。"""
        return self.dao.get_by_user(user_id)

    def get_profile_dict(
        self, user_id: int, db: Session | None = None
    ) -> dict:
        """返回画像字典；无画像时返回空字典（由注入层补默认值）。

        :param user_id: 用户ID
        :param db: 可选独立 Session（流式/异步场景使用）
        """
        dao = UserProfileDao(db) if db is not None else self.dao
        profile = dao.get_by_user(user_id)
        if profile is None:
            return {}
        return {
            "target_job": profile.target_job,
            "years_experience": profile.years_experience,
            "target_level": profile.target_level,
            "target_skills": profile.target_skills or [],
            "weak_topics": profile.weak_topics or [],
            "learning_goal": profile.learning_goal,
            "learning_style": profile.learning_style,
            "interview_focus": profile.interview_focus or [],
            "long_term_summary": profile.long_term_summary,
        }
