"""新增提示词模板表 prompt_templates 与用户画像表 user_profiles

Revision ID: b8c9d0e1f2a3
Revises: e1f2a3b4c5d6
Create Date: 2026-10-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMTEXT


# revision identifiers, used by Alembic.
revision = "b8c9d0e1f2a3"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 提示词模板表：公共模板与私有模板统一存储，按 (agent_name, scene) 版本独立递增
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="模板ID"),
        sa.Column("agent_name", sa.String(length=64), nullable=True, comment="智能体名称（公共模板为空）"),
        sa.Column("scene", sa.String(length=64), nullable=False, comment="业务场景"),
        sa.Column("template_type", sa.Integer(), nullable=False, comment="模板类型：1=私有，2=公共"),
        sa.Column("template_content", MEDIUMTEXT(), nullable=False, comment="模板正文"),
        sa.Column("variables", sa.String(length=512), nullable=True, comment="变量名列表（JSON字符串）"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1", comment="版本号"),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="0", comment="是否生效版本：0=否，1=是"),
        sa.Column("description", sa.String(length=255), nullable=True, comment="版本说明"),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("unix_timestamp()"),
            comment="创建时间（Unix秒）",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_templates_agent_name",
        "prompt_templates",
        ["agent_name"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_templates_scene",
        "prompt_templates",
        ["scene"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_templates_agent_scene_version",
        "prompt_templates",
        ["agent_name", "scene", "version"],
        unique=False,
    )

    # 用户画像表：一人一条，供提示词变量注入使用
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="画像ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("target_job", sa.String(length=128), nullable=True, comment="目标岗位"),
        sa.Column("years_experience", sa.String(length=64), nullable=True, comment="工作经验"),
        sa.Column("target_level", sa.String(length=64), nullable=True, comment="目标等级"),
        sa.Column("target_skills", sa.JSON(), nullable=True, comment="已掌握技能（JSON数组）"),
        sa.Column("weak_topics", sa.JSON(), nullable=True, comment="薄弱点（JSON数组）"),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("unix_timestamp()"),
            comment="创建时间（Unix秒）",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uk_user_profiles_user_id"),
    )
    op.create_index(
        "ix_user_profiles_user_id",
        "user_profiles",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
    op.drop_index("ix_prompt_templates_agent_scene_version", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_scene", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_agent_name", table_name="prompt_templates")
    op.drop_table("prompt_templates")
