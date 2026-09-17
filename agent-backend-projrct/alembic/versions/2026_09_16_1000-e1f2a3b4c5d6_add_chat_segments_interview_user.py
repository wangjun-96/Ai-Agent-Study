"""add chat segments and interview user_id

Revision ID: e1f2a3b4c5d6
Revises: d7e8f9a0b1c2
Create Date: 2026-09-16 10:00:00.000000

变更内容：
1. chat_messages 新增 request_segments / response_segments（JSON，附件段）；
2. chat_messages 新增 interview_id（可空，外键关联 interviews.id，加索引）；
3. interviews 新增 user_id（外键关联 users.id，加索引）；
   - 先以 nullable 新增，再从 sessions.user_id 回填，最后置为 NOT NULL。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Alembic 修订版本标识
revision: str = 'e1f2a3b4c5d6'
# 上一修订版本
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
# 分支标签
branch_labels: Union[str, Sequence[str], None] = None
# 依赖的其他修订版本
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移：消息表加附件段/面试ID，面试表加 user_id。"""
    # 1. chat_messages 新增附件段字段（可空，旧消息不受影响）
    op.add_column(
        'chat_messages',
        sa.Column(
            'request_segments',
            sa.JSON(),
            nullable=True,
            comment='用户消息附件段（file/image/audio）',
        ),
    )
    op.add_column(
        'chat_messages',
        sa.Column(
            'response_segments',
            sa.JSON(),
            nullable=True,
            comment='AI回复附件段（file/image/audio）',
        ),
    )

    # 2. chat_messages 新增 interview_id（可空外键 + 索引）
    op.add_column(
        'chat_messages',
        sa.Column(
            'interview_id',
            sa.Integer(),
            nullable=True,
            comment='关联面试记录ID',
        ),
    )
    op.create_index(
        op.f('ix_chat_messages_interview_id'),
        'chat_messages',
        ['interview_id'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_chat_messages_interview_id',
        'chat_messages',
        'interviews',
        ['interview_id'],
        ['id'],
    )

    # 3. interviews 新增 user_id：先可空 → 回填 → 置 NOT NULL
    op.add_column(
        'interviews',
        sa.Column(
            'user_id',
            sa.Integer(),
            nullable=True,
            comment='用户ID',
        ),
    )
    # 从 sessions.user_id 回填已有面试记录的归属用户
    op.execute(
        "UPDATE interviews i "
        "JOIN sessions s ON i.session_id = s.id "
        "SET i.user_id = s.user_id "
        "WHERE i.user_id IS NULL"
    )
    op.alter_column(
        'interviews',
        'user_id',
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_index(
        op.f('ix_interviews_user_id'),
        'interviews',
        ['user_id'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_interviews_user_id',
        'interviews',
        'users',
        ['user_id'],
        ['id'],
    )


def downgrade() -> None:
    """回滚迁移：逆序删除新增字段、索引与外键。"""
    # interviews.user_id
    op.drop_constraint('fk_interviews_user_id', 'interviews', type_='foreignkey')
    op.drop_index(op.f('ix_interviews_user_id'), table_name='interviews')
    op.drop_column('interviews', 'user_id')

    # chat_messages.interview_id
    op.drop_constraint('fk_chat_messages_interview_id', 'chat_messages', type_='foreignkey')
    op.drop_index(op.f('ix_chat_messages_interview_id'), table_name='chat_messages')
    op.drop_column('chat_messages', 'interview_id')

    # chat_messages 附件段
    op.drop_column('chat_messages', 'response_segments')
    op.drop_column('chat_messages', 'request_segments')
