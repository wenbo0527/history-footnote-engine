"""🆕 v2.10.16 Phase 10 — 故事模式路由（零 LLM）

路由：
- POST /api/scripted/start   - 开始剧本（reset state）
- POST /api/scripted/input    - 玩家选择 voice_id
- GET  /api/scripted/state    - 查看当前节点 + options
"""
from __future__ import annotations

from history_footnote.story_mode import get_engine
from history_footnote.web_server.handler_base import logger, safe_route
from history_footnote.web_server.views.session import _get_or_load_session


@safe_route(scope="scripted_start")
def handle_POST_scripted_start(handler, body) -> bool:
    """开始故事模式"""
    sid = body.get("session_id")
    chapter_id = body.get("chapter_id", 1)
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True

    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True

    engine = get_engine()
    # 用 dict 而不是对象（这样 _apply_effects 能改字段）
    state_dict = game.__dict__ if hasattr(game, "__dict__") else game

    narr, options = engine.start_chapter(state_dict, chapter_id)
    options_export = engine.export_voice_options(options)

    # 保存
    try:
        if hasattr(game, "save"):
            game.save()
    except Exception as e:
        logger.warning(f"save failed: {e}")

    handler._json(200, {
        "narrative": narr,
        "voice_options": options_export,
        "scripted_mode": True,
        "scripted_chapter_id": chapter_id,
        "scripted_node_id": state_dict.get("scripted_node_id"),
        "cash": state_dict.get("cash"),
        "city": state_dict.get("city"),
        "llm_calls": 0,  # 关键指标：0 LLM 调用
    })
    return True


@safe_route(scope="scripted_input")
def handle_POST_scripted_input(handler, body) -> bool:
    """玩家选择"""
    sid = body.get("session_id")
    voice_id = body.get("input", "").strip() or body.get("voice_id", "").strip()
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    if not voice_id:
        handler._json(400, {"error": "missing input or voice_id"})
        return True

    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True

    state_dict = game.__dict__ if hasattr(game, "__dict__") else game
    engine = get_engine()

    # 检查是否在故事模式
    if not state_dict.get("scripted_mode"):
        handler._json(400, {"error": "not in scripted mode. call /api/scripted/start first"})
        return True

    narr, options, info = engine.handle_input(state_dict, voice_id)
    options_export = engine.export_voice_options(options)

    # 保存
    try:
        if hasattr(game, "save"):
            game.save()
    except Exception as e:
        logger.warning(f"save failed: {e}")

    handler._json(200, {
        "narrative": narr,
        "voice_options": options_export,
        "scripted_node_id": info.get("new_node_id"),
        "chapter_complete": info.get("chapter_complete", False),
        "effects_applied": info.get("effects_applied", {}),
        "flag_added": info.get("flag_added", []),
        "cash": state_dict.get("cash"),
        "debt": state_dict.get("debt"),
        "rice": state_dict.get("rice"),
        "looms": state_dict.get("looms"),
        "city": state_dict.get("city"),
        "scripted_flags": state_dict.get("scripted_flags", []),
        "llm_calls": 0,
    })
    return True


@safe_route(scope="scripted_state")
def handle_GET_scripted_state(handler, query) -> bool:
    """查看当前故事状态"""
    from urllib.parse import parse_qs
    qs = parse_qs(query)
    sid = qs.get("session_id", [None])[0]
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True

    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True

    state_dict = game.__dict__ if hasattr(game, "__dict__") else game
    engine = get_engine()
    narr, options = engine.get_current(state_dict)
    options_export = engine.export_voice_options(options)

    handler._json(200, {
        "scripted_mode": state_dict.get("scripted_mode", False),
        "scripted_chapter_id": state_dict.get("scripted_chapter_id", 0),
        "scripted_node_id": state_dict.get("scripted_node_id", ""),
        "scripted_flags": state_dict.get("scripted_flags", []),
        "scripted_visits": state_dict.get("scripted_visits", []),
        "scripted_chapter_complete": state_dict.get("scripted_chapter_complete", False),
        "narrative": narr,
        "voice_options": options_export,
        "llm_calls": 0,
    })
    return True