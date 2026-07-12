"""GET /api/state — 当前 session 状态
POST /api/load — 加载存档到内存
POST /api/confirm_city_change — 确认城市变更
POST /api/reject_city_change — 拒绝城市变更
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


# 🆕 v2.10.1 W77: 城市变更确认路由
def handle_POST_confirm_city_change(handler, body) -> bool:
    """玩家确认到达新城市（应用 pending_city_change）"""
    sid = body.get("session_id")
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True
    pending = getattr(game.state, "pending_city_change", None)
    if not pending:
        handler._json(400, {"error": "no pending city change"})
        return True
    # 应用变更
    to_city = pending.get("to_city", "")
    if to_city:
        game.state.current_city = to_city
        logger.info(f"[W77] 玩家确认城市变更：→ {to_city}")
    # 清空 pending
    game.state.pending_city_change = None
    handler._json(200, format_state(game))


def handle_POST_reject_city_change(handler, body) -> bool:
    """玩家拒绝到达新城市（保持原 city，清空 pending）"""
    sid = body.get("session_id")
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True
    pending = getattr(game.state, "pending_city_change", None)
    if not pending:
        handler._json(400, {"error": "no pending city change"})
        return True
    from_city = pending.get("from_city", game.state.current_city)
    logger.info(f"[W77] 玩家拒绝城市变更：保持 {from_city}")
    # 清空 pending
    game.state.pending_city_change = None
    handler._json(200, format_state(game))
    return True
