"""调度层：每日 03:00 清理过期资源。

使用 asyncio 轻量实现，不引入 APScheduler 等额外依赖：
1. 计算距离下一个 03:00 的秒数并睡眠，到点执行清理，随后按天循环；
2. 清理任务在线程中执行（DAO/MinIO 均为同步 SDK），不阻塞事件循环；
3. 由 FastAPI lifespan 启动与取消。适用于单 worker 部署；多 worker 会各自
   触发一次，删除操作幂等，不会产生错误结果。
"""
import asyncio
from datetime import datetime, timedelta

from app.core.logger import get_logger
from app.dao.resource_dao import ResourceDao
from app.db.database import SessionLocal
from app.integrations.minio_client import get_minio_storage
from app.services.resource_cleanup_service import ResourceCleanupService

logger = get_logger("scheduler")

# 每日清理时刻：03:00
CLEANUP_HOUR = 3
CLEANUP_MINUTE = 0


def seconds_until_next_run(
    hour: int = CLEANUP_HOUR,
    minute: int = CLEANUP_MINUTE,
    now: datetime | None = None,
) -> float:
    """计算从当前时间到下一个指定时刻（默认今日/次日 03:00）的秒数。"""
    current = now or datetime.now()
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return (target - current).total_seconds()


async def daily_cleanup_loop() -> None:
    """每日定时清理循环：睡眠到 03:00 → 执行 → 继续等待下一天。"""
    while True:
        await asyncio.sleep(seconds_until_next_run())
        await asyncio.to_thread(run_cleanup_once)


def run_cleanup_once() -> None:
    """执行一次清理：自建 Session（定时任务不在请求上下文中），异常只记录不抛出。"""
    db = SessionLocal()
    try:
        service = ResourceCleanupService(get_minio_storage(), ResourceDao(db))
        service.cleanup_expired()
    except Exception:
        logger.exception("过期资源清理任务执行异常")
    finally:
        db.close()
