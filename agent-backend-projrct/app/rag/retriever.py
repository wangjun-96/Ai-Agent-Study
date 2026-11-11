"""RAG 检索：按用户隔离召回知识切片。

流程：问题向量化 → Qdrant 相似检索（user_id 过滤）→ 相似度阈值过滤
→ MySQL 按 vector_id 回查原文 → 超长截断。
"""
from sqlalchemy.orm import Session

from app.core import get_logger, settings
from app.rag.chunk_store import fetch_chunks_by_vector_ids
from app.rag.qdrant_utils import embed_texts, search_vectors

logger = get_logger("rag_retriever")


def search_similar_chunks(
    query: str,
    user_id: int,
    db: Session,
    top_k: int | None = None,
) -> list[dict]:
    """召回与问题最相关的知识切片。

    :param query: 用户本轮问题
    :param user_id: 当前用户，Qdrant 侧按 user_id 过滤，避免跨用户泄露
    :param db: 请求级 Session，用于回查切片原文
    :param top_k: 召回条数，默认读取配置
    :return: [{chunk_id, resource_id, chunk_index, file_name, score, text}]
    """
    text = (query or "").strip()
    if not text:
        return []
    limit = top_k or settings.RAG_TOP_K
    query_vector = embed_texts([text])[0]
    points = search_vectors(query_vector, user_id, limit)

    vector_ids = [str(point.id) for point in points]
    chunks = fetch_chunks_by_vector_ids(db, vector_ids)
    results: list[dict] = []
    for point in points:
        score = float(point.score or 0.0)
        # 相似度低于阈值直接丢弃，避免低相关片段污染上下文
        if score < settings.RAG_SCORE_THRESHOLD:
            continue
        chunk = chunks.get(str(point.id))
        if chunk is None:
            logger.warning("检索向量在 MySQL 中缺少对应切片 vector_id={}", point.id)
            continue
        payload = point.payload or {}
        content = chunk.text
        if len(content) > settings.RAG_CHUNK_TEXT_MAX:
            content = content[: settings.RAG_CHUNK_TEXT_MAX] + "……"
        results.append(
            {
                "chunk_id": chunk.id,
                "resource_id": chunk.resource_id,
                "chunk_index": chunk.chunk_index,
                "file_name": payload.get("file_name"),
                "score": score,
                "text": content,
            }
        )
    logger.info(
        "RAG 检索完成 user_id={} query_chars={} hits={}",
        user_id,
        len(text),
        len(results),
    )
    return results
