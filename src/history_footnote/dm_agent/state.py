"""🆕 v1.7.30 dm_agent/DMState TypedDict (LangGraph state)

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

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class DMState(TypedDict):
    """DM Agent的StateGraph状态"""

    # === 对话历史（LangGraph MessagesState模式） ===
    messages: Annotated[list[BaseMessage], add_messages]

    # === 输入 ===
    player_input: str
    era_id: str

    # === 阶段1产出（规则引擎预计算 + Tool调用结果） ===
    view_state: dict  # GameStateView的dict形式
    forced_events: list[dict]  # ForcedEvent列表
    triggered_rules: list[dict]  # TriggeredRule列表
    pacing_directives: list[dict]  # PacingDirective列表
    insight_candidates: list[dict]  # InsightCandidate列表
    recent_events: list[dict]  # 多路召回的事件
    related_knowledge: list[dict]  # query_knowledge结果

    # === 阶段2产出（DM生成的叙事） ===
    narrative: str
    state_changes: dict
    events_to_save: list[str]
    updates: dict | None

    # === 阶段3产出（应用结果） ===
    applied_changes: dict  # apply_changes的返回值
    validation_passed: bool
