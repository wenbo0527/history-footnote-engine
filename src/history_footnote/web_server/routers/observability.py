"""可观测性路由：

GET /metrics                — 性能指标
GET /health                 — 健康检查（基础）
GET /api/llm/stats          — LLM token 统计
GET /api/llm/reset_stats    — 重置统计（开发）
GET /api/monitor/health     — 详细健康检查
GET /api/monitor/stats      — 监控统计（端点调用/慢请求/错误）
"""
from __future__ import annotations

import time

from history_footnote.web_server.handler_base import logger, safe_error_id
from history_footnote.web_server.views.session import session_get, _get_or_load_session


def handle_GET_metrics(handler) -> bool:
    from history_footnote.web_enhancements import GLOBAL_METRICS
    handler._json(200, GLOBAL_METRICS.snapshot())
    return True


def handle_GET_health(handler) -> bool:
    handler._json(200, {"status": "ok", "version": "1.7.29"})
    return True


def handle_GET_llm_stats(handler, query) -> bool:
    try:
        from history_footnote.llm_wrapper import get_usage_logger
        logger_instance = get_usage_logger()
        from urllib.parse import parse_qs
        qs = parse_qs(query)
        recent_limit = int(qs.get("recent_limit", ["20"])[0])
        stats = logger_instance.get_stats()
        stats["recent"] = logger_instance.get_recent(limit=recent_limit)
        handler._json(200, stats)
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[llm/stats] {error_id} failed: {e}")
        handler._json(500, {"error": "llm stats fetch failed", "error_id": error_id})
    return True


def handle_GET_llm_reset_stats(handler) -> bool:
    try:
        from history_footnote.llm_wrapper import get_usage_logger
        get_usage_logger().reset()
        handler._json(200, {"ok": True, "message": "stats reset"})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[llm/reset_stats] {error_id} failed: {e}")
        handler._json(500, {"error": "reset failed", "error_id": error_id})
    return True


def handle_GET_monitor_health(handler) -> bool:
    try:
        from history_footnote.monitor import get_monitor
        from history_footnote.issue_reporter import VERSION
        monitor = get_monitor()
        status = "healthy" if monitor.is_healthy() else "degraded"
        handler._json(200, {
            "status": status,
            "uptime_seconds": round(time.time() - monitor.start_time, 1),
            "version": VERSION,
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[monitor/health] {error_id} failed: {e}")
        handler._json(500, {"status": "unhealthy", "error": str(e), "error_id": error_id})
    return True


def handle_GET_monitor_stats(handler) -> bool:
    try:
        from history_footnote.monitor import get_monitor
        monitor = get_monitor()
        handler._json(200, monitor.get_stats())
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[monitor/stats] {error_id} failed: {e}")
        handler._json(500, {"error": "monitor stats failed", "error_id": error_id})
    return True
