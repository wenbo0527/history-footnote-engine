"""🆕 v2.10.1 W52 P1-3 followup: Admin Tokens 模块

admin.py v1.7.30-2.10.1 段（行 279-337）拆出。
- GET /api/admin/tokens — token 消耗统计（全局 + 近期调用）

Auth 依赖 admin._shared 中的 helper：
- _check_admin_token / _admin_get_token / _admin_get_account_id
- _get_account_system
- logger
"""
from __future__ import annotations

from urllib.parse import parse_qs

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.routers.admin import (
    _check_admin_token,
    _admin_get_token,
    _admin_get_account_id,
    _get_account_system,
)


def handle_GET_admin_tokens(handler, query: str) -> bool:
    """GET /api/admin/tokens?account_id=xxx[&recent_limit=20]
    Returns: token 消耗统计（全局 + 近期调用）
    """
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        return True
    admin_id = _admin_get_account_id(handler, query)
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        qs = parse_qs(query)
        recent_limit = int(qs.get("recent_limit", ["20"])[0])
        from history_footnote.llm_wrapper import get_usage_logger
        usage = get_usage_logger()
        raw_stats = usage.get_stats()
        recent = usage.get_recent(limit=recent_limit)
        # 🆕 v1.7.47 字段对齐前端期望：
        # 前端用 s.total_calls / s.total_tokens / s.total_prompt_tokens / s.total_completion_tokens / s.error_count
        # 后端用 totals.calls / totals.tokens / totals.input_tokens / totals.output_tokens
        totals = raw_stats.get("totals", {})
        flat_stats = {
            "total_calls": totals.get("calls", 0),
            "total_tokens": totals.get("tokens", 0),
            "total_prompt_tokens": totals.get("input_tokens", 0),
            "total_completion_tokens": totals.get("output_tokens", 0),
            "total_latency_ms": totals.get("latency_ms", 0),
            "error_count": totals.get("fallback_count", 0) + totals.get("timeout_count", 0),
            "fallback_count": totals.get("fallback_count", 0),
            "timeout_count": totals.get("timeout_count", 0),
        }
        # 近期调用：每条改 prompt_tokens/completion_tokens
        normalized_recent = []
        for r in recent:
            normalized_recent.append({
                "model": r.get("model", ""),
                "prompt_tokens": r.get("input_tokens", r.get("prompt_tokens", 0)),
                "completion_tokens": r.get("output_tokens", r.get("completion_tokens", 0)),
                "total_tokens": r.get("total_tokens", 0),
                "latency_ms": r.get("latency_ms", 0),
                "timestamp": r.get("timestamp", ""),
                "fallback": r.get("fallback", False),
                "timeout": r.get("timeout", False),
            })
        handler._json(200, {
            "stats": flat_stats,  # 前端期望的扁平字段
            "stats_raw": raw_stats,  # 完整原始数据（保留）
            "recent": normalized_recent,
            "recent_limit": recent_limit,
        })
    except Exception as e:
        logger.exception(f"[/api/admin/tokens] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True