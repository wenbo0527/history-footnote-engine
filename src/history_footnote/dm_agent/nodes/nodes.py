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
    """提取 narrative 节点（后处理）"""
    raw_narrative = state.get("narrative", "")
    import re
    m = re.search(r"<narrative>(.*?)</narrative>", raw_narrative, re.DOTALL)
    if m:
        return {"narrative": m.group(1).strip()}
    return {"narrative": raw_narrative[:1000]}


# ============= Node 5: state_confirmation_node =============

def state_confirmation_node(state: DMState) -> dict:
    """状态确认节点（持久化前）"""
    return {"confirmed": True}


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
