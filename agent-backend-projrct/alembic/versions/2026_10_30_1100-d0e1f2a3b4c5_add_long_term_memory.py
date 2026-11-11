"""用户画像表扩展长期记忆字段

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-30 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMTEXT


# revision identifiers, used by Alembic.
revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 学习目标 / 学习风格 / 面试关注方向 / 长期记忆摘要
    op.add_column(
        "user_profiles",
        sa.Column("learning_goal", sa.String(length=255), nullable=True, comment="学习目标"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("learning_style", sa.String(length=128), nullable=True, comment="学习风格/偏好"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("interview_focus", sa.JSON(), nullable=True, comment="面试关注方向（JSON数组）"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("long_term_summary", MEDIUMTEXT(), nullable=True, comment="长期记忆摘要"),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "long_term_summary")
    op.drop_column("user_profiles", "interview_focus")
    op.drop_column("user_profiles", "learning_style")
    op.drop_column("user_profiles", "learning_goal")
