"""Redis 客户端封装：统一连接池、序列化与异常降级。

设计要点：
- 全项目通过 ``get_redis_cache()`` 获取缓存工具，业务层不直接写 Redis SDK 代码；
- 连接参数全部来自配置层（REDIS_HOST / REDIS_PORT / REDIS_DB / REDIS_PASSWORD）；
- 所有读写操作捕获异常后返回空值，Redis 故障不得影响主业务流程。
"""
import json
from functools import lru_cache
from typing import Any

import redis

from app.core import get_logger, settings

logger = get_logger("redis_client")


class RedisCache:
    """Redis 缓存工具：Hash 结构读写 + JSON 序列化 + 异常降级。"""

    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    def ping(self) -> bool:
        """连通性检查，异常时返回 False（不抛出）。"""
        try:
            return bool(self.client.ping())
        except Exception as exc:  # noqa: BLE001 Redis 故障统一降级
            logger.warning("Redis 连接异常 error={}", exc)
            return False

    def hget_json(self, key: str, field: str) -> dict[str, Any] | None:
        """读取 Hash 中某个字段并反序列化为字典，不存在或异常返回 None。"""
        try:
            raw = self.client.hget(key, field)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 读取失败 key={} field={} error={}", key, field, exc)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Redis 缓存反序列化失败 key={} field={} error={}", key, field, exc)
            return None

    def hset_json(self, key: str, field: str, value: dict[str, Any]) -> bool:
        """写入 Hash 字段（JSON 序列化），成功返回 True。"""
        try:
            self.client.hset(key, field, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 写入失败 key={} field={} error={}", key, field, exc)
            return False

    def hgetall_json(self, key: str) -> dict[str, dict[str, Any]]:
        """读取整个 Hash 并反序列化，异常返回空字典。"""
        try:
            raw_map = self.client.hgetall(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 批量读取失败 key={} error={}", key, exc)
            return {}

        result: dict[str, dict[str, Any]] = {}
        for field, raw in raw_map.items():
            try:
                result[field] = json.loads(raw)
            except json.JSONDecodeError:
                continue
        return result

    def delete(self, key: str) -> bool:
        """删除指定 Key，异常返回 False。"""
        try:
            self.client.delete(key)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 删除失败 key={} error={}", key, exc)
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """为 Key 设置过期时间（秒），用于工作记忆读写续期。"""
        try:
            return bool(self.client.expire(key, seconds))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 设置过期失败 key={} error={}", key, exc)
            return False


@lru_cache
def get_redis_cache() -> RedisCache | None:
    """获取全局 Redis 缓存工具；未启用或初始化失败时返回 None（调用方降级到数据库）。"""
    if not settings.REDIS_ENABLED:
        logger.info("Redis 未启用（REDIS_ENABLED=false），相关缓存自动降级")
        return None
    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            decode_responses=True,
        )
        client.ping()
    except Exception as exc:  # noqa: BLE001 初始化失败不阻断应用启动
        logger.warning("Redis 初始化失败，相关缓存自动降级 error={}", exc)
        return None
    return RedisCache(client)
