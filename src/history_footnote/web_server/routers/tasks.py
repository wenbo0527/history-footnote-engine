"""任务管理路由：

POST /api/task/complete — 标记任务完成
POST /api/task/add      — 手动添加任务
"""
from __future__ import annotations

from history_footnote.web_server.handler_base import logger, safe_error_id
from history_footnote.web_server.views.session import _get_or_load_session


"""POST /api/task/complete — 标记任务完成"""
def handle_POST_task_complete(handler, body) -> bool:
    sid = body.get("session_id")
    title = body.get("title", "").strip()
    if not sid or not title:
        handler._json(400, {"error": "session_id and title required"})
        return True
    game = _get_or_load_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True
    try:
        from history_footnote.sidebar_parser import mark_task_completed
        new_active, completed, found = mark_task_completed(
            game.state.active_tasks, title, game.state.round_number
        )
        if not found:
            handler._json(404, {
                "session_id": sid,
                "title": title,
                "status": "not_found",
                "message": "任务不存在或已完成",
            })
            return True
        game.state.active_tasks = new_active
        game.state.completed_tasks.extend(completed)
        handler._json(200, {
            "session_id": sid,
            "title": title,
            "status": "completed",
            "completed_round": game.state.round_number,
            "active_count": len(new_active),
            "completed_count": len(game.state.completed_tasks),
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[task/complete] {error_id} failed: {e}")
        handler._json(500, {"error": "task complete failed", "error_id": error_id})
    return True


def handle_POST_task_add(handler, body) -> bool:
    sid = body.get("session_id")
    title = body.get("title", "").strip()
    urgency = body.get("urgency", "normal")
    if not sid or not title:
        handler._json(400, {"error": "session_id and title required"})
        return True
    game = _get_or_load_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True
    existing_titles = {t.get("title") for t in game.state.active_tasks}
    if title in existing_titles:
        handler._json(200, {
            "session_id": sid,
            "title": title,
            "status": "duplicate",
            "message": "任务已存在，未重复添加",
        })
        return True
    game.state.active_tasks.append({
        "title": title,
        "urgency": urgency,
        "status": "pending",
        "created_round": game.state.round_number,
        "completed_round": None,
    })
    handler._json(200, {
        "session_id": sid,
        "title": title,
        "status": "added",
        "created_round": game.state.round_number,
        "active_count": len(game.state.active_tasks),
    })
    return True
