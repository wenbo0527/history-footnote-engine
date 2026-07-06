"""🆕 v1.7.27 内置轻量级监控

不依赖第三方（如 Sentry），做应用内监控：
- 错误计数（按 error_id）
- 慢请求记录（> 5s）
- 健康检查（/api/monitor/health）
- 进程统计

设计原则：
- 简单：内存计数（重启丢失）
- 可选：未来可对接 Sentry / Prometheus
"""
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any


class AppMonitor:
    """🆕 v1.7.27 应用监控器

    用法:
        monitor = AppMonitor()
        with monitor.track("api.input"):
            # do work
        stats = monitor.get_stats()
    """

    def __init__(self, slow_threshold_ms: int = 5000, error_window: int = 100):
        self._lock = Lock()
        self.slow_threshold_ms = slow_threshold_ms
        # 错误历史（最近 error_window 条）
        self.recent_errors: deque = deque(maxlen=error_window)
        # 慢请求历史
        self.slow_requests: deque = deque(maxlen=error_window)
        # 端点调用计数
        self.endpoint_counts: dict[str, int] = defaultdict(int)
        # 端点平均延迟（最近 100 次）
        self.endpoint_latency: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        # 错误类型计数
        self.error_types: dict[str, int] = defaultdict(int)
        # 启动时间
        self.start_time = time.time()

    def track(self, endpoint: str):
        """🆕 上下文管理器：记录端点调用

        用法:
            with monitor.track("api.input"):
                # do work
        """
        return _TrackContext(self, endpoint)

    def record_error(self, error_id: str, error_type: str, endpoint: str = ""):
        """🆕 记录错误"""
        with self._lock:
            self.recent_errors.append({
                "error_id": error_id,
                "error_type": error_type,
                "endpoint": endpoint,
                "ts": time.time(),
            })
            self.error_types[error_type] += 1

    def record_slow(self, endpoint: str, latency_ms: float):
        """🆕 记录慢请求"""
        with self._lock:
            self.slow_requests.append({
                "endpoint": endpoint,
                "latency_ms": latency_ms,
                "ts": time.time(),
            })

    def record_call(self, endpoint: str, latency_ms: float):
        """🆕 记录调用"""
        with self._lock:
            self.endpoint_counts[endpoint] += 1
            self.endpoint_latency[endpoint].append(latency_ms)

    def get_stats(self) -> dict[str, Any]:
        """🆕 获取监控统计"""
        with self._lock:
            uptime = time.time() - self.start_time
            # 端点统计
            endpoint_stats = []
            for ep, count in sorted(self.endpoint_counts.items(), key=lambda x: -x[1]):
                latencies = list(self.endpoint_latency[ep])
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
                else:
                    avg_latency = 0
                    p95_latency = 0
                endpoint_stats.append({
                    "endpoint": ep,
                    "calls": count,
                    "avg_latency_ms": round(avg_latency, 2),
                    "p95_latency_ms": round(p95_latency, 2),
                })
            return {
                "uptime_seconds": round(uptime, 1),
                "total_errors": sum(self.error_types.values()),
                "error_types": dict(self.error_types),
                "slow_requests": len(self.slow_requests),
                "endpoint_count": len(self.endpoint_counts),
                "endpoints": endpoint_stats[:20],  # top 20
                "recent_errors": list(self.recent_errors)[-10:],  # 最近 10
            }

    def is_healthy(self) -> bool:
        """🆕 健康检查"""
        # 简单规则：错误率 < 50% 算健康
        with self._lock:
            total = sum(self.endpoint_counts.values())
            errors = sum(self.error_types.values())
            if total == 0:
                return True
            error_rate = errors / total
            return error_rate < 0.5


class _TrackContext:
    """🆕 track 上下文管理器"""

    def __init__(self, monitor: AppMonitor, endpoint: str):
        self.monitor = monitor
        self.endpoint = endpoint
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.time() - self.start) * 1000
        self.monitor.record_call(self.endpoint, latency_ms)
        if latency_ms > self.monitor.slow_threshold_ms:
            self.monitor.record_slow(self.endpoint, latency_ms)
        if exc_type is not None:
            import uuid
            self.monitor.record_error(
                error_id=str(uuid.uuid4())[:8],
                error_type=exc_type.__name__,
                endpoint=self.endpoint,
            )


# 全局单例
_app_monitor: AppMonitor | None = None


def get_monitor() -> AppMonitor:
    """🆕 获取全局监控器（单例）"""
    global _app_monitor
    if _app_monitor is None:
        _app_monitor = AppMonitor()
    return _app_monitor
