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
    # 🆕 v1.7.30: 接 account_id（账户隔离）
    account_id = body.get("account_id", "") or ""
    game = new_session(era_id, identity, gender, custom_character=custom_character)
    # 把 account_id 绑定到 game.state（供 save 时持久化）
    if account_id and hasattr(game, 'state'):
        try:
            game.state.account_id = account_id
        except Exception:
            pass

    # 🆕 v2.5: 全局随机种子（replay 机制）
    # 玩家可传 seed 用同一 seed 重玩（分享 / debug / 重玩）
    # 不传则系统生成随机 seed
    from history_footnote.random_utils import (
        set_session_seed, generate_random_seed, make_seed_from_string,
    )
    sid = getattr(game, "session_id", None)
    requested_seed = body.get("seed")
    seed_str = body.get("seed_str")  # 例: "wanli-love-story"
    if requested_seed is not None and isinstance(requested_seed, int):
        actual_seed = requested_seed & 0xFFFFFFFF
    elif seed_str and isinstance(seed_str, str):
        actual_seed = make_seed_from_string(seed_str)
    else:
        actual_seed = generate_random_seed()
    if sid:
        set_session_seed(sid, actual_seed)
        if hasattr(game.state, 'seed'):
            game.state.seed = actual_seed
        logger.info(f"[v2.5] session {sid[:8]} seed={actual_seed}")

    # 🆕 v2.5: 命运卡抽 5 张 + 立即应用开局效果
    from history_footnote.fate_cards import draw_fate_cards, apply_fate_card
    try:
        fate_cards = draw_fate_cards(sid, n=5)
        # 把卡转为 dict 存到 state
        game.state.fate_hand = [
            {
                "id": c.id, "name": c.name, "icon": c.icon, "color": c.color,
                "description": c.description, "effect_type": c.effect_type,
                "effect_params": c.effect_params, "used": False,
                # 🆕 v2.6 主动使用字段
                "use_type": c.use_type,
                "use_constraints": c.use_constraints,
                "use_hint": c.use_hint,
            }
            for c in fate_cards
        ]
        logger.info(f"[v2.5] 抽命运卡 5 张: {[c.id for c in fate_cards]}")
    except Exception as e:
        logger.exception(f"[v2.5] 命运卡抽取失败: {e}")
        game.state.fate_hand = []
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
    # 🆕 v1.7.32: 开局也要生成"脑海中的声音"，否则 format_state 兜底只塞一个
    # 「自由输入」，玩家首屏只剩单个选项（Bug：开头没有声音）
    # 🆕 v2.3: 传 game 给 LLM 驱动（基于开场叙事的具体情境生成 3-4 个可执行动作）
    if opening_text:
        try:
            from history_footnote.web_server.routers.input import _context_aware_voices
            opening_voices = _context_aware_voices(opening_text, game=game)
            if opening_voices:
                state["last_voice_options"] = list(opening_voices)
                game.state.last_voice_options = list(opening_voices)
                logger.info(
                    f"[start] 注入 {len(opening_voices)} voice_options (context-aware from opening)"
                )
        except Exception as e:
            logger.exception(f"[start] 开场 voice_options 注入失败: {e}")
    handler._json(200, {
        "session_id": game.session.session_id,
        "seed": getattr(game.state, "seed", 0),  # 🆕 v2.5: 返回 seed（玩家可重玩）
        "fate_hand": getattr(game.state, "fate_hand", []),  # 🆕 v2.5: 命运卡手牌
        **state,
    })
    return True


def handle_GET_archives(handler, query) -> bool:
    from urllib.parse import parse_qs
    qs = parse_qs(query)
    era_id = qs.get("era_id", [None])[0]
    # 🆕 v1.7.30: 接 account 过滤
    account = qs.get("account", [None])[0]
    try:
        save_manager = get_save_manager_cached()
        sessions = save_manager.list_sessions(era_id=era_id, account_id=account)
        out = []
        for s in sessions[:20]:  # 增加 limit 到 20
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
                "account_id": getattr(s, "account_id", ""),
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
