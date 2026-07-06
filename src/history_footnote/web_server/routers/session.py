"""Session 管理路由：

POST /api/start               — 启动新游戏
GET  /api/archives            — 列出存档
POST /api/archive/delete      — 删除单个存档
POST /api/archives/clear      — 清空某 era 所有存档
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

from history_footnote.resource_cache import get_save_manager as get_save_manager_cached
from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.format_state import format_state
from history_footnote.web_server.views.session import new_session, session_pop


def handle_POST_start(handler, body) -> bool:
    era_id = body.get("era_id", "wanli1587")
    identity = body.get("identity", "weaving_male")
    gender = body.get("gender", "male")
    custom_character = body.get("character")
    game = new_session(era_id, identity, gender, custom_character=custom_character)
    # 捕获开场白到 narrative_history
    buf = io.StringIO()
    with redirect_stdout(buf):
        game._print_opening()
    opening_text = buf.getvalue().strip()
    if opening_text:
        game.state.append_narrative(0, opening_text, "开场")
    # 🆕 v1.7.22: start 时不注入 freetext 占位
    state = format_state(game)
    state.pop("last_voice_options", None)
    state["last_voice_options"] = []
    handler._json(200, {"session_id": game.session.session_id, **state})
    return True


def handle_GET_archives(handler, query) -> bool:
    from urllib.parse import parse_qs
    qs = parse_qs(query)
    era_id = qs.get("era_id", [None])[0]
    try:
        save_manager = get_save_manager_cached()
        sessions = save_manager.list_sessions(era_id=era_id)
        out = []
        for s in sessions[:10]:
            out.append({
                "session_id": s.session_id,
                "era_id": s.era_id,
                "current_round": getattr(s, "current_round", 0),
                "current_date": getattr(s, "current_date", ""),
                "summary": getattr(s, "summary", ""),
                "created_at": getattr(s, "created_at", ""),
                "last_saved_at": getattr(s, "last_saved_at", ""),
                "selected_identity": getattr(s, "selected_identity", ""),
                "player_gender": getattr(s, "player_gender", ""),
            })
        handler._json(200, {"archives": out})
    except Exception as e:
        logger.exception("[/api/archives] 失败: %s", e)
        handler._json(500, {"error": f"列出存档失败: {e}", "archives": []})
    return True


def handle_POST_archive_delete(handler, body) -> bool:
    sid = body.get("session_id", "").strip()
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    try:
        save_manager = get_save_manager_cached()
        if "/" in sid or "\\" in sid or ".." in sid:
            handler._json(400, {"error": "invalid session_id"})
            return True
        if not save_manager.find_session(sid):
            handler._json(404, {"error": "session not found", "session_id": sid})
            return True
        ok = save_manager.delete_session(sid)
        if ok:
            session_pop(sid)
            logger.info(f"[/api/archive/delete] Deleted archive: {sid}")
            handler._json(200, {"ok": True, "session_id": sid, "deleted": True})
        else:
            handler._json(500, {"error": "delete failed", "session_id": sid})
    except Exception as e:
        logger.exception(f"[/api/archive/delete] 失败: {e}")
        handler._json(500, {"error": f"delete failed: {e}"})
    return True


def handle_POST_archives_clear(handler, body) -> bool:
    era_id = body.get("era_id", "").strip()
    confirm = body.get("confirm", False)
    if not era_id:
        handler._json(400, {"error": "missing era_id"})
        return True
    if not confirm:
        handler._json(400, {"error": "需要 confirm=true 二次确认"})
        return True
    try:
        save_manager = get_save_manager_cached()
        sessions = save_manager.list_sessions(era_id=era_id)
        if not sessions:
            handler._json(200, {"ok": True, "deleted_count": 0, "deleted_ids": []})
            return True
        deleted_ids, failed = [], []
        for s in sessions:
            sid = s.session_id
            if "/" in sid or "\\" in sid or ".." in sid:
                failed.append(sid)
                continue
            if save_manager.delete_session(sid):
                deleted_ids.append(sid)
                session_pop(sid)
            else:
                failed.append(sid)
        logger.info(f"[/api/archives/clear] Cleared {len(deleted_ids)} archives for era {era_id}")
        handler._json(200, {
            "ok": True,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "failed": failed,
        })
    except Exception as e:
        logger.exception(f"[/api/archives/clear] 失败: {e}")
        handler._json(500, {"error": f"clear failed: {e}"})
    return True
