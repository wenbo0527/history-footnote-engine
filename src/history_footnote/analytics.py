"""🆕 v2.10.x W65: 数据看板（章节/完成率/LLM 用量 BI）

- analytics_track_event(event_type, data) → None
- analytics_summary() → {total_sessions, completion_rate, llm_tokens, ...}
- analytics_by_era() → {era_id: {sessions, completed, total_chapters}}
"""
from __future__ import annotations
import time
import threading
from typing import Literal

_analytics_lock = threading.Lock()
_events: list[dict] = []


def analytics_track_event(event_type: str, data: dict | None = None) -> None:
    """追踪事件"""
    with _analytics_lock:
        _events.append({
            "type": event_type,
            "data": data or {},
            "ts": time.time(),
        })


def analytics_summary() -> dict:
    """汇总统计"""
    with _analytics_lock:
        sessions_created = sum(1 for e in _events if e["type"] == "session_created")
        chapters_completed = sum(1 for e in _events if e["type"] == "chapter_completed")
        llm_calls = sum(1 for e in _events if e["type"] == "llm_call")
        total_tokens = sum(
            (e["data"].get("prompt_tokens", 0) + e["data"].get("completion_tokens", 0))
            for e in _events if e["type"] == "llm_call"
        )
        return {
            "total_events": len(_events),
            "sessions_created": sessions_created,
            "chapters_completed": chapters_completed,
            "completion_rate": (
                chapters_completed / sessions_created
                if sessions_created > 0 else 0
            ),
            "llm_calls": llm_calls,
            "total_llm_tokens": total_tokens,
        }


def analytics_by_era() -> dict:
    """按 era 分组统计"""
    by_era: dict[str, dict] = {}
    with _analytics_lock:
        for e in _events:
            era = e["data"].get("era_id", "unknown")
            if era not in by_era:
                by_era[era] = {
                    "sessions": 0,
                    "completed": 0,
                    "total_chapters": 0,
                    "llm_tokens": 0,
                }
            if e["type"] == "session_created":
                by_era[era]["sessions"] += 1
            elif e["type"] == "chapter_completed":
                by_era[era]["completed"] += 1
                by_era[era]["total_chapters"] += 1
            elif e["type"] == "llm_call":
                by_era[era]["llm_tokens"] += (
                    e["data"].get("prompt_tokens", 0) +
                    e["data"].get("completion_tokens", 0)
                )
    return by_era


def analytics_clear() -> None:
    """清空（开发/测试用）"""
    with _analytics_lock:
        _events.clear()


def analytics_recent_events(limit: int = 20) -> list[dict]:
    """最近事件"""
    with _analytics_lock:
        return list(reversed(_events[-limit:]))
