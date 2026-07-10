"""🆕 v2.8.0 章节制 API（章节 UI 数据暴露）

路由：
- GET  /api/chapter/state       — 当前 session 的章节状态（章节进度条用）
- GET  /api/chapter/blueprint   — 当前章节蓝图（UI 展示各节点 scene + options）
- POST /api/chapter/record_choice — 记录玩家选项（写入 recent_path_choices）
- GET  /api/chapter/history     — 章节历史（已结算章节摘要）

设计：
- 纯 GET 暴露数据，不修改 state（除 /record_choice）
- 返回格式与 ChapterCoordinator 模型对齐（chapter_state nested dict）
- 旧 session 兼容：chapter_state 字段缺时返回空值
"""
from __future__ import annotations

from urllib.parse import parse_qs
import logging

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.session import _get_or_load_session


def _get_game_or_404(handler, sid):
    """公共辅助：拿 session game，找不到返 404"""
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return None
    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return None
    return game


def handle_GET_chapter_state(handler, query) -> bool:
    """GET /api/chapter/state — 章节状态（进度条 + 节点定位）"""
    qs = parse_qs(query)
    sid = qs.get("session_id", [None])[0]
    game = _get_game_or_404(handler, sid)
    if game is None:
        return True

    try:
        cs = getattr(game.state, "chapter_state", None)
        if cs is None:
            handler._json(200, {
                "active": False,
                "current_chapter": 0,
                "current_node": 1,
                "chapter_start_round": 1,
                "last_closure_status": "INIT",
            })
            return True

        current_chapter = cs.current_chapter
        active = current_chapter > 0
        # 计算节点进度（如 1/4 → 25%）
        if active and cs.blueprint:
            meta = cs.blueprint.get("meta", {}) if isinstance(cs.blueprint, dict) else {}
            node_count = int(meta.get("suggested_node_count", 4)) if meta else 4
            progress_pct = round(cs.current_node / node_count * 100, 1) if node_count > 0 else 0
        else:
            node_count = 4
            progress_pct = 0.0

        handler._json(200, {
            "active": active,
            "current_chapter": current_chapter,
            "current_node": cs.current_node,
            "node_count": node_count,
            "chapter_start_round": cs.chapter_start_round,
            "round_number": game.state.round_number,
            "rounds_elapsed": max(0, game.state.round_number - cs.chapter_start_round + 1) if active else 0,
            "last_closure_status": cs.last_closure_status,
            "progress_pct": progress_pct,
            # 🆕 v2.8.0 段四 Build 字段
            "player_build": getattr(game.state, "player_build", ""),
            # 🆕 v2.8.0 段三 路径字段
            "main_path_focus": getattr(game.state.path_state, "main_path_focus", "") if hasattr(game.state, "path_state") else "",
            # 🆕 v2.8.0 段五 板块张力（取第一个 shifting 板块）
            "active_plate": _first_shifting_plate(game),
        })
    except Exception as e:
        logger.exception(f"[/api/chapter/state] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_chapter_blueprint(handler, query) -> bool:
    """GET /api/chapter/blueprint — 当前章节蓝图（节点 scene + options）"""
    qs = parse_qs(query)
    sid = qs.get("session_id", [None])[0]
    game = _get_game_or_404(handler, sid)
    if game is None:
        return True

    try:
        cs = getattr(game.state, "chapter_state", None)
        if cs is None or not cs.blueprint:
            handler._json(200, {"active": False, "nodes": [], "meta": None})
            return True

        blueprint = cs.blueprint
        # 🔁 仅返回当前节点的简单形式（前端一次只展示一个）
        handler._json(200, {
            "active": True,
            "chapter_id": blueprint.get("chapter_id"),
            "chapter_title": blueprint.get("chapter_title", ""),
            "chapter_subtitle": blueprint.get("chapter_subtitle", ""),
            "transition_hint": blueprint.get("transition_hint", "season"),
            "current_node": cs.current_node,
            "nodes": blueprint.get("nodes", []),
            "meta": blueprint.get("meta", {}),
        })
    except Exception as e:
        logger.exception(f"[/api/chapter/blueprint] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_record_choice(handler, body) -> bool:
    """POST /api/chapter/record_choice — 记录玩家选项（写入 recent_path_choices）"""
    sid = body.get("session_id")
    path = body.get("path", "")
    game = _get_game_or_404(handler, sid)
    if game is None:
        return True

    try:
        # 委托给 ChapterFacade.record_path_choice
        from history_footnote.sub_facades import ChapterFacade
        from history_footnote.game_engine_facade import GameEngineFacade
        # 拿 facade（不构造新的，复用 engine 内的）
        facade = ChapterFacade(
            state=game.state,
            era_config=game.era_config,
            root_dir=None,
        )
        facade.record_path_choice(path)
        handler._json(200, {
            "recorded": True,
            "path": path,
            "recent_path_choices": getattr(game.state, "recent_path_choices", [])[-5:],
        })
    except Exception as e:
        logger.exception(f"[/api/chapter/record_choice] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_chapter_history(handler, query) -> bool:
    """GET /api/chapter/history — 章节历史摘要列表"""
    qs = parse_qs(query)
    sid = qs.get("session_id", [None])[0]
    game = _get_game_or_404(handler, sid)
    if game is None:
        return True

    try:
        cs = getattr(game.state, "chapter_state", None)
        history = getattr(cs, "chapter_history", []) if cs else []
        handler._json(200, {
            "count": len(history),
            "history": history,
        })
    except Exception as e:
        logger.exception(f"[/api/chapter/history] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def _first_shifting_plate(game) -> str:
    """辅助：返回当前状态最值得关注的板块 ID（shifting 优先）"""
    ps = getattr(game.state, "plate_state", None)
    if ps is None:
        return ""
    for pid, status in (ps.statuses or {}).items():
        if status in ("shifting", "collapsed"):
            return pid
    return ""
