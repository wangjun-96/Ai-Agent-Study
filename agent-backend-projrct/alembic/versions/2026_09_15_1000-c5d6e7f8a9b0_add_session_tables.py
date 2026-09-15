"""add session tables

Revision ID: c5d6e7f8a9b0
Revises: a1b2c3d4e5f6
Create Date: 2026-09-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# Alembic 修订版本标识
revision: str = 'c5d6e7f8a9b0'
# 上一修订版本
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
# 分支标签，多分支并行迁移时使用
branch_labels: Union[str, Sequence[str], None] = None
# 依赖的其他修订版本
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移：创建 sessions、chat_messages、interviews 三张表。"""
    # 1. 会话表
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='会话ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('session_model', sa.Integer(), nullable=False, comment='会话模式：0=学习，1=面试，2=笔记'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='会话标题'),
        sa.Column('create_at', sa.BigInteger(), server_default=sa.text('UNIX_TIMESTAMP()'), nullable=False, comment='会话创建时间（Unix秒）'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)

    # 2. 消息表
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='消息ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('session_id', sa.Integer(), nullable=False, comment='会话ID'),
        sa.Column('select_model', sa.Integer(), nullable=False, comment='选择模式：0=默认，1=知识精讲，2=刷题，3=简历优化，4=模拟面试，5=面试复盘'),
        sa.Column('request_id', sa.String(length=64), nullable=False, comment='请求ID'),
        sa.Column('request_text', mysql.MEDIUMTEXT(), nullable=False, comment='请求文本'),
        sa.Column('response_text', mysql.MEDIUMTEXT(), nullable=False, comment='响应文本'),
        sa.Column('create_at', sa.BigInteger(), server_default=sa.text('UNIX_TIMESTAMP()'), nullable=False, comment='消息创建时间（Unix秒）'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_request_id'), 'chat_messages', ['request_id'], unique=False)
    # 复合索引：session_id + create_at
    op.create_index('ix_chat_messages_session_id_create_at', 'chat_messages', ['session_id', 'create_at'], unique=False)

    # 3. 面试记录表
    op.create_table('interviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='面试记录ID'),
        sa.Column('session_id', sa.Integer(), nullable=False, comment='会话ID'),
        sa.Column('message_id', sa.Integer(), nullable=False, comment='入口消息ID'),
        sa.Column('qa_object', sa.JSON(), nullable=False, comment='问答对象'),
        sa.Column('interview_duration', sa.Integer(), server_default='0', nullable=False, comment='累计面试时长（秒）'),
        sa.Column('status', sa.Integer(), server_default='0', nullable=False, comment='面试状态：0=进行中，1=已完成，2=异常终止'),
        sa.Column('create_at', sa.BigInteger(), server_default=sa.text('UNIX_TIMESTAMP()'), nullable=False, comment='面试开始时间（Unix秒）'),
        sa.Column('update_at', sa.BigInteger(), server_default=sa.text('UNIX_TIMESTAMP()'), nullable=False, comment='更新面试时间（Unix秒）'),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id')
    )
    op.create_index(op.f('ix_interviews_status'), 'interviews', ['status'], unique=False)
    # 复合索引：session_id + message_id
    op.create_index('ix_interviews_session_id_message_id', 'interviews', ['session_id', 'message_id'], unique=False)


def downgrade() -> None:
    """回滚迁移：逆序删除三张表及索引。"""
    # 3. 删除 interviews 表索引与表
    op.drop_index('ix_interviews_session_id_message_id', table_name='interviews')
    op.drop_index(op.f('ix_interviews_status'), table_name='interviews')
    op.drop_table('interviews')
    # 2. 删除 chat_messages 表索引与表
    op.drop_index('ix_chat_messages_session_id_create_at', table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_request_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    # 1. 删除 sessions 表索引与表
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
