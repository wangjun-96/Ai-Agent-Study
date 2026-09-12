"""接口限流工具：固定窗口算法，按客户端 IP 维度计数。

设计要点：
1. 固定窗口：同一 key 在 window_seconds 时间窗内最多访问 max_requests 次，
   窗口结束后计数自动清零，下一个窗口重新计数。
2. IP 维度：以客户端 IP 作为限流 key，适配注册接口防刷场景。
3. 进程内内存实现，不引入第三方依赖；多线程（同步接口运行在线程池）下用锁
   保证计数准确。计数器属于跨请求共享的基础设施状态（类似 Redis 限流计数），
   非单次请求业务数据，统一封装在限流器对象内管理。
4. 超限抛 BusinessException（42901 → HTTP 429）并携带标准 Retry-After 头，
   由全局异常处理器统一返回。

高并发防护：
- 周期清理 + 强制清理过期窗口条目，并对跟踪 key 数量设上限，防止伪造海量
  IP 打一次就走导致内存无界增长；清理后仍超上限时 fail-open（放行并告警），
  优先保证服务可用性。
- X-Forwarded-For 仅在配置了可信代理跳数时才采信，防止客户端伪造该头绕过限流。

已知边界（生产多实例部署）：
- 进程内计数仅在单进程内有效，uvicorn 多 worker / 多副本部署时限流阈值会随
  进程数放大，应将本类替换为 Redis 等共享存储实现（check 接口保持不变即可）。
- 固定窗口在窗口切换边界可能出现最多 2 倍瞬时突发，注册防刷场景可接受。
"""
import math
import threading
import time
from dataclasses import dataclass

from fastapi import Request

from app.core import BusinessException, get_logger
from app.core.config import settings
from app.enums.response_code import ResponseCode

logger = get_logger("rate_limit")

# 单个限流器最多跟踪的 key（IP）数量，超出后先强制清理，仍超则 fail-open
_MAX_TRACKED_KEYS = 10_000


def resolve_client_ip(
    forwarded_for: str | None, peer_host: str | None, trusted_hops: int
) -> str:
    """根据可信代理跳数解析客户端真实 IP（纯函数，便于单测）。

    :param forwarded_for: X-Forwarded-For 头原文，形如 "client, proxy1, proxy2"
    :param peer_host: TCP 直连对端 IP（request.client.host）
    :param trusted_hops: 可信反向代理跳数：
                         0 = 直连部署，一律不信 XFF，防止客户端伪造绕过限流；
                         1 = 单层 Nginx，取链路最右（代理追加的 TCP 对端）；
                         N = N 层可信代理，取从右数第 N 个位置
    """
    if not forwarded_for or trusted_hops <= 0:
        return peer_host or "unknown"
    parts = [item.strip() for item in forwarded_for.split(",") if item.strip()]
    if not parts:
        return peer_host or "unknown"
    # 链路最右 trusted_hops 跳由可信代理追加，其左侧紧邻位置即真实客户端
    index = len(parts) - trusted_hops
    return parts[index] if index >= 0 else parts[0]


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP，可信代理跳数由配置 TRUSTED_PROXY_HOPS 控制。"""
    return resolve_client_ip(
        request.headers.get("X-Forwarded-For"),
        request.client.host if request.client else None,
        settings.TRUSTED_PROXY_HOPS,
    )


@dataclass
class _Window:
    """单个固定窗口：起始时间戳与窗口内已计数请求数。"""

    start: float
    count: int


class FixedWindowRateLimiter:
    """固定窗口限流器：线程安全的进程内计数器。"""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        max_tracked_keys: int = _MAX_TRACKED_KEYS,
    ) -> None:
        # 窗口内最大允许请求数
        self.max_requests = max_requests
        # 窗口大小（秒）
        self.window_seconds = window_seconds
        # 跟踪 key 数量上限，防止伪造海量 IP 撑爆内存
        self.max_tracked_keys = max_tracked_keys
        # 限流 key（客户端 IP）→ 窗口
        self._windows: dict[str, _Window] = {}
        # 同步接口跑在线程池，计数与窗口切换需加锁
        self._lock = threading.Lock()
        # 上次全量清理过期窗口的时间戳
        self._last_sweep = 0.0

    def _sweep_locked(self, now: float) -> None:
        """清理全部已过期窗口（调用方须持有锁）。"""
        expired_keys = [
            key
            for key, window in self._windows.items()
            if now - window.start >= self.window_seconds
        ]
        for key in expired_keys:
            del self._windows[key]

    def check(self, key: str) -> None:
        """校验 key 是否超过限流阈值，未超限则累加计数，超限抛业务异常。"""
        now = time.monotonic()
        with self._lock:
            # 周期性清理过期条目；跟踪 key 达上限时立即强制清理，避免内存无界增长
            if (
                now - self._last_sweep >= self.window_seconds
                or len(self._windows) >= self.max_tracked_keys
            ):
                self._sweep_locked(now)
                self._last_sweep = now

            window = self._windows.get(key)
            # 窗口不存在或已过期：开启新窗口，首次计数
            if window is None or now - window.start >= self.window_seconds:
                # 清理后仍达上限（疑似伪造海量 IP 攻击）：fail-open 放行并告警，
                # 避免限流器自身 OOM 拖垮整个服务
                if window is None and len(self._windows) >= self.max_tracked_keys:
                    logger.error(
                        "[限流保护] 跟踪 key 已达上限 {}，疑似 IP 伪造攻击，本次放行",
                        self.max_tracked_keys,
                    )
                    return
                self._windows[key] = _Window(start=now, count=1)
                return
            # 当前窗口已达上限：拒绝并提示距离窗口重置的剩余秒数
            if window.count >= self.max_requests:
                # 距窗口重置的剩余秒数向上取整（同 tick 请求剩余恰为整窗口秒数）
                retry_after = max(
                    math.ceil(self.window_seconds - (now - window.start)), 1
                )
                logger.warning(
                    "[限流触发] key={} window_count={} limit={}/{}s",
                    key, window.count, self.max_requests, self.window_seconds,
                )
                raise BusinessException(
                    ResponseCode.RATE_LIMITED,
                    detail={"retry_after_seconds": retry_after},
                    # RFC 6585：429 建议携带 Retry-After 头，告知客户端重试间隔
                    headers={"Retry-After": str(retry_after)},
                )
            window.count += 1

    def reset(self) -> None:
        """清空全部计数（主要供测试用例重置限流状态）。"""
        with self._lock:
            self._windows.clear()
            self._last_sweep = 0.0


# 注册接口专用限流器：阈值与窗口统一从配置层读取，默认单 IP 5 次/分钟
register_rate_limiter = FixedWindowRateLimiter(
    max_requests=settings.REGISTER_RATE_LIMIT,
    window_seconds=settings.REGISTER_RATE_WINDOW_SECONDS,
)


def rate_limit_register(request: Request) -> None:
    """注册接口限流依赖：固定窗口 + IP 维度，在路由 dependencies 中统一挂载。"""
    register_rate_limiter.check(get_client_ip(request))
