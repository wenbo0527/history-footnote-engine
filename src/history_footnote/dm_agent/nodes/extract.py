"""🆕 v1.7.30 dm_agent/extract_narrative_node + state_confirmation_node

历史背景：从 src/history_footnote/dm_agent.py（v1.7.29 1434 行）拆出。
本模块是 v1.7.30 P1-⑤ "拆 dm_agent.py 为 agent 包" 的具体执行。

v1.7.30 拆分原则：
- 拆分后行为 100% 与拆分前一致（黄金快照验证，见 scripts/test_dm_agent_golden.py）
- 公开符号（DMAgent / DMState / make_tools / make_dm_nodes /
  extract_narrative_node / state_confirmation_node）从 history_footnote.dm_agent
  仍可正常 import
- 各子模块职责单一，可独立单测
"""
from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict

from history_footnote.narrative_sanitizer import (
    sanitize as _narrative_sanitize,
    strip_skill_metadata,
    extract_json_from_text as _extract_json_from_text,
)

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from history_footnote.game_state import GameState
from history_footnote.knowledge_base import KnowledgeBase
from history_footnote.rule_engine import (
    ForcedEvent, GameStateView, InsightCandidate,
    PacingDirective, RuleEngine, TriggeredRule,
)
from history_footnote.game_memory import GameMemory, GameEvent

from history_footnote.dm_agent.state import DMState


def extract_narrative_node(state: DMState) -> dict:
    """从最后一条AIMessage中提取结构化叙事

    v1.2+ DND化：LLM可能返回JSON或纯文本
    - 如果JSON：直接解析
    - 如果纯文本：fallback用state_ref的insight_candidates生成updates

    🆕 v1.6.7 架构重构：清洗逻辑下沉到 narrative_sanitizer.sanitize()
    之前 dm_agent 自己持有一份正则表，现在复用单一权威实现。
    """
    narrative_data = {
        "narrative": "",
        "state_changes": {},
        "events_to_save": [],
        "updates": None,
        "is_action": True,
        "time_cost": 1,
        "intent_type": "action",
        "voice_options": [],
    }

    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            # 🆕 v1.6.7：单一权威 sanitize()（JSON 提取 + SKILL 剥离 + fallback 一站完成）
            narrative_data["narrative"] = _narrative_sanitize(msg.content)
            break

    # v1.2+ Fallback：LLM没返回JSON时，从state_ref.insight_candidates生成updates
    if narrative_data.get("updates") is None:
        insight_candidates = state.get("insight_candidates", [])
        if insight_candidates:
            fallback_updates = {}
            for ic in insight_candidates:
                if isinstance(ic, dict):
                    ic_id = ic.get("id")
                    confirm_needed = ic.get("confirm_needed", True)
                else:
                    ic_id = getattr(ic, "id", None)
                    confirm_needed = getattr(ic, "confirm_needed", True)
                if not ic_id:
                    continue
                fallback_updates[f"insight:{ic_id}"] = "unlocked"
            narrative_data["updates"] = fallback_updates

    return {
        "narrative": narrative_data.get("narrative", ""),
        "state_changes": narrative_data.get("state_changes", {}),
        "events_to_save": narrative_data.get("events_to_save", []),
        "updates": narrative_data.get("updates"),
        "is_action": narrative_data.get("is_action", True),
        "time_cost": int(narrative_data.get("time_cost", 1)),
        "intent_type": narrative_data.get("intent_type", "action"),
        "voice_options": narrative_data.get("voice_options", []),
        "validation_passed": True,
    }


def state_confirmation_node(state: DMState) -> dict:
    """阶段3：状态确认（合并到 extract_narrative_node 里）"""
    return {"validation_passed": True}