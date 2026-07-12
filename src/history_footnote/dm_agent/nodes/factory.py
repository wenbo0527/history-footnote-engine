"""🆕 v1.7.30 dm_agent/make_dm_nodes 工厂（嵌套 4 节点）

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
# 🆕 v2.10.1 fix: import extract_narrative_node（factory.py:291 调用，但未 import）
from history_footnote.dm_agent.nodes.extract import extract_narrative_node


def make_dm_nodes(llm_with_tools, state_ref):
    """构造DM Agent的节点函数（闭包形式，绑定LLM和state_ref）"""

    def skill_orchestration_node(state: DMState) -> dict:
        """v1.4.0 阶段0：DM 8 大公共 SKILL 编排

        在调用 LLM 之前，跑完 8 个 SKILL：
        - SKILL-1 读场判断
        - SKILL-2 节奏控制（4 种时间模式）
        - SKILL-3 线索投放（4 种线索类型）
        - SKILL-4 史实锚定
        - SKILL-5 价值观发声
        - SKILL-6 失败叙事化
        - SKILL-7 三层裁判
        - SKILL-8 认知框架锁定

        结果注入到 state_ref 和 system prompt。
        """
        from history_footnote.dm_skills import run_all_skills, run_dm_skills

        # 获取当前 player_input
        player_input = ""
        for msg in reversed(state["messages"]):
            if msg.__class__.__name__ == "HumanMessage":
                player_input = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        # 构造 state dict 给 skill
        skill_state = {
            "round_number": state_ref.get("round_number", 1),
            "action_points_current": state_ref.get("action_points_current", 3),
            "current_scene": state_ref.get("current_scene", ""),
            "variables": state_ref.get("variables", {}),
            "unlocked_insights": state_ref.get("unlocked_insights", []),
            "value_shifts": state_ref.get("value_shifts", {}),
            "selected_identity": state_ref.get("selected_identity", ""),
            "triggered_events": state_ref.get("triggered_events", []),
            "route_tendency": state_ref.get("route_tendency", ""),
        }
        era_config = state_ref.get("era_config", {})
        recent_scenes = state_ref.get("recent_scenes", [])
        recent_inputs = state_ref.get("recent_inputs", [])
        idle_rounds = state_ref.get("idle_rounds", 0)
        failure_type = state_ref.get("failure_type", "")

        # 🐛 Issue #6 修复：跑一次（去重）
        try:
            ctx = run_all_skills(
                player_input, skill_state, era_config, recent_scenes, recent_inputs, idle_rounds, failure_type
            )
            # 从 ctx 转成 v1.3 兼容 dict
            from dataclasses import asdict
            ctx_dict = {
                "pacing": {
                    "pacing": ctx.pacing.time_mode,
                    "detail_level": ctx.pacing.detail_level,
                    "rationale": ctx.pacing.rationale,
                    "should_linger": ctx.pacing.time_mode == "slow_time",
                    "player_engagement": {"high": 0.9, "normal": 0.6, "low": 0.3, "stuck": 0.2}.get(ctx.scene.engagement, 0.5),
                },
                "action": {
                    "is_action": not any(kw in player_input for kw in ["看看", "听听", "问"]),
                    "time_cost": 1,
                    "exhaustion": "none",
                    "rationale": "v1.4 from run_all_skills",
                },
                "scene": {
                    "scene": "已分类" if ctx.scene.route_tendency else "未分类",
                    "matched_keywords": [],
                    "is_new_scene": False,
                    "should_linger": ctx.pacing.time_mode == "slow_time",
                    "suggested_pacing": ctx.pacing.time_mode,
                },
                "active_voices": [asdict(v) for v in ctx.voices],
                "voices_prompt": "\n".join([v.expression for v in ctx.voices]),
                "skill_directive": ctx.skill_directive,
            }
            skills_result = ctx_dict
        except Exception as e:
            # 兼容：v1.3 旧接口
            import traceback
            print(f"[WARN] run_all_skills failed: {e}, fallback to v1.3")
            skills_result = run_dm_skills(player_input, skill_state, era_config, recent_scenes)

        # 🆕 v1.6.2 P1 B1 优化：SKILL 选择性注入（按 intent_type 预检测）
        # 简化预检测（详细检测在 narrative_fusion 之后）
        intent_type_pre = "action"
        if any(kw in player_input for kw in ["我叫", "我是", "我在", "我家", "描述", "其实", "我是从", "我从"]):
            intent_type_pre = "describe"
        elif player_input.strip().endswith(("？", "?", "吗")):
            intent_type_pre = "inquire"

        from history_footnote.skill_selector import select_skills, filter_skill_directive
        selected_skills = select_skills(intent_type_pre, state=skill_state)
        full_directive = skills_result["skill_directive"]
        filtered_directive = filter_skill_directive(full_directive, selected_skills)
        # 用过滤后的 directive（节省 60-75% tokens）
        skills_result["skill_directive"] = filtered_directive

        # 注入到 state_ref 供 LLM 使用
        state_ref["skill_directive"] = skills_result["skill_directive"]
        state_ref["skill_pacing"] = skills_result["pacing"]
        state_ref["skill_action"] = skills_result["action"]
        state_ref["skill_scene"] = skills_result["scene"]
        state_ref["active_voices"] = skills_result["active_voices"]
        state_ref["current_scene"] = skills_result["scene"]["scene"]
        state_ref["_selected_skills"] = selected_skills
        state_ref["_intent_type_pre"] = intent_type_pre
        recent_scenes.append(skills_result["scene"]["scene"])
        state_ref["recent_scenes"] = recent_scenes[-10:]

        # 记录最近 inputs
        recent_inputs.append(player_input)
        state_ref["recent_inputs"] = recent_inputs[-5:]

        # 🐛 Issue #9 修复：同步 v1.4.0 字段到 GameState（持久化）
        # 注意：skill_orchestration_node 是 nested function，不能直接访问 self.state
        # 但 state_ref 已经在 run() 中被填充了 GameState 字段
        # 这里再把更新写回 state_ref 即可
        # 真正的 GameState 同步由 run() 完成（或者在 game_loop._run_round 中）
        if state_ref.get("recent_scenes") is not None:
            state_ref["recent_scenes"] = state_ref["recent_scenes"]
        if state_ref.get("route_tendency") is not None:
            state_ref["route_tendency"] = state_ref.get("route_tendency", "")

        # 动态注入 skill_directive 到 system prompt
        from langchain_core.messages import SystemMessage
        for i, msg in enumerate(state["messages"]):
            if isinstance(msg, SystemMessage):
                # 🆕 v1.6+ KV 缓存：msg.content 是 list（带 cache_control 的结构）
                # 需要保留 cache_control，只更新 text 部分
                if isinstance(msg.content, list):
                    # 找到第一个 text block 并追加 skill_directive
                    for j, block in enumerate(msg.content):
                        if isinstance(block, dict) and block.get("type") == "text":
                            new_block = dict(block)
                            new_block["text"] = block["text"] + "\n\n" + skills_result["skill_directive"]
                            msg.content[j] = new_block
                            break
                else:
                    # 旧版 content 是 str
                    new_content = msg.content + "\n\n" + skills_result["skill_directive"]
                    state["messages"][i] = SystemMessage(content=new_content)
                break

        return {"messages": state["messages"]}

    def situation_assessment_node(state: DMState) -> dict:
        """阶段1：态势评估

        DM调用LLM，让LLM自主决定调哪些Tool。
        LLM会返回一个带tool_calls的AIMessage，LangGraph会自动路由到ToolNode。
        """
        # 每次调用前更新 llm._state_ref_slot_ref[0]（防止 model_copy 后丢失）
        if hasattr(llm_with_tools, "_state_ref_slot_ref"):
            llm_with_tools._state_ref_slot_ref[0] = state_ref
        # 调用LLM（绑定tools的版本）
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: DMState) -> str:
        """判断是否继续Tool Calling循环"""
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "call_tools"
        return "narrative_fusion"

    def narrative_fusion_node(state: DMState) -> dict:
        """阶段2：叙事生成

        阶段1的所有Tool已经执行完毕（ToolMessage在messages里）。
        再次调用LLM，让DM融合所有Tool结果生成最终叙事。
        """
        # 同样更新 state_ref
        if hasattr(llm_with_tools, "_state_ref_slot_ref"):
            llm_with_tools._state_ref_slot_ref[0] = state_ref
        # 把narrative_snippets从ToolMessage抽取到state_ref
        # 这样Mock LLM第二轮能读到
        snippets = []
        for msg in state["messages"]:
            # ToolMessage的content是字符串（JSON）
            if msg.__class__.__name__ == "ToolMessage":
                # 检查name属性（只处理query_narrative_snippets的ToolMessage）
                msg_name = getattr(msg, "name", "")
                if "narrative_snippets" not in msg_name:
                    continue
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                try:
                    data = json.loads(content)
                    # ToolMessage的content是JSON list of dict
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "snippet_text" in item:
                                snippets.append(item)
                    elif isinstance(data, dict) and "snippet_text" in data:
                        snippets.append(data)
                except json.JSONDecodeError:
                    pass

        if snippets:
            state_ref["available_snippets"] = snippets

        # 抽取story_segments（DM可能调get_random_segment或query_story_segments）
        story_segments = []
        for msg in state["messages"]:
            if msg.__class__.__name__ == "ToolMessage":
                msg_name = getattr(msg, "name", "")
                if "story_segment" in msg_name or "random_segment" in msg_name:
                    try:
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        data = json.loads(content)
                        if isinstance(data, dict) and data.get("found"):
                            story_segments.append(data)
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and "text" in item:
                                    story_segments.append(item)
                    except (json.JSONDecodeError, TypeError):
                        pass
        if story_segments:
            state_ref["available_story_segments"] = story_segments

        # 抽取identity_offer（DM可能在Tool调用中发起身份切换offer）
        offer = None
        for msg in state["messages"]:
            if msg.__class__.__name__ == "ToolMessage":
                msg_name = getattr(msg, "name", "")
                if "offer_identity" in msg_name or "identity_switch" in msg_name:
                    try:
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        data = json.loads(content)
                        if isinstance(data, dict) and data.get("offered"):
                            offer = data
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass
        if offer:
            state_ref["identity_offer"] = offer

        # 第二次LLM调用，生成最终叙事
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # 🆕 v1.7.6 修复：第 5 个嵌套节点（extract_narrative_node）
    # 之前 extract_narrative_node 在顶层定义（line 715），但 make_dm_nodes 调用方
    # 期望从闭包内拿到 5 个节点。修复：在 make_dm_nodes 内增加一个闭包版。
    def extract_narrative_node_inner(state: DMState) -> dict:
        """闭包版 extract_narrative_node（绑定 state_ref）

        复用顶层 extract_narrative_node 实现
        """
        return extract_narrative_node(state)

    # 🆕 v1.7.6 修复：返回 5 个节点元组
    # 之前 make_dm_nodes 没有 return → 返回 None → cannot unpack
    return (
        skill_orchestration_node,
        situation_assessment_node,
        should_continue,
        narrative_fusion_node,
        extract_narrative_node_inner,
    )

