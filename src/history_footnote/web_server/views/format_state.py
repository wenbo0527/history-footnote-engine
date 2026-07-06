"""🆕 v1.7.29 状态序列化层：把 GameLoop 内部 state 转成前端可消费的 dict。

包含：
- format_state(game)            — 序列化完整 state（API 响应主体）
- build_sidebar_data(state, ...) — 构建侧边栏 3 面板（任务/还债/财务）
- detect_intent(player_input, dm_response) — 统一意图判定

设计：
- 纯函数（接受 GameLoop 实例，返回 dict）便于单测
- 这是 view 层唯一对外的公共 API
"""
from __future__ import annotations

import logging

from history_footnote.web_server.handler_base import logger


# ============================================================
# 侧边栏数据
# ============================================================

def build_sidebar_data(state, recent_narratives: list) -> dict:
    """🆕 v1.7.26: 构建侧边栏数据（任务/还债/财务）

    1. 先从 state 取（如果 LLM 主动写入）
    2. 兜底：从最新 narrative 解析或推断
    """
    # 优先用 state 上的固化数据
    if state.active_tasks or state.upcoming_deadlines or state.financial_status:
        return {
            "active_tasks": list(state.active_tasks),
            "upcoming_deadlines": list(state.upcoming_deadlines),
            "financial_status": dict(state.financial_status),
        }
    # 兜底：从最新 narrative 解析
    if recent_narratives:
        latest = recent_narratives[-1].get("narrative", "")
        from history_footnote.sidebar_parser import build_sidebar_data as _parse_sidebar
        # 🆕 v1.7.27: 传入 existing_tasks 实现持久化（防丢）
        result = _parse_sidebar(latest, state.variables, state.active_tasks)
        # 🆕 v1.7.27: 解析结果写回 state（持久化）
        state.active_tasks = result.get("active_tasks", state.active_tasks)
        return result
    return {
        "active_tasks": [],
        "upcoming_deadlines": [],
        "financial_status": {},
    }


# ============================================================
# 完整 state 序列化
# ============================================================

def format_state(game) -> dict:
    """序列化当前游戏状态供前端展示

    Args:
        game: GameLoop 实例
    """
    s = game.state
    recent_narr = []
    for nh in s.narrative_history[-3:]:
        recent_narr.append({
            "round": nh.get("round"),
            "summary": nh.get("summary", ""),
            "narrative": nh.get("narrative", ""),
        })
    result = {
        "session_id": game.session.session_id,
        "era_id": game.era_id,
        "era_name": game.era_config.get("era_name", game.era_id),
        "round_number": s.round_number,
        "current_date": s.current_date,
        "action_points_current": s.action_points_current,
        "action_points_max": s.action_points_max,
        "selected_identity": s.selected_identity,
        "player_gender": s.player_gender,
        "unlocked_insights": sorted(s.unlocked_insights),
        "triggered_events": sorted(s.triggered_events),
        "variables": dict(s.variables),
        "value_shifts": dict(s.value_shifts),
        "recent_narratives": recent_narr,
        # 🐛 v1.5.1 P0 Bug #1 修复：暴露 custom_character 给前端
        "custom_character": getattr(s, "custom_character", {}),
        # 🐛 v1.5.1 P1 Issue 5 修复：暴露 last_voice_options 给前端
        "last_voice_options": list(getattr(s, "last_voice_options", []) or []),
        # 🆕 v1.7.26 侧边栏固化面板数据
        "sidebar_data": build_sidebar_data(s, recent_narr),
        # 🆕 v1.7.28：已完成任务计数（前端展示 + 弹层入口）
        "completed_tasks_count": len(getattr(s, "completed_tasks", []) or []),
    }
    # 兜底注入（如果空）
    if not result["last_voice_options"]:
        result["last_voice_options"] = [{
            "voice_id": "voice_freetext",
            "voice_name": "✍️ 自由输入",
            "intent_text": "",
            "is_freetext": True,
        }]
    return result


# ============================================================
# Intent 检测（DRY：/api/input 用）
# ============================================================

def detect_intent(player_input: str, dm_response: dict) -> str:
    """🐛 v1.5.1 P1 Issue 6 修复：统一意图判定

    优先用 dm_skills._detect_intent_type（规则判定，更可靠），
    LLM 返回的 intent_type 仅作 fallback。
    """
    try:
        from history_footnote.dm_skills import _detect_intent_type
        rule_intent = _detect_intent_type(player_input)
        if rule_intent and rule_intent != "action":
            # 规则判定为 describe/inquire → 比 LLM 更可靠
            return rule_intent
    except Exception:
        logger.exception("intent 检测失败")
        pass
    # Fallback: LLM 返回的 intent_type
    return dm_response.get("intent_type", "action")


# ============================================================
# Wiki summary 安全渲染（XSS 兜底）
# ============================================================

def render_wiki_summary_safe(wiki) -> str:
    """🆕 v1.7.1 安全地渲染 wiki summary（用于 HTTP API）"""
    try:
        from history_footnote.character_wiki import render_wiki_summary
        return render_wiki_summary(wiki)
    except Exception:
        logger.exception("wiki summary 渲染失败")
        return ""
