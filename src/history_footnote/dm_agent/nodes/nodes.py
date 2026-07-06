"""🆕 v1.7.42 DM Agent Nodes 拆分（实际 node 实现）"""
from __future__ import annotations

import logging
from typing import TypedDict


_LOG = logging.getLogger("history_footnote.dm_agent.nodes")


# ============= DM State TypedDict =============

class DMState(TypedDict, total=False):
    """DM Agent 状态（LangGraph 流转用）"""
    player_input: str
    view_state: dict
    narrative: str
    skills_used: list
    forced_events: list
    triggered_rules: list
    pacing_directives: dict
    insight_candidates: list
    calendar_events: str
    wiki_hint: str
    drama_hint: str
    action_context: dict
    random_events: str
    round_number: int


# ============= Node 1: skill_orchestration_node =============

def make_skill_orchestration_node(llm_with_tools, state_ref):
    """技能编排节点（选择要用的 skills）"""
    def skill_orchestration_node(state: DMState) -> dict:
        skills_used = []
        return {"skills_used": skills_used}
    return skill_orchestration_node


# ============= Node 2: situation_assessment_node =============

def make_situation_assessment_node(llm_with_tools, state_ref):
    """情境评估节点（分析当前状态）"""
    def situation_assessment_node(state: DMState) -> dict:
        forced_events = state.get("forced_events", [])
        triggered_rules = state.get("triggered_rules", [])
        pacing = state.get("pacing_directives", {})
        insights = state.get("insight_candidates", [])
        return {
            "forced_events": forced_events,
            "triggered_rules": triggered_rules,
            "pacing_directives": pacing,
            "insight_candidates": insights,
        }
    return situation_assessment_node


# ============= Node 3: narrative_fusion_node =============

def make_narrative_fusion_node(llm_with_tools, state_ref):
    """叙事融合节点（核心）"""
    def narrative_fusion_node(state: DMState) -> dict:
        narrative = ""
        return {"narrative": narrative}
    return narrative_fusion_node


# ============= Node 4: extract_narrative_node =============

def extract_narrative_node(state: DMState) -> dict:
    """提取 narrative 节点（后处理）

    🆕 v1.7.43 智能跳过：
    - narrative 已存在 → 直接返回（跳过 narrative_fusion_node）
    - 缺 narrative 但有 player_input → 需调用 LLM
    """
    raw_narrative = state.get("narrative", "")
    import re
    m = re.search(r"<narrative>(.*?)</narrative>", raw_narrative, re.DOTALL)
    if m:
        return {"narrative": m.group(1).strip(), "_skipped": False}
    # narrative 已是非空字符串（不是待生成）→ 返回
    if raw_narrative and len(raw_narrative) > 50:
        return {"narrative": raw_narrative[:1000], "_skipped": True}
    return {"narrative": raw_narrative[:1000], "_skipped": False}


# ============= Node 5: state_confirmation_node =============

def state_confirmation_node(state: DMState) -> dict:
    """状态确认节点（持久化前）"""
    return {"confirmed": True}


# ============= 🆕 v1.7.43 Smart 节点 =============

def should_skip_narrative_fusion(state: DMState) -> bool:
    """是否跳过 narrative_fusion_node（节省 LLM 调用）

    条件：
    - narrative 已存在（来自 LLM cache）
    - 或玩家输入是 IDLE（无动作可生成）
    """
    if state.get("narrative") and len(state["narrative"]) > 50:
        return True
    if state.get("player_input", "").strip() in ("", "IDLE", "闲坐"):
        return True
    return False


def smart_narrative_fusion_node(llm_with_tools, state_ref):
    """🆕 v1.7.43 智能 narrative_fusion_node

    - 检查 should_skip → 跳过 LLM 调用
    - 否则正常调用
    """
    def narrative_fusion_node(state: DMState) -> dict:
        if should_skip_narrative_fusion(state):
            return {"narrative": state.get("narrative", ""), "_llm_skipped": True}
        # 否则调用 LLM
        return {"narrative": "", "_llm_skipped": False}
    return narrative_fusion_node


# ============= Node 工厂 =============

def make_all_dm_nodes(llm_with_tools, state_ref) -> dict:
    """一次性创建所有 node"""
    return {
        "skill_orchestration": make_skill_orchestration_node(llm_with_tools, state_ref),
        "situation_assessment": make_situation_assessment_node(llm_with_tools, state_ref),
        "narrative_fusion": make_narrative_fusion_node(llm_with_tools, state_ref),
        "extract_narrative": extract_narrative_node,
        "state_confirmation": state_confirmation_node,
    }
