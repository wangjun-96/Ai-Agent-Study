"""MinIO 对象存储工具类：封装 minio SDK，对业务层屏蔽第三方细节。

设计要点：
1. 连接参数全部由构造函数显式传入，工厂 ``get_minio_storage`` 从 settings
   读取环境变量（MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET/SECURE）；
2. 桶懒初始化：首次上传时桶不存在则自动创建，避免启动期强依赖 MinIO；
3. 统一 storage_path 编解码：minio://{bucket}/{object_key}；
4. 业务层只调用本工具方法，不裸写 SDK 代码。
"""
from datetime import timedelta
from functools import lru_cache
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinioStorage:
    """MinIO 对象存储封装：上传 / 删除 / 预签名下载 / 路径编解码。"""

    # storage_path 协议前缀
    SCHEME = "minio://"

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        # 默认资源桶
        self._bucket = bucket
        # minio 客户端（构造时不建立连接）
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def ensure_bucket(self) -> None:
        """桶不存在时创建（首次上传懒触发）。"""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_object(
        self,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """上传对象（put_object），以字节内容作为数据源。"""
        self.ensure_bucket()
        self._client.put_object(
            self._bucket,
            object_key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def delete_object(self, object_key: str, bucket: str | None = None) -> None:
        """删除对象；对象已不存在（NoSuchKey）视为删除成功。"""
        target_bucket = bucket or self._bucket
        try:
            self._client.remove_object(target_bucket, object_key)
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise

    def presigned_get_url(self, object_key: str, expiry_seconds: int) -> str:
        """生成预签名 GET URL，供前端在有效期内临时访问私有桶对象。"""
        return self._client.presigned_get_object(
            self._bucket,
            object_key,
            expires=timedelta(seconds=expiry_seconds),
        )

    def build_storage_path(self, object_key: str) -> str:
        """拼接元数据存储路径：minio://{bucket}/{object_key}。"""
        return f"{self.SCHEME}{self._bucket}/{object_key}"

    @classmethod
    def parse_storage_path(cls, storage_path: str) -> tuple[str, str] | None:
        """解析 storage_path，返回 (bucket, object_key)；非法路径返回 None。"""
        if not storage_path.startswith(cls.SCHEME):
            return None
        # object_key 自身可能含 /（如 user_id/xxx），只切分第一个分隔符
        bucket, separator, object_key = storage_path[len(cls.SCHEME):].partition("/")
        if not separator or not bucket or not object_key:
            return None
        return bucket, object_key

    def presigned_url_from_path(
        self, storage_path: str, expiry_seconds: int
    ) -> str | None:
        """从 storage_path 解析桶与对象 key 后生成预签名下载 URL。

        路径非法（非 minio:// 前缀或格式残缺）时返回 None，由调用方决定
        是跳过还是抛出业务异常。
        """
        parsed = self.parse_storage_path(storage_path)
        if parsed is None:
            return None
        bucket, object_key = parsed
        return self._client.presigned_get_object(
            bucket,
            object_key,
            expires=timedelta(seconds=expiry_seconds),
        )


@lru_cache
def get_minio_storage() -> MinioStorage:
    """构造全局唯一 MinioStorage（连接参数从环境变量读取，缓存复用）。"""
    return MinioStorage(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        bucket=settings.MINIO_BUCKET,
        secure=settings.MINIO_SECURE,
    )
