"""第三方集成层：统一封装外部 SDK（MinIO 等），业务层只调用工具方法。"""
from app.integrations.minio_client import MinioStorage, get_minio_storage

__all__ = ["MinioStorage", "get_minio_storage"]
