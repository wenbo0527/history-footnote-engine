"""GET /api/state — 当前 session 状态
POST /api/load — 加载存档到内存
"""
from __future__ import annotations

from urllib.parse import parse_qs

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.format_state import format_state
from history_footnote.web_server.views.session import _get_or_load_session


def handle_GET_state(handler, query) -> bool:
    qs = parse_qs(query)
    sid = qs.get("session_id", [None])[0]
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    try:
        game = _get_or_load_session(sid)
        if game is None:
            handler._json(404, {"error": "session not found"})
            return True
        handler._json(200, format_state(game))
    except Exception as e:
        logger.exception(f"[/api/state] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_load(handler, body) -> bool:
    sid = body.get("session_id")
    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True
    handler._json(200, format_state(game))
    return True
