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
# 🆕 v1.9.5 辅助函数
# ============================================================

def _flatten_custom_character(cc: dict | None) -> dict:
    """把 custom_character 关键字段铺平到顶层

    前端 char-card 用 state.character.name / .age / .background / .starting_situation
    但 custom_character 嵌套在 state.custom_character 里——平铺解决一致性
    """
    if not cc or not isinstance(cc, dict):
        return {}
    return {
        "name": cc.get("name", ""),
        "hometown": cc.get("hometown", ""),
        "age": cc.get("age"),
        "occupation": cc.get("occupation", cc.get("role", "")),
        "background": cc.get("background", ""),
        "starting_situation": cc.get("starting_situation", ""),
        "personality": cc.get("personality", ""),
        "tics": cc.get("tics", ""),
        "opening_paragraph": cc.get("opening_paragraph", ""),
        "voices": cc.get("voices", []),
        "skills": cc.get("skills", []),
        "family": cc.get("family", {}),
        "initial_state": cc.get("initial_state", {}),
    }


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
            # 🆕 v1.7.32 修复：保留 type 字段，让前端 mapper 区分
            # 真 narrative（type: opening/turn/none）和面板型 entry
            # （type: monthly_settlement/event_log），后者是月末结算或事件日志，
            # 不应作为「当前回合剧情」展示，会让玩家看不到真实叙事。
            "type": nh.get("type"),
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
        "current_city": getattr(s, "current_city", "shengze"),
        "unlocked_insights": sorted(s.unlocked_insights),
        "triggered_events": sorted(s.triggered_events),
        "variables": dict(s.variables),
        "value_shifts": dict(s.value_shifts),
        "recent_narratives": recent_narr,
        # 🐛 v1.5.1 P0 Bug #1 修复：暴露 custom_character 给前端
        "custom_character": getattr(s, "custom_character", {}),
        # 🆕 v1.9.5：把 custom_character 的关键字段也铺平到顶层（前端兼容用）
        # 这样 sidebar/character-card 不需要深嵌套取 cc.background / cc.name
        "character": _flatten_custom_character(getattr(s, "custom_character", {})),
        # 🆕 v2.10.1 W77: 待确认的城市变更
        "pending_city_change": getattr(s, "pending_city_change", None),
        # 🐛 v1.5.1 P1 Issue 5 修复：暴露 last_voice_options 给前端
        "last_voice_options": list(getattr(s, "last_voice_options", []) or []),
        # 🆕 v2.10.5: 暴露 voice_options_pending 给前端
        # True = 后台线程还在生成 voice_options（前端可显示"思考中"）
        "voice_options_pending": bool(getattr(s, "voice_options_pending", False)),
        # 🆕 v1.7.26 侧边栏固化面板数据
        "sidebar_data": build_sidebar_data(s, recent_narr),
        # 🆕 v1.7.28：已完成任务计数（前端展示 + 弹层入口）
        "completed_tasks_count": len(getattr(s, "completed_tasks", []) or []),
        # 🆕 v1.7.30 财务结构化字段
        "cash": getattr(s, "cash", 0.0),
        "rice": getattr(s, "rice", 0.0),
        "debt": getattr(s, "debt", 0.0),
        "monthly_burn": getattr(s, "monthly_burn", 0.0),
        "financial_log": list(getattr(s, "financial_log", []) or []),
        # 🆕 v1.7.30 家人 + 谱系
        "family_members": list(getattr(s, "family_members", []) or []),
        "genealogy": list(getattr(s, "genealogy", []) or []),
        # 🆕 v1.7.30 城市财产 + 跨城库存
        "city_properties": dict(getattr(s, "city_properties", {}) or {}),
        "inventory": dict(getattr(s, "inventory", {}) or {}),
        # 🆕 v1.7.30 本次发现层（discoveries）
        "discoveries": dict(getattr(s, "discoveries", {}) or {}),
        # 🆕 v2.5 全局随机种子（replay 机制）
        "seed": int(getattr(s, "seed", 0) or 0),
        # 🆕 v2.5 命运卡（玩家一打开就看到自己的卡）
        "fate_hand": list(getattr(s, "fate_hand", []) or []),
        "fate_used": list(getattr(s, "fate_used", []) or []),
        "fate_event_flags": list(getattr(s, "fate_event_flags", []) or []),
        # 🆕 v2.5 NPC 关系 + 当前 buff（命运卡影响展示）
        "npc_relations": dict(getattr(s, "npc_relations", {}) or {}),
        "active_buffs": list(getattr(s, "active_buffs", []) or []),
    }
    # 🆕 v1.7.32 修复：移除 voice_freetext 兜底。
    # 原因：前端 InputArea 已是独立 textarea（不是 voice_options 的一部分），
    # 这个「自由输入」voice 卡是冗余的。删除后：
    #  - /api/state 加载存档时（last_voice_options=[]）会返空数组
    #  - 加载时由 _get_or_load_session 调 _context_aware_voices 注入真 voices
    #  - 玩家看到"暂无选项，直接在下方输入"，体验比看到重复项更清晰
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
