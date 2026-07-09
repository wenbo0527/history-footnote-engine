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
        # 🆕 v2.6.2: 附加 npc_relations（命运卡/事件已应用的 NPC 关系）
        npc_relations = list((getattr(game.state, "npc_relations", {}) or {}).items())
        # 🆕 v2.6.2: 命运卡对 NPC 的影响清单（用 modify_npc 的卡）
        fate_hand = list(getattr(game.state, "fate_hand", []) or [])
        fate_npc_effects = []
        for card in fate_hand:
            if not card.get("used"):
                continue
            if card.get("effect_type") == "modify_npc":
                params = card.get("effect_params", {}) or {}
                fate_npc_effects.append({
                    "card_id": card.get("id"),
                    "card_name": card.get("name"),
                    "card_icon": card.get("icon"),
                    "npc": params.get("npc", ""),
                    "affinity_delta": params.get("affinity_delta", 0),
                })
        # 🆕 v2.6.2: 当前 buff
        active_buffs = list(getattr(game.state, "active_buffs", []) or [])
        handler._json(200, {
            "session_id": sid,
            "wiki": wiki,
            "npc_relations": npc_relations,      # 列表 [(npc, affinity), ...]
            "fate_npc_effects": fate_npc_effects,  # 命运卡 → NPC 影响清单
            "active_buffs": active_buffs,        # 当前 buff
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
    # 🆕 v1.7.32 修复：默认返所有完整叙事（recent=NARRATIVE_RECENT_SIZE=20），
    # 让玩家在"回顾"里看到每一回合的完整 DM 叙事，不是只看到最近 5 条 + 20 条摘要。
    from history_footnote.game_state import GameState
    default_recent = GameState.NARRATIVE_RECENT_SIZE
    default_archive = GameState.NARRATIVE_ARCHIVE_SIZE
    # 🆕 v1.7.32 修复：get(key, default) 当 value=None 时返 None 不用 default——
    # 必须用 `if key in body` 显式区分"未传"和"传了 None"
    recent_count = body["recent_count"] if "recent_count" in body else default_recent
    archive_count = body["archive_count"] if "archive_count" in body else default_archive
    logger.info(f"[recap] requested recent_count={recent_count} (default={default_recent}), archive_count={archive_count}")
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    # 🆕 v1.7.32 修复：用 _get_or_load_session 替代 session_get，自动从存档加载
    # 否则玩家跨页面 / 跨重启进入游戏，第一次直接点"回顾"会 404（必须先调过 /api/state 触发加载）
    game = _get_or_load_session(sid)
    if game is None:
        handler._json(404, {"error": "session not found"})
        return True
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
