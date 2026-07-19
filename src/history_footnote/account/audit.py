"""🆕 v1.8.0 Audit Logger

设计：
- JSONL append-only
- WatchedFileHandler 自动 flush
- 每天 rotation（外部 cron 或手动）
- 保留 30 天（外部 logrotate）

事件类型：
- login_ok / login_fail / account_locked
- action / logout / session_expired / kill_sessions
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import Optional


_AUDIT_LOGGER_NAME = "hfe_audit"
_AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "saves/audit.log")


def _get_audit_logger() -> logging.Logger:
    """获取单例 logger"""
    logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    if not logger.handlers:
        Path(_AUDIT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        handler = WatchedFileHandler(_AUDIT_LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


_LOCK = threading.Lock()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def audit_log(
    event: str,
    account_id: str = "",
    session_id: str = "",
    route: str = "",
    method: str = "",
    status: int = 0,
    latency_ms: int = 0,
    ip: str = "",
    user_agent: str = "",
    **kwargs,
) -> None:
    """写一条 audit 记录

    Args:
        event: 事件类型（login_ok / login_fail / action / logout / ...）
        account_id: 账户 ID
        session_id: session ID
        route: 路由路径
        method: HTTP 方法
        status: HTTP 状态码
        latency_ms: 耗时毫秒
        ip: 客户端 IP
        user_agent: User-Agent
        **kwargs: 其他字段
    """
    record = {
        "ts": _now_iso(),
        "event": event,
        "account_id": account_id,
        "session_id": session_id[:32] if session_id else "",
        "route": route,
        "method": method,
        "status": status,
        "latency_ms": latency_ms,
        "ip": ip,
        "user_agent": user_agent[:200] if user_agent else "",
    }
    # 合并 kwargs
    for k, v in kwargs.items():
        if k not in record:
            record[k] = v
    with _LOCK:
        try:
            line = json.dumps(record, ensure_ascii=False)
            _get_audit_logger().info(line)
        except Exception:
            pass  # audit 失败不阻塞主流程


def get_audit_log_path() -> Path:
    return Path(_AUDIT_LOG_PATH)
