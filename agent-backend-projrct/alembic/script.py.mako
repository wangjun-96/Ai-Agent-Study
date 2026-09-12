"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Alembic 修订版本标识
revision: str = ${repr(up_revision)}
# 上一修订版本（None 表示首个版本）
down_revision: Union[str, None] = ${repr(down_revision)}
# 分支标签，多分支并行迁移时使用
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
# 依赖的其他修订版本
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """升级迁移：正向执行表结构变更。"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """回滚迁移：逆序撤销 upgrade 的变更。"""
    ${downgrades if downgrades else "pass"}
