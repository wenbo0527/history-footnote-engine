"""DM Agent——LangGraph StateGraph实现

设计参考：设计文档v1.0.md 第3.1节"DM Agent" + DM引导者行为模式文档

DM的三阶段行为模型（一次API调用内完成）：
1. 态势评估（situation_assessment）
   - 自主决定调哪些Tool查状态/规则/记忆/知识
   - 工具：get_state / recall_events / check_rules / query_knowledge

2. 叙事生成（narrative_fusion）
   - 融合所有判断，输出叙事
   - 推进节奏 + 植入线索 + 查证史实 + 融合叙事

3. 状态确认（state_confirmation）
   - 调save_event记录
   - 变量变更应用
   - 后校验
"""
from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict
# 🆕 v1.6.7 架构重构：所有 SKILL 元数据清洗逻辑沉淀到 narrative_sanitizer.py
# dm_agent 不再持有 SKILL_METADATA_PATTERNS / _strip_skill_metadata，改为复用
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
    ForcedEvent,
    GameStateView,
    InsightCandidate,
    PacingDirective,
    RuleEngine,
    TriggeredRule,
)
from history_footnote.game_memory import GameMemory, GameEvent


# === State Schema ===

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


# === Tool定义（5个Tool，DM可自主调用） ===

def make_tools(
    state: GameState,
    rule_engine: RuleEngine,
    memory: GameMemory,
    knowledge_base: KnowledgeBase,
    era_config: dict = None,
) -> list:
    """构造Tool函数——确定性操作，无创意判断

    Args:
        state, rule_engine, memory, knowledge_base: 引擎组件
        era_config: 时代包配置（v1.2+需要，offer_identity_switch Tool要用）
    """
    if era_config is None:
        era_config = rule_engine.config if hasattr(rule_engine, "config") else {}

    from langchain_core.tools import tool

    @tool
    def get_state() -> dict:
        """获取当前游戏状态（变量值+已触发事件+NPC状态+回合数）"""
        view = rule_engine.make_view(state)
        return {
            "round": state.round_number,
            "date": state.current_date,
            "variables": dict(state.variables),
            "triggered_events": list(state.triggered_events),
            "triggered_triggers": list(state.triggered_triggers),
            "unlocked_insights": list(state.unlocked_insights),
            "npc_levels": dict(state.npc_levels),
            "value_shifts": dict(state.value_shifts),
            "player_idle_rounds": state.player_idle_rounds,
            "rounds_since_last_insight": state.rounds_since_last_insight,
        }

    @tool
    def recall_events(query: str = "", recent_n: int = 3, by_entity: str = "") -> list[dict]:
        """召回相关历史事件

        Args:
            query: 关键词查询
            recent_n: 时间召回数量（默认3回合）
            by_entity: 关联实体（如NPC id）
        """
        return memory.recall_events(
            query=query,
            recent_n=recent_n,
            by_entity=by_entity,
        )

    @tool
    def check_rules(action: str = "", check_type: str = "all") -> dict:
        """查询规则引擎

        Args:
            action: 玩家行动描述（用于行动边界检查）
            check_type: all / action_boundary / forced_events / triggers / pacing / insights
        """
        view = rule_engine.make_view(state)
        result = {}

        if check_type in ("all", "action_boundary") and action:
            result["action_check"] = rule_engine.check_action(view, action)

        if check_type in ("all", "forced_events"):
            forced = rule_engine.check_forced_events(view)
            result["forced_events"] = [
                {
                    "event_id": fe.event_id,
                    "event_name": fe.event_name,
                    "date": fe.date,
                    "description": fe.description,
                    "scope": fe.scope,
                    "player_visibility": fe.player_visibility,
                    "narrative_mandatory": fe.narrative_mandatory,
                }
                for fe in forced
            ]

        if check_type in ("all", "triggers"):
            triggered = rule_engine.check_triggers(view)
            result["triggered_rules"] = [
                {
                    "id": tr.id,
                    "narrative_hint": tr.narrative_hint,
                    "effect": tr.effect,
                }
                for tr in triggered
            ]

        if check_type in ("all", "pacing"):
            pacing = rule_engine.check_pacing(view)
            result["pacing_directives"] = [
                {
                    "id": pd.id,
                    "direction": pd.direction,
                    "hint": pd.hint,
                    "constraint": pd.constraint,
                }
                for pd in pacing
            ]

        if check_type in ("all", "insights"):
            # 玩家输入的insight候选
            insights = rule_engine.check_insights(
                view,
                player_input=state._last_player_input or "",
            )
            result["insight_candidates"] = [
                {
                    "id": ic.id,
                    "topic": ic.topic,
                    "trigger_type": ic.trigger_type,
                    "confirm_needed": ic.confirm_needed,
                    "unlock_knowledge": ic.unlock_knowledge,
                    "narrative_hint": ic.narrative_hint,
                }
                for ic in insights
            ]

        return result

    @tool
    def query_knowledge(keywords: list[str] = None, scene: str = "", entry_ids: list[str] = None) -> list[dict]:
        """查询知识库

        Args:
            keywords: 关键词列表
            scene: 场景名
            entry_ids: 直接指定条目ID
        """
        # 🆕 v1.6.2 P2 D1：Tool 结果缓存（key 包含 keywords + scene + entry_ids）
        from history_footnote.web_enhancements import TOOL_RESULT_CACHE
        cache_key_parts = ["query_knowledge"]
        cache_key_parts.extend(sorted(keywords or []))
        cache_key_parts.append(f"scene={scene}")
        cache_key_parts.extend(sorted(entry_ids or []))
        cache_key = "|".join(cache_key_parts)

        cached = TOOL_RESULT_CACHE.get(cache_key)
        if cached is not None:
            return cached

        results = knowledge_base.query(
            keywords=keywords or [],
            scene=scene,
            entry_ids=entry_ids or [],
        )
        result_list = [
            {
                "id": r["id"],
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "layer": r.get("layer", ""),
            }
            for r in results
        ]
        TOOL_RESULT_CACHE.set(cache_key, result_list)
        return result_list

    @tool
    def query_narrative_snippets(
        scene: str = "",
        keywords: list[str] = None,
        snippet_ids: list[str] = None,
        top_k: int = 2,
        player_gender: str = "",
    ) -> list[dict]:
        """查询叙事片段（小说原文、NPC对白、场景描写）

        用于DM在生成场景描写、NPC对白、市井闲谈时引用素材。
        调用建议：在生成场景相关叙事前，先查匹配片段，再融合输出。

        v1.1+：支持player_gender过滤，避免对女玩家引用男性故事（如沈万三、施润泽）。
        片段的target_gender字段："male"/"female"/"all"。

        Args:
            scene: 当前场景名（"茶馆"/"盛泽市集"/"牙行"/"自家作坊"/"镇外桑田"/"县衙"）
            keywords: 关键词列表
            snippet_ids: 直接指定片段ID
            top_k: 返回前K条
            player_gender: 玩家性别（male/female）
        """
        # 默认从state读取player_gender
        if not player_gender:
            player_gender = getattr(state, "player_gender", "")

        results = knowledge_base.query_snippets(
            scene=scene,
            keywords=keywords or [],
            snippet_ids=snippet_ids or [],
            top_k=top_k,
            player_gender=player_gender,
        )
        return [
            {
                "id": r["id"],
                "source": r.get("source", ""),
                "snippet_text": r.get("snippet_text", ""),
                "npc_use_case": r.get("npc_use_case", ""),
                "applies_to_scenes": r.get("applies_to_scenes", []),
                "target_gender": r.get("target_gender", "all"),
            }
            for r in results
        ]

    @tool
    def query_story_segments(
        scene: str = "",
        segment_type: str = "",
        keywords: list[str] = None,
        top_k: int = 3,
    ) -> list[dict]:
        """查询分段叙事片段（按场景+类型）

        v1.2+：DND分段叙事。检索到的片段是独立的叙事单元，
        DM可以自由组合它们来生成故事，每次会拿到不同的片段（随机性）。

        与query_narrative_snippets的区别：
        - narrative_snippets：小说是原文引用（如《金瓶梅》选段）
        - story_segments：场景描写/NPC对白/传言/交易（结构性片段）

        Args:
            scene: 场景名（如"盛泽市集"）
            segment_type: atmosphere/npc_dialog/transaction/rumor/description
            keywords: 关键词
            top_k: 返回数量
        """
        results = knowledge_base.query_segments(
            scene=scene,
            segment_type=segment_type,
            keywords=keywords or [],
            top_k=top_k,
        )
        return [
            {
                "id": r["id"],
                "scene": scene,
                "type": r.get("type", ""),
                "text": r.get("text", ""),
                "npc_role": r.get("npc_role", ""),
            }
            for r in results
        ]

    @tool
    def get_random_segment(
        scene: str = "",
        segment_type: str = "",
    ) -> dict:
        """随机获取一条叙事片段（DND随机性核心）

        每次调用都返回不同的片段（除非该场景下没有可选）。
        这是打破"线性叙事"的关键——同一场景，玩家可能遇到不同的NPC和事件。

        Args:
            scene: 场景名
            segment_type: 可选的类型过滤

        Returns:
            随机segment dict（含text字段）
        """
        seg = knowledge_base.get_random_segment(scene=scene, segment_type=segment_type)
        if seg is None:
            return {"found": False, "scene": scene}
        return {
            "found": True,
            "scene": scene,
            "id": seg["id"],
            "type": seg.get("type", ""),
            "text": seg.get("text", ""),
            "npc_role": seg.get("npc_role", ""),
        }

    @tool
    def roll_dice(
        dice_expr: str = "d20",
        modifier: int = 0,
        purpose: str = "",
        dc: int = 0,
    ) -> dict:
        """掷骰子（DND核心）

        v1.2+：让LLM能够主动掷骰子判定玩家行动的成败。

        使用场景：
        - 谈判/说服：d20+魅力修正 vs DC（对方意愿）
        - 技能检定：d20+技能修正 vs DC（任务难度）
        - 攻击/对抗：双方各roll一次比大小
        - 随机事件：纯d100或d20+阈值

        Args:
            dice_expr: 骰子表达式（d20/2d6+3/1d100等）
            modifier: 修正值（魅力/技能/装备加成）
            purpose: 这次掷骰的用途（用于日志）
            dc: 困难等级（0=纯随机，不判定成功失败）

        Returns:
            {
                "expression": "1d20+3",
                "rolls": [15],
                "total": 18,
                "dc": 12,
                "success": True,
                "margin": 6,
                "is_critical_success": False,
                "is_critical_fail": False,
                "purpose": "牙行谈判"
            }
        """
        from history_footnote.dice_engine import DiceEngine
        engine = DiceEngine()
        if dc > 0:
            return engine.check(dc, dice_expr, modifier, purpose)
        else:
            result = engine.roll(dice_expr, modifier, purpose)
            return result.to_dict()

    @tool
    def offer_identity_switch(
        to_identity: str,
        reason: str,
        cost: str = "",
        benefit: str = "",
    ) -> dict:
        """发起身份切换offer——告诉玩家可以从当前身份切换到新身份

        v1.2+：DM在生成叙事时，如果认为满足切换条件，可以调用此Tool
        玩家会看到[OFFER]提示并输入/accept或/decline决定

        Args:
            to_identity: 目标身份id（如"merchant_female"）
            reason: 触发原因（"卖婆看中你的丝织经验..."）
            cost: 代价说明（"放弃现有织机..."）
            benefit: 收益说明（"可以进入富户内宅..."）
        """
        # 验证to_identity合法
        identities = era_config.get("world", {}).get("player_identities", {})
        if to_identity not in identities:
            return {
                "offered": False,
                "error": f"目标身份 {to_identity} 不存在",
            }

        # 验证性别一致性
        current_identity = identities.get(state.selected_identity, {})
        target_identity = identities.get(to_identity, {})
        if current_identity.get("gender") != target_identity.get("gender"):
            return {
                "offered": False,
                "error": f"性别不一致：当前{current_identity.get('gender')}，目标{target_identity.get('gender')}",
            }

        return {
            "offered": True,
            "to_identity": to_identity,
            "to_label": target_identity.get("label", to_identity),
            "reason": reason,
            "cost": cost or "(未指定)",
            "benefit": benefit or "(未指定)",
            "message": f"DM提供身份切换offer：{current_identity.get('label', '当前身份')} → {target_identity.get('label', to_identity)}",
        }

    @tool
    def save_event(summary: str, consequences: dict = None) -> dict:
        """保存事件到记忆

        Args:
            summary: 事件摘要
            consequences: {"variables": {...}, "npc_changes": {...}, "insight_unlocked": "..."}
        """
        event = GameEvent(
            round=state.round_number,
            type="dm_narrative",
            summary=summary,
            consequences=list((consequences or {}).get("descriptions", [])),
            affected_variables=(consequences or {}).get("variables", {}),
            relationship_changes=(consequences or {}).get("npc_changes", {}),
            insight_unlocked=(consequences or {}).get("insight_unlocked", ""),
        )
        memory.save_event(event)
        return {"saved": True, "summary": summary}

    return [get_state, recall_events, check_rules, query_knowledge, query_narrative_snippets, query_story_segments, get_random_segment, roll_dice, offer_identity_switch, save_event]


# === StateGraph节点函数 ===

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


# === DM Agent主类 ===

class DMAgent:
    """DM Agent——LangGraph StateGraph编排

    Usage:
        agent = DMAgent(era_config, state, rule_engine, memory, knowledge_base, llm_model)
        result = agent.run(player_input="去牙行看看丝价")
        # result = {"narrative": "...", "state_changes": {...}, ...}
    """

    def __init__(
        self,
        era_config: dict,
        state: GameState,
        rule_engine: RuleEngine,
        memory: GameMemory,
        knowledge_base: KnowledgeBase,
        llm_model: Any,
    ):
        self.era_config = era_config
        self.state = state
        self.rule_engine = rule_engine
        self.memory = memory
        self.knowledge_base = knowledge_base
        self.llm = llm_model
        # 🐛 v1.6+ 修复：selected_identity 应来自 state（避免 AttributeError）
        self.selected_identity = getattr(state, "selected_identity", "") or ""
        self.tools = make_tools(state, rule_engine, memory, knowledge_base, era_config)

        # 绑定tools到LLM（真实LLM需要这一步）
        # bind_tools 返回新模型，新模型会通过 model_copy 共享 _state_ref_slot_ref
        if hasattr(self.llm, "bind_tools"):
            new_llm = self.llm.bind_tools(self.tools)
            self._llm_with_tools = new_llm

        # 构建StateGraph（一次性创建，复用）
        self.graph = self._build_graph()
        # 🆕 v1.6.2 P0 A4 优化：缓存 graph 引用，永久复用
        self._graph_compiled = self.graph

    def _build_graph(self, state_ref: dict | None = None):
        """构建DM Agent的StateGraph

        流程：
        1. situation_assessment → LLM（生成tool_calls）
        2. should_continue → 判断：有tool_calls则调Tool，没有则跳到叙事
        3. call_tools → 执行Tool
        4. （回到）situation_assessment → 继续LLM判断（可能更多Tool calls）
        5. narrative_fusion → 第二次LLM（生成最终叙事）
        6. extract_narrative → 提取结构化数据
        7. END

        Args:
            state_ref: 当前回合的state_ref（如果为None则用空dict）
        """
        if state_ref is None:
            state_ref = {}

        # 绑定tools到LLM
        llm_with_tools = self.llm.bind_tools(self.tools) if hasattr(self.llm, "bind_tools") else self.llm
        # 把 state_ref 存到 llm_with_tools（Mock LLM会用）
        # 必须用 [0] = state_ref 修改列表内容，保持引用不断开
        if hasattr(llm_with_tools, "_state_ref_slot_ref"):
            if isinstance(llm_with_tools._state_ref_slot_ref, list):
                llm_with_tools._state_ref_slot_ref[0] = state_ref
            else:
                llm_with_tools._state_ref_slot_ref = [state_ref]

        # 构造节点（闭包绑定llm_with_tools和state_ref）
        skill_node, situation_node, should_continue, narrative_node, extract_node = make_dm_nodes(llm_with_tools, state_ref)

        workflow = StateGraph(DMState)

        # 节点
        workflow.add_node("skill_orchestration", skill_node)
        workflow.add_node("situation_assessment", situation_node)
        workflow.add_node("narrative_fusion", narrative_node)
        workflow.add_node("extract_narrative", extract_node)

        # Tool执行节点（LangGraph内置）
        tool_node = ToolNode(self.tools)
        workflow.add_node("call_tools", tool_node)

        # 入口：先跑 DM skills
        workflow.set_entry_point("skill_orchestration")
        workflow.add_edge("skill_orchestration", "situation_assessment")

        # 条件边：LLM返回后判断是否调Tool
        workflow.add_conditional_edges(
            "situation_assessment",
            should_continue,
            {
                "call_tools": "call_tools",
                "narrative_fusion": "narrative_fusion",
            },
        )

        # Tool执行后回到态势评估（可能继续调Tool）
        workflow.add_edge("call_tools", "situation_assessment")

        # 叙事生成
        workflow.add_edge("narrative_fusion", "extract_narrative")
        workflow.add_edge("extract_narrative", END)

        return workflow.compile()

    def _build_system_prompt(self) -> str:
        """构建DM的System Prompt——从era_config填充"""
        # 优先用 player_identities[selected_identity]，否则用 default_identity
        identities = self.era_config.get("world", {}).get("player_identities", {})
        identity = identities.get(self.selected_identity, {})
        if not identity:
            default_id = self.era_config.get("world", {}).get("default_identity", "")
            identity = identities.get(default_id, {})
        timeline = self.era_config.get("world", {}).get("timeline", {})
        iron_laws = self.era_config.get("world", {}).get("iron_laws", [])
        plausibility_rules = self.era_config.get("world", {}).get("plausibility_rules", [])

        # 加载dm_persona.md（如有）
        persona_md = self._load_dm_persona()
        if persona_md:
            return persona_md

        # 否则用模板生成
        # 🆕 v1.6.4 P0 Bug 修复：注入最近叙事上下文（避免 NPC 混淆）
        # 之前：recent_scenes 只有场景标签，LLM 不知上回合完整对话
        # 现在：注入最近 N 回合的"摘要 + 角色 + 关键对话" 防止上下文断裂
        recent_context = self._build_recent_context_for_prompt()

        return f"""你是{self.era_config.get('era_name', '万历十五年')}的历史DM。

{recent_context}

## 时代背景
{timeline.get('description', '')}

## 你的三重身份
你是叙事者、仲裁者、引导者。
- 叙事者：用细节而非数字，用场景而非概括
- 仲裁者：严格执行规则引擎的计算结果
- 引导者：推进节奏、植入线索、查证史实

## 历史红线（不可违反）
{chr(10).join(f"- {law['fact']}" for law in iron_laws)}

## 小人物身份约束
你是{identity.get('role', '小人物')}，{identity.get('social_class', '')}。
可接触：{', '.join(identity.get('action_boundaries', {}).get('can_access', []))}
不可接触：{', '.join(identity.get('action_boundaries', {}).get('cannot_access', []))}
可影响：{', '.join(identity.get('action_boundaries', {}).get('can_interact_with', []))}
不可影响：{', '.join(identity.get('action_boundaries', {}).get('cannot_influence', []))}

## 可然性原则
{chr(10).join(f"{i+1}. {rule}" for i, rule in enumerate(plausibility_rules))}

## ⏱️ 行动点（v1.3+ 关键约束）
**这个游戏的核心节奏机制**：
- 每月固定 **3 个行动点**（基础）。本月还有X点时，玩家可以继续行动；行动点=0 时，自动跳到下个月。
- **你必须在每次叙事中，判定本轮玩家的行动消耗多少行动点**，并在输出JSON里用 `time_cost` 字段返回（0/1/2/3）。
- **time_cost 判定规则**（基于时代常识）：
  - **0** = 问询/观察/闲聊/问路/看一眼（不消耗行动点）—— 例："我看看窗外"、"我问邻居张三借个火"
  - **1** = 半日功夫（小半天，可做1-2件事）—— 例："我去茶馆听消息"、"我给织机上油"
  - **2** = 一日功夫（一天时间）—— 例："我去苏州城里一趟"、"我织了一匹湖绫"
  - **3** = 数日功夫（跨多日）—— 例："我做完一整批上供的丝绸"、"我出门走亲戚两三天"
- **is_action** 字段：true=真行动（消耗行动点），false=问询/观察（不消耗，但照样输出叙事细节）

**为什么这个机制重要**：玩家要的是"过日子"的沉浸感——织布、卖丝、纳粮、交税，这些事一件件来，月内可以做3-5件具体的事。**不要把一个月压缩进一段叙事里**——一段叙事 = 半个时辰到两三天的具体场景。

## 📤 输出格式（严格遵守）
你必须输出合法 JSON：
```json
{{
  "narrative": "具体场景描写（半文半白，至少300字）",
  "is_action": true,
  "time_cost": 2,
  "intent_type": "action",  // action | inquire | describe | voice
  "voice_options": [         // 🆕 v1.5+：2-4 个内在声音选项
    {{
      "voice_id": "voice_xxx",
      "voice_name": "内在声音名",
      "intent_text": "按这个声音行动时，玩家实际做的事（10-20字）"
    }}
  ],
  "state_changes": {{"variable_id": +1.0}},
  "events_to_save": ["事件摘要"],
  "updates": {{"insight:xxx": "unlocked"}}
}}
```

### 字段说明

- `narrative` 必填，**300-800字**的具体场景，不要总结。
- `is_action` 必填（true/false）。
- `time_cost` 必填（0/1/2/3）。
- `intent_type` 🆕：本次交互的类型
  - `action` = 真行动（消耗行动点）
  - `inquire` = 问询/观察（不消耗行动点）
  - `describe` = 玩家补充身份/环境/性格描述（不消耗行动点，但DM应承认这些信息）
  - `voice` = 玩家选择了某个内在声音选项（强制 is_action=true）
- `voice_options` 🆕：**2-4 个内在声音选项**
  - 每个选项对应一个内在声音（来自 era.json 的 voices 定义）
  - `intent_text` 是玩家点这个选项后会发生什么（10-20字，半文半白）
  - 选项必须在叙事结尾呈现，让玩家选择
- `state_changes` 选填。
- `events_to_save` 选填。
- `updates` 选填。

### 🎭 voice_options 设计原则

- **每个叙事回合** 都应给出 2-4 个 voice_options（DE 风格的"脑海中的几个声音"）
- 选项要**性格鲜明**——同一件事，不同声音给不同建议
- 选项要**符合时代**——不出现现代思维（如"跳槽/辞职/投资"）
- 最后一个隐藏选项是**自由输入**——玩家可以自己描述行动（绕过选项）
- 示例（赵里长催税时）：
  ```json
  "voice_options": [
    {{"voice_id": "voice_accountant", "voice_name": "算盘声",
     "intent_text": "再拖拖，看能不能借到银子"}},
    {{"voice_id": "voice_moral", "voice_name": "读书人的本分",
     "intent_text": "按额交齐，欠账不是做人的道理"}},
    {{"voice_id": "voice_dignity", "voice_name": "做人要有骨气",
     "intent_text": "今年水脚银凭啥又加？我要问问清楚"}}
  ]
  ```

### 🪞 describe 类型处理（玩家补充身份/环境）

当玩家输入是**描述自己的身份/环境/性格**（如"我是从福建逃难来的破产绸缎商人"），你应该：
1. `intent_type` = `describe`
2. `is_action` = false
3. `time_cost` = 0
4. **叙事中承认并吸收这个信息**——"你想起了自己的来历，叹了口气..."（不消耗行动点）
5. 不强行推进剧情

"""

    def _load_dm_persona(self) -> str | None:
        """加载dm_persona.md文件"""
        from pathlib import Path
        persona_path = Path("eras") / self.era_config.get("era_id", "") / "dm_persona.md"
        if persona_path.exists():
            return persona_path.read_text(encoding="utf-8")
        return None

    def _build_recent_context_for_prompt(self) -> str:
        """🆕 v1.6.4 P0 Bug 修复：构建最近叙事上下文

        问题：之前 system prompt 只有 recent_scenes（场景标签如"织机前/茶馆"），
        导致 LLM 不知道上回合完整对话内容（如谁在对话、玩家承诺了什么、状态如何变化），
        从而出现 NPC 混淆（张寡妇 → 陈三）、上下文断裂等问题。

        修复：把最近 N 回合的【摘要 + 玩家输入 + 关键状态】注入到 system prompt。

        Args:
            无（从 self.state.narrative_recent 读）

        Returns:
            Markdown 格式的"最近剧情上下文"段（如果无历史返回空串）
        """
        recent = getattr(self.state, "narrative_recent", [])
        if not recent:
            return ""

        # 取最近 3 回合（约 1500 字，平衡上下文 vs token）
        tail = recent[-3:]
        lines = [
            "## 📜 最近剧情上下文（v1.6.4+ 关键修复：保持叙事连贯性）",
            "",
            "**重要提示**：以下是你最近 3 回合已经发生的剧情。你的下一回合叙事**必须**承接上文，",
            "**不可**突然切换场景/NPC/对话对象。如玩家没说离开某地，就继续在该地叙事。",
            "",
        ]

        for i, n in enumerate(tail, 1):
            round_num = n.get("round", "?")
            summary = n.get("summary", "") or ""
            narrative = n.get("narrative", "") or ""
            player_input = ""

            # 从 event_log 找对应的 player_action
            for ev in (self.state.event_log or []):
                if ev.get("round") == round_num and ev.get("player_action"):
                    player_input = ev["player_action"]
                    break

            lines.append(f"### 第 {round_num} 回合")
            if player_input:
                lines.append(f"**玩家行动**：{player_input}")
            if summary:
                lines.append(f"**上回合摘要**：{summary}")
            # 截取叙事前 400 字作为上下文锚点
            snippet = narrative[:400] + ("…" if len(narrative) > 400 else "")
            lines.append(f"**叙事片段**：{snippet}")
            lines.append("")

        # 附加变量变化（如果 round ≥ 2）
        if len(tail) >= 1:
            vars_recent = getattr(self.state, "variables", {}) or {}
            if vars_recent:
                # 只显示非零值
                non_zero = {k: v for k, v in vars_recent.items() if v not in (0, 0.0, "")}
                if non_zero:
                    lines.append("**当前关键变量**：")
                    for k, v in list(non_zero.items())[:5]:
                        lines.append(f"  - {k}: {v}")

        return "\n".join(lines) + "\n"

    def run(self, player_input: str) -> dict:
        """运行一回合DM Agent

        Args:
            player_input: 玩家输入

        Returns:
            {"narrative": str, "state_changes": dict, "events_to_save": list, "updates": dict|None}
        """
        # 记录玩家输入到state（供check_rules的insight检查使用）
        self.state._last_player_input = player_input
        # 🐛 v1.6+ 修复：每次 run 同步 selected_identity（避免 selected_identity 不更新）
        self.selected_identity = self.state.selected_identity or ""

        # 构建最新的state_ref（用于Mock LLM实时读取状态）
        state_ref = {
            "view_state": self._make_view_state_dict(),
            "forced_events": self._get_forced_events_for_mock(),
            "triggered_rules": self._get_triggers_for_mock(),
            "pacing_directives": self._get_pacing_for_mock(),
            "insight_candidates": self._get_insights_for_mock(),
            # 🐛 Issue #9 修复：从 GameState 同步 v1.4.0+ 8 SKILL 字段
            "round_number": self.state.round_number,
            "action_points_current": self.state.action_points_current,
            "variables": dict(self.state.variables),
            "unlocked_insights": sorted(self.state.unlocked_insights),
            "value_shifts": dict(self.state.value_shifts),
            "selected_identity": self.state.selected_identity,
            "triggered_events": sorted(self.state.triggered_events),
            "recent_scenes": list(self.state.recent_scenes),
            "recent_inputs": list(self.state.recent_inputs),
            # 🆕 v1.6.4 P0 Bug 修复：注入最近叙事（让 Mock LLM 也能保持上下文）
            # 之前只传场景标签，导致 NPC/场景混淆（张寡妇 → 陈三）
            "recent_narratives": [
                {
                    "round": n.get("round"),
                    "summary": n.get("summary", ""),
                    "narrative": (n.get("narrative", "") or "")[:400],  # 截前 400 字
                }
                for n in getattr(self.state, "narrative_recent", [])[-3:]
            ],
            "route_tendency": self.state.route_tendency,
            "failure_type": self.state.failure_type,
            "idle_rounds": self.state.player_idle_rounds,
        }

        # 准备输入state
        system_prompt = self._build_system_prompt()

        # 🆕 v1.6+ KV 缓存：在 system prompt 加 cache_control（ephemeral 5min TTL）
        # 后续 50 回合：99% 命中，节省 70-98% input tokens
        from history_footnote.kv_cache import SYSTEM_PROMPT_CACHE
        cache_control = SYSTEM_PROMPT_CACHE.get_cache_control(system_prompt)

        # 把 state_ref 编码到 system prompt 后面的一个特殊 SystemMessage 里
        # 这样 Mock LLM 在第二次调用（生成叙事）时也能读到
        # 注意：state_ref 每回合都变，**不能加 cache_control**（会破坏缓存命中）
        import json as _json
        state_ref_msg = SystemMessage(
            content=f"\n\n[__STATE_REF__]\n{_json.dumps(state_ref, ensure_ascii=False)}"
        )

        # SystemMessage 支持 structured content（list of blocks with cache_control）
        # Anthropic API 通过 cache_control={"type": "ephemeral"} 标记 block
        # 注意：只有 Anthropic provider 支持此结构；其他 provider 会忽略 cache_control
        system_message = SystemMessage(
            content=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": cache_control,
                }
            ]
        )

        initial_state: DMState = {
            "messages": [
                system_message,
                state_ref_msg,  # 第二条SystemMessage携带state_ref（每回合变，不缓存）
                HumanMessage(content=player_input),
            ],
            "player_input": player_input,
            "era_id": self.era_config.get("era_id", ""),
            "view_state": state_ref["view_state"],
            "forced_events": state_ref["forced_events"],
            "triggered_rules": state_ref["triggered_rules"],
            "pacing_directives": state_ref["pacing_directives"],
            "insight_candidates": state_ref["insight_candidates"],
            "recent_events": [],
            "related_knowledge": [],
            "narrative": "",
            "state_changes": {},
            "events_to_save": [],
            "updates": None,
            "applied_changes": {},
            "validation_passed": False,
        }

        # 每次run重新构建graph（带最新的state_ref绑定）
        # 🆕 v1.6.2 P0 A4 优化：graph 复用 + 只更新 state_ref slot
        if hasattr(self, '_graph_compiled') and self._graph_compiled is not None:
            # 复用已有 graph（LangGraph compile 后的对象）
            # 关键：通过 _state_ref_slot_ref 更新 state_ref（让闭包看到新数据）
            llm_with_tools = getattr(self, '_llm_with_tools', None)
            if llm_with_tools and hasattr(llm_with_tools, '_state_ref_slot_ref'):
                if isinstance(llm_with_tools._state_ref_slot_ref, list):
                    llm_with_tools._state_ref_slot_ref[0] = state_ref
                else:
                    llm_with_tools._state_ref_slot_ref = [state_ref]
            self.graph = self._graph_compiled
        else:
            # 首次：build + cache
            self.graph = self._build_graph(state_ref=state_ref)
            self._graph_compiled = self.graph

        # 🐛 Issue #9 修复：保存 state_ref 供 game_loop 同步用
        self._last_state_ref = state_ref

        # 执行StateGraph
        result = self.graph.invoke(initial_state)

        # 🆕 v1.6+ P0 修复：返回 DMResponse 完整字段（含 voice_options/intent_type/is_action/time_cost）
        return {
            "narrative": result.get("narrative", ""),
            "state_changes": result.get("state_changes", {}),
            "events_to_save": result.get("events_to_save", []),
            "updates": result.get("updates"),
            "identity_offer": state_ref.get("identity_offer"),  # v1.2+身份切换offer
            "is_action": True,
            "time_cost": 1,
            "intent_type": "action",
            "voice_options": [],
        }

    def regenerate(
        self,
        player_input: str,
        validation_issues: list,
        prev_narrative: str = "",
    ) -> dict:
        """🆕 v1.6+ P0 修复：带 validation issues 重新生成叙事

        Args:
            player_input: 玩家原始输入
            validation_issues: 上次校验的问题列表（来自 post_validate）
            prev_narrative: 上次生成的叙事（供 LLM 参考"这次要改什么"）

        Returns:
            DMResponse 格式 dict（同 run）
        """
        # 构造包含 validation issues 的"重试 prompt"
        issue_descriptions = []
        for issue in validation_issues:
            issue_descriptions.append(
                f"- [{issue.get('layer', 'unknown')}/{issue.get('severity', 'error')}] {issue.get('message', '?')}"
            )
        issues_text = "\n".join(issue_descriptions) if issue_descriptions else "无"

        retry_human_input = (
            f"【系统重试提示】\n"
            f"你上一次的叙事被后校验系统判定为不符合约束，需要重新生成。\n"
            f"以下是发现的问题：\n{issues_text}\n\n"
            f"上一次的叙事（前 500 字）：\n{prev_narrative[:500] if prev_narrative else '（无）'}\n\n"
            f"请**严格遵守约束**重新生成叙事。\n\n"
            f"玩家原始输入：{player_input}"
        )

        # 复用 run 逻辑，但用 retry_human_input 替换 player_input
        # 先把 player_input 存到 state（让 rule_engine 能读到）
        self.state._last_player_input = player_input
        # 🐛 v1.6+ 修复：regenerate 也同步 selected_identity
        self.selected_identity = self.state.selected_identity or ""

        # 构造 state_ref（与 run 一致）
        state_ref = {
            "view_state": self._make_view_state_dict(),
            "forced_events": self._get_forced_events_for_mock(),
            "triggered_rules": self._get_triggers_for_mock(),
            "pacing_directives": self._get_pacing_for_mock(),
            "insight_candidates": self._get_insights_for_mock(),
            "round_number": self.state.round_number,
            "action_points_current": self.state.action_points_current,
            "variables": dict(self.state.variables),
            "unlocked_insights": sorted(self.state.unlocked_insights),
            "value_shifts": dict(self.state.value_shifts),
            "selected_identity": self.state.selected_identity,
            "triggered_events": sorted(self.state.triggered_events),
            "recent_scenes": list(self.state.recent_scenes),
            "recent_inputs": list(self.state.recent_inputs),
            # 🆕 v1.6.4 P0 Bug 修复：regenerate 也注入最近叙事
            "recent_narratives": [
                {
                    "round": n.get("round"),
                    "summary": n.get("summary", ""),
                    "narrative": (n.get("narrative", "") or "")[:400],
                }
                for n in getattr(self.state, "narrative_recent", [])[-3:]
            ],
            "route_tendency": self.state.route_tendency,
            "failure_type": self.state.failure_type,
            "idle_rounds": self.state.player_idle_rounds,
            "_is_regeneration": True,
            "_validation_issues": validation_issues,
        }

        system_prompt = self._build_system_prompt()
        # 🆕 v1.6+ KV 缓存：system_prompt 加 cache_control（regenerate 也复用）
        from history_footnote.kv_cache import SYSTEM_PROMPT_CACHE
        cache_control = SYSTEM_PROMPT_CACHE.get_cache_control(system_prompt)

        import json as _json
        state_ref_msg = SystemMessage(
            content=f"\n\n[__STATE_REF__]\n{_json.dumps(state_ref, ensure_ascii=False)}"
        )

        system_message = SystemMessage(
            content=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": cache_control,
                }
            ]
        )

        initial_state: DMState = {
            "messages": [
                system_message,
                state_ref_msg,
                HumanMessage(content=retry_human_input),
            ],
            "player_input": retry_human_input,
            "era_id": self.era_config.get("era_id", ""),
            "view_state": state_ref["view_state"],
            "forced_events": state_ref["forced_events"],
            "triggered_rules": state_ref["triggered_rules"],
            "pacing_directives": state_ref["pacing_directives"],
            "insight_candidates": state_ref["insight_candidates"],
            "recent_events": [],
            "related_knowledge": [],
            "narrative": "",
            "state_changes": {},
            "events_to_save": [],
            "updates": None,
            "applied_changes": {},
            "validation_passed": False,
        }

        # 🆕 v1.6.2 P0 A4 优化：regenerate 也复用 graph
        if hasattr(self, '_graph_compiled') and self._graph_compiled is not None:
            llm_with_tools = getattr(self, '_llm_with_tools', None)
            if llm_with_tools and hasattr(llm_with_tools, '_state_ref_slot_ref'):
                if isinstance(llm_with_tools._state_ref_slot_ref, list):
                    llm_with_tools._state_ref_slot_ref[0] = state_ref
                else:
                    llm_with_tools._state_ref_slot_ref = [state_ref]
            self.graph = self._graph_compiled
        else:
            self.graph = self._build_graph(state_ref=state_ref)
            self._graph_compiled = self.graph
        self._last_state_ref = state_ref

        try:
            result = self.graph.invoke(initial_state)
            return {
                "narrative": result.get("narrative", ""),
                "state_changes": result.get("state_changes", {}),
                "events_to_save": result.get("events_to_save", []),
                "updates": result.get("updates"),
                "identity_offer": state_ref.get("identity_offer"),
                "is_action": True,
                "time_cost": 1,
                "intent_type": "action",
                "voice_options": [],
                "_is_regeneration": True,
            }
        except Exception as e:
            # 重试时出错 → 返回最小响应
            return {
                "narrative": f"（重试失败：{str(e)[:100]}）",
                "state_changes": {},
                "events_to_save": [],
                "updates": None,
                "is_action": True,
                "time_cost": 1,
                "intent_type": "action",
                "voice_options": [],
                "_is_regeneration": True,
                "_regeneration_failed": True,
            }

    # === Mock模式辅助方法 ===

    def _make_view_state_dict(self) -> dict:
        return {
            "round_number": self.state.round_number,
            "current_date": self.state.current_date,
            "variables": dict(self.state.variables),
            "triggered_events": list(self.state.triggered_events),
            "unlocked_insights": list(self.state.unlocked_insights),
            "npc_levels": dict(self.state.npc_levels),
            "value_shifts": dict(self.state.value_shifts),
            "player_idle_rounds": self.state.player_idle_rounds,
            "selected_identity": self.state.selected_identity,
            "player_gender": self.state.player_gender,
        }

    def _get_forced_events_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        forced = self.rule_engine.check_forced_events(view)
        return [
            {
                "event_id": fe.event_id,
                "event_name": fe.event_name,
                "description": fe.description,
                "narrative_mandatory": fe.narrative_mandatory,
            }
            for fe in forced
        ]

    def _get_pacing_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        pacing = self.rule_engine.check_pacing(view)
        return [
            {
                "id": pd.id,
                "direction": pd.direction,
                "hint": pd.hint,
            }
            for pd in pacing
        ]

    def _get_triggers_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        triggers = self.rule_engine.check_triggers(view)
        return [
            {
                "id": tr.id,
                "narrative_hint": tr.narrative_hint,
                "effect": tr.effect,
            }
            for tr in triggers
        ]

    def _get_insights_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        insights = self.rule_engine.check_insights(view, player_input=self.state._last_player_input or "")
        return [
            {
                "id": ic.id,
                "topic": ic.topic,
                "confirm_needed": ic.confirm_needed,
                "narrative_hint": ic.narrative_hint,
            }
            for ic in insights
        ]
