"""🆕 v2.10.x W58: 多用户协作（共享 session）"""
from __future__ import annotations
import time
from typing import Literal

# 简单协作（单线程版本）
_collab_sessions: dict[str, dict] = {}


def collab_create(session_id: str, max_users: int = 4) -> str:
    collab_id = f"collab_{session_id}_{int(time.time() * 1000000)}"
    _collab_sessions[collab_id] = {
        "session_id": session_id,
        "max_users": max_users,
        "users": [],
        "round": 0,
        "narrative": "",
        "created_at": time.time(),
    }
    return collab_id


def collab_join(collab_id: str, user_id: str) -> bool:
    if collab_id not in _collab_sessions:
        return False
    c = _collab_sessions[collab_id]
    if len(c["users"]) >= c["max_users"]:
        return False
    if user_id in c["users"]:
        return True
    c["users"].append(user_id)
    return True


def collab_leave(collab_id: str, user_id: str) -> bool:
    if collab_id not in _collab_sessions:
        return False
    c = _collab_sessions[collab_id]
    if user_id in c["users"]:
        c["users"].remove(user_id)
        return True
    return False


def collab_action(collab_id: str, user_id: str, action: str) -> dict | None:
    if collab_id not in _collab_sessions:
        return None
    c = _collab_sessions[collab_id]
    if user_id not in c["users"]:
        return None
    c["round"] += 1
    c["narrative"] += f"\n[Round {c['round']}] {user_id}: {action}"
    return collab_state(collab_id)


def collab_state(collab_id: str) -> dict | None:
    if collab_id not in _collab_sessions:
        return None
    c = _collab_sessions[collab_id]
    return {
        "collab_id": collab_id,
        "session_id": c["session_id"],
        "users": list(c["users"]),
        "max_users": c["max_users"],
        "round": c["round"],
        "narrative": c["narrative"],
        "created_at": c["created_at"],
    }


def collab_list() -> list[str]:
    return list(_collab_sessions.keys())


def collab_delete(collab_id: str) -> bool:
    if collab_id in _collab_sessions:
        del _collab_sessions[collab_id]
        return True
    return False
