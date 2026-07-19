"""🆕 v2.10.x W59: 章节回放功能

重看历史章节（含 LLM 真实输出）
- replay_chapter(session_id, chapter) → {chapter, narrative, choices, summary}
- replay_chapter_meta(session_id, chapter) → {started_at, ended_at, round_count}
"""
from __future__ import annotations
import time
from typing import Literal

_replay_lock = None  # 不需锁（纯函数）
_replay_storage: dict[str, dict[int, dict]] = {}


def replay_record_chapter(
    session_id: str,
    chapter: int,
    narrative: str,
    choices: list[dict],
    summary: str,
    started_at: float,
    ended_at: float,
) -> None:
    """记录章节回放数据"""
    if session_id not in _replay_storage:
        _replay_storage[session_id] = {}
    _replay_storage[session_id][chapter] = {
        "chapter": chapter,
        "narrative": narrative,
        "choices": choices,
        "summary": summary,
        "started_at": started_at,
        "ended_at": ended_at,
        "round_count": len(choices),
    }


def replay_chapter(session_id: str, chapter: int) -> dict | None:
    """获取章节回放数据"""
    if session_id not in _replay_storage:
        return None
    return _replay_storage[session_id].get(chapter)


def replay_chapter_meta(session_id: str, chapter: int) -> dict | None:
    """获取章节元信息"""
    data = replay_chapter(session_id, chapter)
    if not data:
        return None
    return {
        "chapter": data["chapter"],
        "started_at": data["started_at"],
        "ended_at": data["ended_at"],
        "round_count": data["round_count"],
        "duration_seconds": data["ended_at"] - data["started_at"],
    }


def replay_list_chapters(session_id: str) -> list[int]:
    """列出 session 所有已记录章节"""
    if session_id not in _replay_storage:
        return []
    return sorted(_replay_storage[session_id].keys())


def replay_delete_chapter(session_id: str, chapter: int) -> bool:
    if session_id not in _replay_storage:
        return False
    if chapter in _replay_storage[session_id]:
        del _replay_storage[session_id][chapter]
        return True
    return False


def replay_clear_session(session_id: str) -> None:
    if session_id in _replay_storage:
        del _replay_storage[session_id]
