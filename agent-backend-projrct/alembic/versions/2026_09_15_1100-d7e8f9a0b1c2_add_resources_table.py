"""add resources table and chat_messages.file_extracted_text

Revision ID: d7e8f9a0b1c2
Revises: c5d6e7f8a9b0
Create Date: 2026-09-15 11:00:00.000000

变更内容：
1. chat_messages 新增 file_extracted_text（从文件中提取的完整文本，对话上下文用）；
2. 新建 resources 资源元数据表（MinIO 存原文件，本表存元数据）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# Alembic 修订版本标识
revision: str = 'd7e8f9a0b1c2'
# 上一修订版本
down_revision: Union[str, None] = 'c5d6e7f8a9b0'
# 分支标签
branch_labels: Union[str, Sequence[str], None] = None
# 依赖的其他修订版本
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移：消息表加字段 + 创建资源元数据表。"""
    # 1. chat_messages 新增文件提取文本字段（可空，旧消息不受影响）
    op.add_column(
        'chat_messages',
        sa.Column(
            'file_extracted_text',
            mysql.MEDIUMTEXT(),
            nullable=True,
            comment='从文件中提取的完整文本（对话上下文用）',
        ),
    )

    # 2. 资源元数据表
    op.create_table(
        'resources',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='资源主键ID'),
        sa.Column('resource_type', mysql.TINYINT(), nullable=False, comment='资源类型：0=文件，1=图片，2=音频'),
        sa.Column('storage_scene', mysql.TINYINT(), server_default='0', nullable=False, comment='存储场景：0=长过期时间（1个月），1=短过期时间（2小时）'),
        sa.Column('update_purpose', mysql.TINYINT(), server_default='0', nullable=False, comment='上传用途：0=普通资源，1=用户头像'),
        sa.Column('file_name', sa.String(length=255), nullable=False, comment='用户上传原始文件名'),
        sa.Column('file_hash', sa.String(length=64), nullable=False, comment='文件MD5，去重核心字段'),
        sa.Column('storage_path', sa.String(length=512), nullable=False, comment='MinIO对象存储路径'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='上传用户ID'),
        sa.Column('expire_time', sa.DateTime(), nullable=True, comment='资源过期时间'),
        sa.Column('create_time', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        # 用户 + MD5 联合唯一：用户级去重，数据库兜底
        sa.UniqueConstraint('file_hash', 'user_id', name='uk_file_hash_user_id'),
        mysql_comment='资源元数据表',
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
    )


def downgrade() -> None:
    """回滚迁移：删除资源表 + 删除消息表新字段。"""
    op.drop_table('resources')
    op.drop_column('chat_messages', 'file_extracted_text')
