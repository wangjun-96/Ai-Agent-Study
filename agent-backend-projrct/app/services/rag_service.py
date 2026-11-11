"""业务层：知识库资源入库编排。

职责：
- 校验资源归属与类型；
- 从 MinIO 下载原文件到临时目录；
- 调用 RAG 核心链路解析 / 切片 / 向量化 / 写 Qdrant；
- 切片原文写入 MySQL knowledge_chunks 并统一提交事务。
"""
import os
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.core import BusinessException, SystemException, get_logger
from app.dao.resource_dao import ResourceDao
from app.enums.response_code import ResponseCode
from app.enums.resource_type import ResourceType
from app.integrations.minio_client import MinioStorage
from app.rag.chunk_store import save_chunks
from app.rag.core import ingest_file

logger = get_logger("rag_service")


class RagService:
    """知识库入库服务：每个实例绑定请求级 Session。"""

    def __init__(self, resource_dao: ResourceDao, minio_storage: MinioStorage) -> None:
        self.resource_dao = resource_dao
        self.minio_storage = minio_storage

    def ingest_resource(self, resource_id: int, user_id: int, db: Session) -> dict:
        """把指定资源文件入库为知识切片。

        :param resource_id: resources 表主键
        :param user_id: 当前登录用户，越权统一按不存在处理
        :param db: 请求级 Session（用于切片落库）
        :return: {resource_id, file_name, chunk_count}
        """
        resource = self.resource_dao.get_by_id(resource_id)
        if resource is None or int(resource.user_id) != int(user_id):
            raise BusinessException(
                ResponseCode.RESOURCE_NOT_FOUND, detail=f"resource_id={resource_id}"
            )
        if int(resource.resource_type) != int(ResourceType.FILE):
            raise BusinessException(
                ResponseCode.PARAM_INVALID,
                message="仅支持对文档类型资源建立知识库",
                detail=f"resource_type={resource.resource_type}",
            )

        parsed = self.minio_storage.parse_storage_path(resource.storage_path)
        if parsed is None:
            raise SystemException(
                code=ResponseCode.SYSTEM_ERROR,
                message="资源存储路径非法，无法建立知识库",
                detail=f"resource_id={resource_id}",
            )
        bucket, object_key = parsed
        file_bytes = self.minio_storage.get_object_bytes(object_key, bucket)

        suffix = Path(resource.file_name).suffix or ".bin"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(file_bytes)
        temp_file.close()
        try:
            chunks = ingest_file(
                temp_file.name,
                user_id=user_id,
                file_name=resource.file_name,
                resource_id=resource_id,
            )
            chunk_count = save_chunks(
                db,
                resource_id=resource_id,
                user_id=user_id,
                chunks=chunks,
            )
            db.commit()
            logger.info(
                "知识库入库成功 resource_id={} user_id={} chunks={}",
                resource_id,
                user_id,
                chunk_count,
            )
            return {
                "resource_id": resource_id,
                "file_name": resource.file_name,
                "chunk_count": chunk_count,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            # 临时文件用完即删，避免磁盘堆积
            try:
                os.unlink(temp_file.name)
            except OSError:
                logger.warning("临时文件删除失败 path={}", temp_file.name)
