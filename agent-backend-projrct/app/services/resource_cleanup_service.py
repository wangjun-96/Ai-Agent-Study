"""业务层：过期资源清理。

规则（见 prompt.md L147）：扫描 expire_time 已到期记录，
先删 MinIO 对象，再删 resources 元数据。
单条记录清理失败（存储/数据库异常）只跳过该条并记录日志，不影响其他记录。
"""
from datetime import datetime

from app.core import get_logger
from app.dao.resource_dao import ResourceDao
from app.integrations.minio_client import MinioStorage

logger = get_logger("resource_cleanup_service")


class ResourceCleanupService:
    """过期资源清理服务：MinIO 对象与元数据按序删除。"""

    def __init__(
        self,
        minio_storage: MinioStorage,
        resource_dao: ResourceDao,
    ) -> None:
        self.minio_storage = minio_storage
        self.resource_dao = resource_dao

    def cleanup_expired(self, now: datetime | None = None) -> int:
        """清理全部已过期资源，返回成功删除条数。

        :param now: 基准时间（默认当前时间，测试可注入）
        """
        scan_time = now or datetime.now()
        expired = self.resource_dao.list_expired(scan_time)

        deleted = 0
        for resource in expired:
            try:
                # 先删 MinIO 对象；无法解析路径（异常/空）时跳过对象删除
                parsed = self.minio_storage.parse_storage_path(resource.storage_path)
                if parsed is not None:
                    bucket, object_key = parsed
                    self.minio_storage.delete_object(object_key, bucket)
                # 再删元数据
                self.resource_dao.delete(resource)
                deleted += 1
            except Exception:
                # 单条失败不阻断整体清理
                logger.exception(
                    "过期资源删除失败 resource_id={} path={}",
                    resource.id,
                    resource.storage_path,
                )

        logger.info(
            "过期资源清理完成 scanned={} deleted={}",
            len(expired),
            deleted,
        )
        return deleted
