"""知识切片存储：MySQL knowledge_chunks 的写入与回查。

- 写入不 commit，由业务层（RagService）统一提交，保证与元数据更新同事务；
- 回查用于 RAG 检索命中后取原文，以及历史消息按 reference_sources 重新拼来源。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk, Resource

# 知识块已被删除时的占位文案
DELETED_CHUNK_TEXT = "该参考片段已被删除"


def save_chunks(
    db: Session,
    *,
    resource_id: int,
    user_id: int,
    chunks,
) -> int:
    """批量写入切片原文（flush 不 commit），返回写入条数。

    :param db: 当前事务 Session
    :param resource_id: 关联 resources 表 ID
    :param user_id: 归属用户
    :param chunks: core.IngestedChunk 列表
    """
    if not chunks:
        return 0
    rows = [
        KnowledgeChunk(
            resource_id=resource_id,
            user_id=user_id,
            vector_id=chunk.vector_id,
            text=chunk.text,
            chunk_index=chunk.chunk_index,
            char_count=chunk.char_count,
        )
        for chunk in chunks
    ]
    db.add_all(rows)
    db.flush()
    return len(rows)


def fetch_chunks_by_vector_ids(
    db: Session, vector_ids: list[str]
) -> dict[str, KnowledgeChunk]:
    """按 vector_id 批量回查切片原文，返回 {vector_id: KnowledgeChunk}。"""
    if not vector_ids:
        return {}
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.vector_id.in_(vector_ids))
    rows = list(db.scalars(stmt))
    return {row.vector_id: row for row in rows}


def fetch_sources_by_reference(
    db: Session, references: list[dict]
) -> list[dict]:
    """按历史消息的 reference_sources 回查切片与文件，重新拼出 sources。

    :param references: [{chunk_id, score}]，仅存 ID 与分数，不存原文
    :return: [{chunk_id, resource_id, chunk_index, file_name, score, text}]
             知识块已删除时 text 返回“该参考片段已被删除”
    """
    if not references:
        return []
    chunk_ids = [
        int(ref["chunk_id"])
        for ref in references
        if isinstance(ref, dict) and ref.get("chunk_id") is not None
    ]
    chunks = {
        row.id: row
        for row in db.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids))
        )
    }
    resource_ids = {chunk.resource_id for chunk in chunks.values()}
    resources = {
        row.id: row
        for row in db.scalars(select(Resource).where(Resource.id.in_(resource_ids)))
    }

    sources: list[dict] = []
    for ref in references:
        if not isinstance(ref, dict):
            continue
        chunk_id = ref.get("chunk_id")
        chunk = chunks.get(int(chunk_id)) if chunk_id is not None else None
        if chunk is None:
            sources.append(
                {
                    "chunk_id": chunk_id,
                    "resource_id": None,
                    "chunk_index": None,
                    "file_name": None,
                    "score": ref.get("score"),
                    "text": DELETED_CHUNK_TEXT,
                }
            )
            continue
        resource = resources.get(chunk.resource_id)
        sources.append(
            {
                "chunk_id": chunk.id,
                "resource_id": chunk.resource_id,
                "chunk_index": chunk.chunk_index,
                "file_name": resource.file_name if resource else None,
                "score": ref.get("score"),
                "text": chunk.text,
            }
        )
    return sources
