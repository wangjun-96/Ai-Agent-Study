"""固定窗口限流器单元测试：高并发防护逻辑与客户端 IP 解析。

覆盖范围：
1. 客户端真实 IP 解析：可信代理跳数 0/1/2、伪造 X-Forwarded-For 防护。
2. 固定窗口：窗口内阈值拦截、窗口过期自动重置。
3. 高并发防护：过期 key 清理、跟踪 key 上限 fail-open、429 携带 Retry-After。

运行命令：pytest tests/test_rate_limit.py -v
"""
import time

import pytest

from app.core import BusinessException
from app.core.rate_limit import FixedWindowRateLimiter, resolve_client_ip


# ---------------------------------------------------------------------------
# 一、客户端 IP 解析（防 X-Forwarded-For 伪造）
# ---------------------------------------------------------------------------


class TestResolveClientIp:
    """可信代理跳数语义测试。"""

    def test_direct_deploy_ignores_forwarded_for(self):
        """直连部署（hops=0）：即使携带 XFF 也一律忽略，防止伪造绕过限流。"""
        ip = resolve_client_ip("1.2.3.4", "10.0.0.1", trusted_hops=0)
        assert ip == "10.0.0.1"

    def test_single_proxy_takes_peer_appended_ip(self):
        """单层代理（hops=1）：取链路最右，即代理追加的 TCP 对端真实 IP。"""
        # 客户端伪造两个假 IP，Nginx 追加真实 TCP 对端
        ip = resolve_client_ip("fake1, fake2, 203.0.113.9", "127.0.0.1", 1)
        assert ip == "203.0.113.9"

    def test_two_layer_proxy(self):
        """两层代理（hops=2）：取从右数第 2 个位置（外层代理追加的真实客户端）。"""
        ip = resolve_client_ip("fake, 203.0.113.9, 10.0.0.10, 10.0.0.1", None, 2)
        assert ip == "10.0.0.10"

    def test_no_forwarded_header_falls_back_to_peer(self):
        """无 XFF 头：回退 TCP 直连 IP；连直连信息也没有时为 unknown。"""
        assert resolve_client_ip(None, "10.0.0.1", 1) == "10.0.0.1"
        assert resolve_client_ip(None, None, 1) == "unknown"
        assert resolve_client_ip("  ,  ", None, 1) == "unknown"


# ---------------------------------------------------------------------------
# 二、固定窗口计数
# ---------------------------------------------------------------------------


class TestFixedWindow:
    """固定窗口阈值与窗口重置测试。"""

    def test_blocks_after_threshold_and_carries_retry_after(self):
        """窗口内超过阈值即抛 429 业务异常，并携带 Retry-After 响应头。"""
        limiter = FixedWindowRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.check("1.1.1.1")  # 前 3 次放行

        with pytest.raises(BusinessException) as exc_info:
            limiter.check("1.1.1.1")
        assert exc_info.value.http_status == 429
        assert exc_info.value.headers is not None
        retry_after = int(exc_info.value.headers["Retry-After"])
        assert 1 <= retry_after <= 60

    def test_window_expiry_resets_counter(self):
        """窗口过期后计数自动重置，请求重新放行。"""
        limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=1)
        limiter.check("2.2.2.2")
        with pytest.raises(BusinessException):
            limiter.check("2.2.2.2")
        # 等待窗口过期
        time.sleep(1.1)
        limiter.check("2.2.2.2")  # 不抛异常即通过

    def test_different_keys_count_independently(self):
        """不同 IP 各自独立计数。"""
        limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60)
        limiter.check("3.3.3.3")
        limiter.check("4.4.4.4")  # 不同 IP 不受影响
        with pytest.raises(BusinessException):
            limiter.check("3.3.3.3")


# ---------------------------------------------------------------------------
# 三、高并发防护：过期清理与 key 上限保护
# ---------------------------------------------------------------------------


class TestMemoryProtection:
    """过期窗口清理与跟踪 key 上限保护测试。"""

    def test_expired_keys_are_swept(self):
        """短窗口 + 上限触发强制清理：过期条目被 sweep，dict 不残留。"""
        limiter = FixedWindowRateLimiter(
            max_requests=100, window_seconds=1, max_tracked_keys=3
        )
        limiter.check("ip1")
        limiter.check("ip2")
        time.sleep(1.1)
        # 第 3 个 key 触发上限强制清理，前两个过期条目应被回收
        limiter.check("ip3")
        assert set(limiter._windows.keys()) == {"ip3"}

    def test_fail_open_when_tracked_keys_exceed_cap(self):
        """跟踪 key 达上限且全部有效（疑似伪造海量 IP）时 fail-open 放行，不抛异常。"""
        limiter = FixedWindowRateLimiter(
            max_requests=100, window_seconds=60, max_tracked_keys=2
        )
        limiter.check("ip1")
        limiter.check("ip2")  # 达到上限，且均未过期
        # 第 3 个全新 IP：清理无过期项可回收，按 fail-open 策略放行
        limiter.check("ip3")
        limiter.check("ip4")
