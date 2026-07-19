"""🆕 v1.6.2 Web Server 增强层

整合多个 P2 优化：
- A6: HTTP keep-alive（连接复用）
- D1: Tool 结果缓存
- D6: 请求限流（防 DDoS）
- 监控面板 /metrics

Usage:
    from history_footnote.web_enhancements import (
        RateLimiter, MetricsCollector, ToolResultCache,
        setup_keepalive, install_metrics_endpoint,
    )
"""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict, defaultdict, deque
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ============================================================
# A6: HTTP keep-alive 辅助
# ============================================================

def setup_keepalive(handler_class):
    """为 BaseHTTPRequestHandler 启用 keep-alive

    通过设置 protocol_version = 'HTTP/1.1' 来启用持久连接
    """
    handler_class.protocol_version = "HTTP/1.1"
    # 5 秒空闲超时（避免占连接）
    handler_class.timeout = 5
    return handler_class


# ============================================================
# D1: Tool 结果缓存（LRU）
# ============================================================

class ToolResultCache:
    """Tool 调用结果缓存（线程安全 LRU）

    用于缓存 query_knowledge、recall_events 等只读 Tool 的结果。
    缓存 key：(tool_name, args_hash)
    缓存 value：(result, timestamp)

    用法：
        cache = ToolResultCache(max_size=1000, ttl_seconds=300)

        @cache.cached("query_knowledge")
        def query_knowledge(...): ...
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            value, timestamp = self._cache[key]
            # 检查 TTL
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                self._misses += 1
                return None
            # 更新 LRU
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            # 如果已存在，先删
            if key in self._cache:
                del self._cache[key]
            # 如果满了，移除最旧的
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = (value, time.time())

    def cached(self, prefix: str = "") -> Callable:
        """装饰器：缓存函数结果"""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # 构造 cache key
                key_parts = [prefix, func.__name__]
                for arg in args:
                    key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")
                key = "|".join(key_parts)

                # 检查缓存
                cached = self.get(key)
                if cached is not None:
                    return cached

                # 计算并缓存
                result = func(*args, **kwargs)
                self.set(key, result)
                return result
            return wrapper
        return decorator

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }


# 全局实例
TOOL_RESULT_CACHE = ToolResultCache(max_size=2000, ttl_seconds=600)


# ============================================================
# D6: 请求限流器（滑动窗口）
# ============================================================

class RateLimiter:
    """滑动窗口限流器（防 DDoS / 限恶意刷）

    每个 IP 地址独立计数。
    在 window_seconds 秒内最多允许 max_requests 个请求。

    用法：
        limiter = RateLimiter(max_requests=60, window_seconds=60)

        # 在 web handler 里：
        client_ip = self.client_address[0]
        if not limiter.allow(client_ip):
            self._json(429, {"error": "Too Many Requests"})
            return
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._blocked_count = 0

    def allow(self, key: str) -> bool:
        """检查是否允许该 key 的请求"""
        with self._lock:
            now = time.time()
            bucket = self._buckets[key]

            # 清理过期的请求记录
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()

            # 检查是否超限
            if len(bucket) >= self.max_requests:
                self._blocked_count += 1
                return False

            # 记录本次请求
            bucket.append(now)
            return True

    def stats(self) -> dict:
        with self._lock:
            return {
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "active_ips": len(self._buckets),
                "blocked_count": self._blocked_count,
            }

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._blocked_count = 0


# 🆕 v1.7.2 限流配置从 config.py 读（环境变量可覆盖）
from history_footnote.config import RateLimits as _RateCfg

# 全局限流：每 IP 每分钟最多 N 个请求（环境变量 GLOBAL_MAX_REQUESTS）
GLOBAL_RATE_LIMITER = RateLimiter(
    max_requests=_RateCfg.GLOBAL_MAX_REQUESTS,
    window_seconds=_RateCfg.GLOBAL_WINDOW_SECONDS,
)

# LLM 调用专门限流（更严）：每 IP 每分钟最多 N 次 LLM 调用
LLM_RATE_LIMITER = RateLimiter(
    max_requests=_RateCfg.LLM_MAX_REQUESTS,
    window_seconds=_RateCfg.LLM_WINDOW_SECONDS,
)

# 🆕 v1.7.30: Session 级 LLM 限流（更细粒度）
# 防玩家反复点"帮我一下"刷请求（每 session 每分钟最多 N 次）
SESSION_LLM_RATE_LIMITER = RateLimiter(
    max_requests=_RateCfg.LLM_MAX_REQUESTS // 2,  # 30/分钟（默认）
    window_seconds=_RateCfg.LLM_WINDOW_SECONDS,
)


# ============================================================
# 监控指标收集器
# ============================================================

class MetricsCollector:
    """性能监控指标收集器

    跟踪：
    - 各种端点的调用次数 + 平均耗时
    - 缓存命中率
    - 当前活跃 session 数
    - LLM 调用次数 / token 估算

    通过 GET /metrics 端点暴露
    """

    def __init__(self):
        self._endpoints: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_ms": 0.0, "errors": 0, "latencies": []})
        # 🆕 W44: LLM 专用指标
        self._llm: dict[str, dict] = defaultdict(lambda: {
            "count": 0, "total_prompt_tokens": 0, "total_completion_tokens": 0, "latencies": []
        })
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record_request(self, endpoint: str, duration_ms: float, error: bool = False) -> None:
        """记录一次请求"""
        with self._lock:
            ep = self._endpoints[endpoint]
            ep["count"] += 1
            ep["total_ms"] += duration_ms
            ep["latencies"].append(duration_ms)
            # 防止内存无限增长：保留最近 1000 个延迟样本
            if len(ep["latencies"]) > 1000:
                ep["latencies"] = ep["latencies"][-1000:]
            if error:
                ep["errors"] += 1

    def record_llm_call(
        self,
        provider: str,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """🆕 W44: 记录一次 LLM 调用（按 provider 分组）

        Args:
            provider: "openai" / "anthropic" / "minimax-anthropic" / "minimax-openai" / "deepseek" / "custom" / "mock"
            latency_ms: 调用耗时（毫秒）
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
        """
        with self._lock:
            llm = self._llm[provider]
            llm["count"] += 1
            llm["total_prompt_tokens"] += prompt_tokens
            llm["total_completion_tokens"] += completion_tokens
            llm["latencies"].append(latency_ms)
            if len(llm["latencies"]) > 1000:
                llm["latencies"] = llm["latencies"][-1000:]

    @staticmethod
    def _percentile(values: list, p: float) -> float:
        """计算百分位（P50=0.5, P95=0.95, P99=0.99）

        使用线性插值（Numpy 默认行为）：
        - idx = (n-1) * p
        - lower = floor(idx)
        - upper = ceil(idx)
        - weight = idx - lower
        - return sorted[lower] * (1-weight) + sorted[upper] * weight
        """
        if not values:
            return 0.0
        sorted_v = sorted(values)
        n = len(sorted_v)
        pos = (n - 1) * p
        lower = int(pos)  # 向下取整
        upper = min(lower + 1, n - 1)
        weight = pos - lower
        return sorted_v[lower] * (1 - weight) + sorted_v[upper] * weight

    def snapshot(self) -> dict:
        """获取当前指标快照"""
        with self._lock:
            endpoints = {}
            for k, v in self._endpoints.items():
                count = v["count"]
                avg_ms = v["total_ms"] / count if count > 0 else 0
                endpoints[k] = {
                    "count": count,
                    "avg_ms": round(avg_ms, 2),
                    "p50_ms": round(self._percentile(v["latencies"], 0.5), 2),
                    "p95_ms": round(self._percentile(v["latencies"], 0.95), 2),
                    "p99_ms": round(self._percentile(v["latencies"], 0.99), 2),
                    "errors": v["errors"],
                    "error_rate": v["errors"] / count if count > 0 else 0.0,
                }
            # 🆕 W44: LLM 指标
            llm_stats = {}
            for k, v in self._llm.items():
                count = v["count"]
                llm_stats[k] = {
                    "count": count,
                    "total_prompt_tokens": v["total_prompt_tokens"],
                    "total_completion_tokens": v["total_completion_tokens"],
                    "avg_prompt_tokens": round(v["total_prompt_tokens"] / count, 1) if count > 0 else 0,
                    "avg_completion_tokens": round(v["total_completion_tokens"] / count, 1) if count > 0 else 0,
                    "avg_latency_ms": round(sum(v["latencies"]) / count, 2) if count > 0 else 0,
                    "p50_latency_ms": round(self._percentile(v["latencies"], 0.5), 2),
                    "p95_latency_ms": round(self._percentile(v["latencies"], 0.95), 2),
                }
            return {
                "uptime_seconds": time.time() - self._start_time,
                "endpoints": endpoints,
                "llm": llm_stats,  # 🆕 W44
                "tool_cache": TOOL_RESULT_CACHE.stats(),
                "rate_limiter": GLOBAL_RATE_LIMITER.stats(),
                "llm_throttle": _get_llm_throttle_stats(),
            }

    def reset(self) -> None:
        with self._lock:
            self._endpoints.clear()
            self._start_time = time.time()


def _get_llm_throttle_stats() -> dict:
    """获取 LLM 限流器状态（避免循环导入）"""
    try:
        from history_footnote.concurrency import LLM_THROTTLE
        return LLM_THROTTLE.stats()
    except Exception:
        logger.exception("[v1.7.2] LLM throttle stats 读取失败")
        return {}


def record_request_metrics(endpoint: str, duration_ms: float, error: bool = False) -> None:
    """便捷函数：记录一次请求指标"""
    GLOBAL_METRICS.record_request(endpoint, duration_ms, error=error)


GLOBAL_METRICS = MetricsCollector()


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Web Enhancements 测试")
    print("=" * 50)

    # 测试 ToolResultCache
    cache = ToolResultCache(max_size=3, ttl_seconds=1)
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    print(f"✅ ToolResultCache: get('k1') = {cache.get('k1')}")

    # 装饰器
    @cache.cached("test")
    def slow_func(x: int) -> int:
        time.sleep(0.1)
        return x * 2

    t0 = time.time()
    r1 = slow_func(5)
    t1 = time.time()
    print(f"❌ slow_func(5) 第一次: {r1} ({(t1-t0)*1000:.1f}ms)")

    t0 = time.time()
    r2 = slow_func(5)
    t1 = time.time()
    print(f"✅ slow_func(5) 第二次（缓存）: {r2} ({(t1-t0)*1000:.1f}ms)")

    # 测试 RateLimiter
    limiter = RateLimiter(max_requests=3, window_seconds=1.0)
    print(f"\n✅ RateLimiter: max=3/秒")
    for i in range(5):
        allowed = limiter.allow("test_ip")
        print(f"  请求 {i+1}: {'✅ 通过' if allowed else '❌ 拒绝'}")

    # 测试 MetricsCollector
    metrics = MetricsCollector()
    metrics.record_request("/api/input", 1500)
    metrics.record_request("/api/input", 2000, error=True)
    metrics.record_request("/api/start", 200)
    print(f"\n✅ Metrics:")
    snap = metrics.snapshot()
    print(f"  uptime: {snap['uptime_seconds']:.1f}s")
    print(f"  endpoints: {snap['endpoints']}")
    print(f"  tool_cache hit_rate: {snap['tool_cache']['hit_rate'] * 100:.0f}%")

    print("\n✅ Web Enhancements 测试通过")