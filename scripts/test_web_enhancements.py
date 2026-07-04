"""Web Enhancements 单元测试（P2 优化）"""
import sys
import threading
import time
sys.path.insert(0, "src")

from history_footnote.web_enhancements import (
    ToolResultCache,
    RateLimiter,
    MetricsCollector,
    GLOBAL_RATE_LIMITER,
    LLM_RATE_LIMITER,
    GLOBAL_METRICS,
    TOOL_RESULT_CACHE,
    setup_keepalive,
    record_request_metrics,
)


def test_tool_cache_basic():
    cache = ToolResultCache(max_size=10, ttl_seconds=2)
    cache.set("k1", "v1")
    cache.set("k2", {"a": 1, "b": 2})

    assert cache.get("k1") == "v1"
    assert cache.get("k2") == {"a": 1, "b": 2}
    assert cache.get("k3") is None
    stats = cache.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    print(f"✅ test_tool_cache_basic: {stats['hit_rate'] * 100:.0f}% 命中率")


def test_tool_cache_ttl():
    cache = ToolResultCache(max_size=10, ttl_seconds=0.5)
    cache.set("k1", "v1")
    assert cache.get("k1") == "v1"
    time.sleep(0.6)
    assert cache.get("k1") is None
    print("✅ test_tool_cache_ttl: TTL 过期正常")


def test_tool_cache_lru_eviction():
    cache = ToolResultCache(max_size=3)
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    cache.set("k3", "v3")
    cache.set("k4", "v4")  # 应淘汰 k1
    assert cache.get("k1") is None
    assert cache.get("k2") == "v2"
    assert cache.get("k4") == "v4"
    print("✅ test_tool_cache_lru_eviction: LRU 淘汰正确")


def test_tool_cache_decorator():
    cache = ToolResultCache(max_size=10)

    call_count = [0]

    @cache.cached("test_func")
    def slow_func(x):
        call_count[0] += 1
        time.sleep(0.05)
        return x * 2

    t0 = time.time()
    r1 = slow_func(5)
    t1 = time.time()
    assert r1 == 10
    assert call_count[0] == 1

    t0 = time.time()
    r2 = slow_func(5)
    t1 = time.time()
    assert r2 == 10
    assert call_count[0] == 1  # 第二次命中缓存
    print(f"✅ test_tool_cache_decorator: 装饰器缓存生效（调用次数={call_count[0]}）")


def test_rate_limiter_basic():
    limiter = RateLimiter(max_requests=3, window_seconds=1.0)
    assert limiter.allow("ip1") is True
    assert limiter.allow("ip1") is True
    assert limiter.allow("ip1") is True
    assert limiter.allow("ip1") is False  # 第 4 个被拒
    print("✅ test_rate_limiter_basic: 4/3 被拒")


def test_rate_limiter_per_ip():
    limiter = RateLimiter(max_requests=2, window_seconds=1.0)
    assert limiter.allow("ip1") is True
    assert limiter.allow("ip1") is True
    assert limiter.allow("ip1") is False  # ip1 满了
    assert limiter.allow("ip2") is True  # ip2 独立
    assert limiter.allow("ip2") is True
    assert limiter.allow("ip2") is False  # ip2 也满了
    print("✅ test_rate_limiter_per_ip: per-IP 独立计数")


def test_rate_limiter_window():
    limiter = RateLimiter(max_requests=2, window_seconds=0.5)
    limiter.allow("ip1")
    limiter.allow("ip1")
    assert limiter.allow("ip1") is False
    time.sleep(0.6)  # 等待窗口过期
    assert limiter.allow("ip1") is True  # 窗口重置
    print("✅ test_rate_limiter_window: 窗口过期重置")


def test_metrics_collector():
    metrics = MetricsCollector()
    metrics.record_request("/api/start", 200)
    metrics.record_request("/api/start", 250)
    metrics.record_request("/api/input", 1500, error=True)
    metrics.record_request("/api/input", 1800)

    snap = metrics.snapshot()
    assert snap["endpoints"]["/api/start"]["count"] == 2
    assert snap["endpoints"]["/api/start"]["avg_ms"] == 225.0
    assert snap["endpoints"]["/api/input"]["count"] == 2
    assert snap["endpoints"]["/api/input"]["errors"] == 1
    print(f"✅ test_metrics_collector: 4 请求 / 1 错误")


def test_global_singletons():
    """全局单例可访问"""
    assert GLOBAL_RATE_LIMITER is not None
    assert LLM_RATE_LIMITER is not None
    assert GLOBAL_METRICS is not None
    assert TOOL_RESULT_CACHE is not None
    print("✅ test_global_singletons: 4 个全局单例就绪")


def test_setup_keepalive():
    """设置 keep-alive 不报错"""
    class DummyHandler:
        pass

    setup_keepalive(DummyHandler)
    assert DummyHandler.protocol_version == "HTTP/1.1"
    assert DummyHandler.timeout == 5
    print("✅ test_setup_keepalive: HTTP/1.1 + 5s 超时")


def test_concurrent_rate_limit():
    """并发安全"""
    limiter = RateLimiter(max_requests=50, window_seconds=1.0)
    allowed = [0]
    blocked = [0]
    lock = threading.Lock()

    def worker():
        for _ in range(20):
            if limiter.allow("concurrent_ip"):
                with lock:
                    allowed[0] += 1
            else:
                with lock:
                    blocked[0] += 1

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 5 线程 × 20 请求 = 100 个，超 50 个
    assert allowed[0] == 50, f"应有 50 个通过，实际 {allowed[0]}"
    assert blocked[0] == 50, f"应有 50 个拒绝，实际 {blocked[0]}"
    print(f"✅ test_concurrent_rate_limit: {allowed[0]}/{blocked[0]} 通过/拒绝（线程安全）")


if __name__ == "__main__":
    print("=" * 50)
    print("Web Enhancements 单元测试（P2 优化）")
    print("=" * 50)
    test_tool_cache_basic()
    test_tool_cache_ttl()
    test_tool_cache_lru_eviction()
    test_tool_cache_decorator()
    test_rate_limiter_basic()
    test_rate_limiter_per_ip()
    test_rate_limiter_window()
    test_metrics_collector()
    test_global_singletons()
    test_setup_keepalive()
    test_concurrent_rate_limit()
    print("\n✅ 所有 P2 优化测试通过")