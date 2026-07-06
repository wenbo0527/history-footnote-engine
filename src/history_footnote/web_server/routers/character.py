"""角色 Wiki 路由：

GET  /api/character_wiki        — 获取角色 wiki
POST /api/character_wiki_update — 更新某 entry
POST /api/recap                 — 剧情回顾（也是 character_wiki 的视图）
"""
from __future__ import annotations

from history_footnote.web_server.handler_base import logger, safe_error_id
from history_footnote.web_server.views.session import _get_or_load_session, session_get


def handle_GET_character_wiki(handler, query) -> bool:
    from urllib.parse import parse_qs
    qs = parse_qs(query)
    sid = qs.get("session_id", [None])[0]
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    game = _get_or_load_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True
    try:
        wiki = game.state.character_wiki or {}
        handler._json(200, {
            "session_id": sid,
            "wiki": wiki,
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[character_wiki] {error_id} failed: {e}")
        handler._json(500, {"error": "wiki fetch failed", "error_id": error_id})
    return True


def handle_POST_character_wiki_update(handler, body) -> bool:
    sid = body.get("session_id")
    entry_kind = body.get("kind", "")
    entry_id = body.get("entry_id", "")
    note = body.get("note", "")
    if not sid or not entry_kind or not entry_id:
        handler._json(400, {"error": "session_id, kind, entry_id required"})
        return True
    game = _get_or_load_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True
    try:
        from history_footnote.character_wiki import CharacterWiki
        wiki = CharacterWiki.from_dict(game.state.character_wiki or {})
        wiki.manual_update(kind=entry_kind, entry_id=entry_id, note=note)
        game.state.character_wiki = wiki.to_dict()
        handler._json(200, {"ok": True, "kind": entry_kind, "entry_id": entry_id})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[character_wiki_update] {error_id} failed: {e}")
        handler._json(500, {"error": "wiki update failed", "error_id": error_id})
    return True


def handle_POST_recap(handler, body) -> bool:
    sid = body.get("session_id")
    recent_count = body.get("recent_count", 5)
    archive_count = body.get("archive_count", 30)
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    entry = session_get(sid)
    if entry is None:
        handler._json(404, {"error": "session not found or not loaded"})
        return True
    game = entry[0]
    try:
        recap = game.state.get_recap(
            recent_count=int(recent_count),
            archive_count=int(archive_count),
        )
        handler._json(200, recap)
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[recap] {error_id} failed: {e}")
        handler._json(500, {"error": "recap failed", "error_id": error_id})
    return True
