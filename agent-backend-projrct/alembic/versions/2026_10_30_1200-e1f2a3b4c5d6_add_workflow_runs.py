"""新增工作流运行记录表 workflow_runs

Revision ID: f0a1b2c3d4e5
Revises: d0e1f2a3b4c5
Create Date: 2026-10-30 12:00:00.000000

变更内容：
1. 新建 workflow_runs 表，保存学习测评等业务工作流的运行业务快照；
2. run_id 唯一，同时作为 LangGraph thread_id 定位执行现场。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# 注意：revision 必须全局唯一（勿与 2026_09_16_1000-e1f2a3b4c5d6 冲突）
revision = "f0a1b2c3d4e5"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 工作流运行记录表：业务状态快照存库，LangGraph 执行现场由 checkpoint 保存
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="运行记录ID"),
        sa.Column("run_id", sa.String(length=64), nullable=False, comment="工作流运行ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("session_id", sa.Integer(), nullable=False, comment="会话ID"),
        sa.Column("workflow_type", sa.String(length=64), nullable=False, comment="工作流类型"),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="created",
            comment="运行状态",
        ),
        sa.Column("state_json", sa.JSON(), nullable=True, comment="业务状态快照"),
        sa.Column("error_message", sa.String(length=512), nullable=True, comment="失败原因"),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("unix_timestamp()"),
            comment="创建时间（Unix秒）",
        ),
        sa.Column(
            "updated_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("unix_timestamp()"),
            comment="更新时间（Unix秒）",
        ),
        sa.Column("completed_at", sa.BigInteger(), nullable=True, comment="完成时间（Unix秒）"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_workflow_runs_user_id", "workflow_runs", ["user_id"], unique=False
    )
    op.create_index(
        "ix_workflow_runs_session_id", "workflow_runs", ["session_id"], unique=False
    )
    # 复合索引：按用户 + 状态查询运行记录
    op.create_index(
        "ix_workflow_runs_user_status",
        "workflow_runs",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_user_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_session_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_user_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
