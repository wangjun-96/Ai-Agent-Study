"""add user avatar

Revision ID: a1b2c3d4e5f6
Revises: 37fbff02c763
Create Date: 2026-09-13 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Alembic 修订版本标识
revision: str = 'a1b2c3d4e5f6'
# 上一修订版本
down_revision: Union[str, None] = '37fbff02c763'
# 分支标签，多分支并行迁移时使用
branch_labels: Union[str, Sequence[str], None] = None
# 依赖的其他修订版本
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移：users 表新增 avatar 列（头像访问 URL，可空）。"""
    op.add_column(
        'users',
        sa.Column('avatar', sa.String(length=255), nullable=True, comment='头像访问URL'),
    )


def downgrade() -> None:
    """回滚迁移：删除 users 表 avatar 列。"""
    op.drop_column('users', 'avatar')
