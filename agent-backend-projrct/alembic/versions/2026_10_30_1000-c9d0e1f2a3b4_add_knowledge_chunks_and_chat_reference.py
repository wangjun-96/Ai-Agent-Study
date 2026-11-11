"""新增知识切片表 knowledge_chunks，并为消息表补充 RAG 来源与结构化回复字段

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMTEXT


# revision identifiers, used by Alembic.
revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 知识切片表：原文存 MySQL，与 Qdrant 向量通过 vector_id 一一对应
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="切片ID"),
        # resources.id 为 BIGINT，外键列类型必须一致，否则建表报 3780
        sa.Column("resource_id", sa.BigInteger(), nullable=False, comment="资源ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("vector_id", sa.String(length=64), nullable=False, comment="向量ID（Qdrant point id）"),
        sa.Column("text", MEDIUMTEXT(), nullable=False, comment="切片原文"),
        sa.Column("chunk_index", sa.Integer(), nullable=False, comment="切片序号"),
        sa.Column("char_count", sa.Integer(), nullable=False, comment="切片字符数"),
        sa.Column(
            "create_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("unix_timestamp()"),
            comment="创建时间（Unix秒）",
        ),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vector_id"),
    )
    op.create_index(
        "ix_knowledge_chunks_resource_id", "knowledge_chunks", ["resource_id"], unique=False
    )
    op.create_index(
        "ix_knowledge_chunks_user_id", "knowledge_chunks", ["user_id"], unique=False
    )
    op.create_index(
        "ix_knowledge_chunks_resource_user",
        "knowledge_chunks",
        ["resource_id", "user_id"],
        unique=False,
    )

    # 消息表：RAG 参考来源（只存 chunk_id / score）与结构化回复数据
    op.add_column(
        "chat_messages",
        sa.Column("reference_sources", sa.JSON(), nullable=True, comment="RAG参考来源（chunk_id/score）"),
    )
    op.add_column(
        "chat_messages",
        sa.Column("response_payload", sa.JSON(), nullable=True, comment="AI回复结构化数据（如测评题目JSON）"),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "response_payload")
    op.drop_column("chat_messages", "reference_sources")
    op.drop_index("ix_knowledge_chunks_resource_user", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_user_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_resource_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
