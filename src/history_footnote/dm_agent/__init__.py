"""🆕 v1.7.30 dm_agent 子包

历史背景：
- 之前 dm_agent.py 是单文件 1434 行
- v1.7.30 拆为子包（state.py / tools.py / nodes/* / agent.py）

100% 向后兼容：从 history_footnote.dm_agent import 仍可访问所有公开符号
（DMAgent、DMState、make_tools、make_dm_nodes、extract_narrative_node、
state_confirmation_node）

子模块索引：
- state.py — LangGraph StateGraph state 类型（DMState）
- tools.py — make_tools 工厂（10 个 LangChain Tool）
- nodes/factory.py — make_dm_nodes（嵌套 4 节点：skill_orchestration/situation_assessment/narrative_fusion/extract_inner）
- nodes/extract.py — extract_narrative_node + state_confirmation_node（顶层节点）
- agent.py — DMAgent 类（__init__ + _build_graph + _build_system_prompt + run + regenerate + mock helpers）
"""
from __future__ import annotations

# 公开符号 re-export（保持 100% 向后兼容）
from history_footnote.dm_agent.state import DMState
from history_footnote.dm_agent.tools import make_tools
from history_footnote.dm_agent.nodes.factory import make_dm_nodes
from history_footnote.dm_agent.nodes.extract import (
    extract_narrative_node,
    state_confirmation_node,
)
from history_footnote.dm_agent.agent import DMAgent


__all__ = [
    "DMState",
    "DMAgent",
    "make_tools",
    "make_dm_nodes",
    "extract_narrative_node",
    "state_confirmation_node",
]
