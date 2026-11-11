"""RAG 向量存储与向量化工具：统一封装 Qdrant 客户端、集合初始化与 DashScope 向量化。

设计要点：
1. 支持两种 Qdrant 运行模式：远端 Server（host/port）与本地文件（local_path），
   本地模式便于开发环境免部署；连接参数全部来自配置层。
2. 向量化统一走 DashScope text-embedding-v4，单批 10 条，按 text_index 回填顺序。
3. 业务层只调用本模块函数，不直接写 Qdrant / DashScope SDK 代码。
"""
from functools import lru_cache
from pathlib import Path
from typing import Any

import dashscope
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core import SystemException, get_logger, settings
from app.core.config import PROJECT_ROOT
from app.enums.response_code import ResponseCode

logger = get_logger("rag_qdrant")

# DashScope 单批向量化条数（接口限制，超出会报错）
EMBEDDING_BATCH_SIZE = 10


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """获取全局唯一 Qdrant 客户端（本地文件模式或远端 Server 模式）。

    本地模式使用嵌入式存储，路径相对项目根目录解析；远端模式连接 host:port。
    初始化失败抛系统异常，由调用方决定是降级还是返回明确错误。
    """
    try:
        if settings.QDRANT_LOCAL_PATH.strip():
            path = Path(settings.QDRANT_LOCAL_PATH.strip())
            local_path = path if path.is_absolute() else PROJECT_ROOT / path
            local_path.mkdir(parents=True, exist_ok=True)
            logger.info("Qdrant 使用本地文件模式 path={}", local_path)
            return QdrantClient(path=str(local_path))
        logger.info(
            "Qdrant 使用远端模式 host={} port={}",
            settings.QDRANT_HOST,
            settings.QDRANT_PORT,
        )
        return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    except Exception as exc:  # noqa: BLE001 第三方初始化失败统一转系统异常
        logger.exception("Qdrant 客户端初始化失败 error={}", exc)
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="向量数据库初始化失败",
            detail=str(exc),
        ) from exc


def ensure_collection(client: QdrantClient) -> None:
    """集合不存在时自动创建：余弦距离 + 配置维度。"""
    collection = settings.QDRANT_COLLECTION
    if client.collection_exists(collection):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(
            size=settings.RAG_EMBEDDING_DIM, distance=Distance.COSINE
        ),
    )
    logger.info("Qdrant 集合已创建 collection={} dim={}", collection, settings.RAG_EMBEDDING_DIM)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化：每批 10 条，按 text_index 对齐返回顺序。

    :param texts: 待向量化文本列表
    :return: 与入参顺序一致的向量列表
    """
    if not texts:
        return []
    api_key = settings.DASHSCOPE_API_KEY.strip()
    if not api_key:
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="向量化服务未配置，请联系管理员",
            detail="环境变量 DASHSCOPE_API_KEY 为空",
        )

    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        response = dashscope.TextEmbedding.call(
            model=settings.RAG_EMBEDDING_MODEL,
            input=batch,
            api_key=api_key,
            dimension=settings.RAG_EMBEDDING_DIM,
        )
        if response.status_code != 200:
            logger.warning(
                "DashScope 向量化失败 status={} message={}",
                response.status_code,
                getattr(response, "message", ""),
            )
            raise SystemException(
                code=ResponseCode.SYSTEM_ERROR,
                message="文本向量化失败，请稍后再试",
                detail=f"status={response.status_code}, message={getattr(response, 'message', '')}",
            )
        embeddings = sorted(
            response.output["embeddings"], key=lambda item: item.get("text_index", 0)
        )
        vectors.extend([list(item["embedding"]) for item in embeddings])
    return vectors


def upsert_vectors(
    points: list[PointStruct],
) -> None:
    """批量写入向量点（payload 只含过滤字段，不存原文）。"""
    if not points:
        return
    client = get_qdrant_client()
    ensure_collection(client)
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points,
        wait=True,
    )


def search_vectors(
    query_vector: list[float], user_id: int, top_k: int
) -> list[Any]:
    """按用户隔离检索最相似向量，返回 ScoredPoint 列表。"""
    client = get_qdrant_client()
    ensure_collection(client)
    response = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return list(response.points)
