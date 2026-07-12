"""🆕 v2.10.1 W52 P1-1: DMAgent 主类

🆕 v2.10.1 W52 P1-1 拆分说明：
- v1.7.30 已把 make_tools / make_dm_nodes / extract_narrative_node / DMState
  拆到 dm_agent/tools.py / nodes/* / state.py
- 本次 W52 P1-1 进一步清理 agent.py 中残留的 dead code
  （make_tools / make_dm_nodes / extract_narrative_node / state_confirmation_node
   / DMState / _extract_keywords，全部无人调用）
- 仅保留 active 的 DMAgent 类
- 公开符号：DMAgent（其他符号从 history_footnote.dm_agent 仍可访问，详见 __init__.py）
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from history_footnote.game_state import GameState
from history_footnote.knowledge_base import KnowledgeBase
from history_footnote.rule_engine import RuleEngine
from history_footnote.game_memory import GameMemory
from history_footnote.dm_agent.mock_helpers import MockHelpersMixin
# 🆕 v2.10.1 W52 P1-1: 关键词提取已迁到 tools.py（与 query_knowledge 工具配套）
from history_footnote.dm_agent.tools import extract_keywords as _extract_keywords_compat
# 🆕 v2.10.1 W52 P1-1: make_dm_nodes 已在 v1.7.30 拆到 nodes/factory.py
from history_footnote.dm_agent.nodes.factory import make_dm_nodes
# 🆕 v2.10.1 W52 P1-1: DMState 已在 v1.7.30 拆到 state.py
from history_footnote.dm_agent.state import DMState
# 🆕 v2.10.1 W52 P1-1 PR#2: 7 个 _build_* 拆到 prompts.py
from history_footnote.dm_agent.prompts import (
    build_prefetch_message as _build_prefetch_message_impl,
    build_system_prompt as _build_system_prompt_impl,
    load_dm_persona as _load_dm_persona_impl,
    build_current_city_section as _build_current_city_section_impl,
    build_current_location_section as _build_current_location_section_impl,
    build_fate_used_section as _build_fate_used_section_impl,
    build_recent_context_for_prompt as _build_recent_context_for_prompt_impl,
)

logger = logging.getLogger("history_footnote.dm_agent")


# === DM Agent主类 ===

class DMAgent(MockHelpersMixin):
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
        # 🆕 W35: 用 tools.py.make_tools（含 fill_chapter_* 12 个 Tool）而非本地 10 个 make_tools
        # 历史原因：agent.py:90 的本地 make_tools 早于 v2.8.0 章节制（不含 fill_chapter）
        # 用 dm_agent.tools.make_tools 让 LLM 能看到所有 12 个 Tool
        from history_footnote.dm_agent.tools import make_tools as dm_make_tools
        self.tools = dm_make_tools(state, rule_engine, memory, knowledge_base, era_config)

        # 🆕 v2.7+ Wiki Agent 拆分：把 10 个 tool 拆成两类
        # - query_tools: 6 个查询类（get_state / recall_events / check_rules / query_knowledge / query_narrative_snippets / query_story_segments）
        #   这些在 game_loop 阶段已预取（结果在 state_ref.wiki_hint 等）
        #   LLM#1 看不到这些工具，自然不调
        # - decision_tools: 4 个决策类（get_random_segment / roll_dice / offer_identity_switch / save_event）
        #   这些必须 LLM 决策
        # 节省：消除 LLM#1 反复调 6 个查询类 tool 的 3-30s 开销
        _QUERY_TOOL_NAMES = {
            "get_state", "recall_events", "check_rules", "query_knowledge",
            "query_narrative_snippets", "query_story_segments",
        }
        self.query_tools = [t for t in self.tools if getattr(t, "name", "") in _QUERY_TOOL_NAMES]
        self.decision_tools = [t for t in self.tools if getattr(t, "name", "") not in _QUERY_TOOL_NAMES]
        logger.info(
            f"[v2.7+ agent split] query_tools={len(self.query_tools)} (不 bind), "
            f"decision_tools={len(self.decision_tools)} (bind 给 LLM)"
        )

        # ⚠️ 优化 A 实验结论：cache_control 在 MiniMax-M3 端点**不可用**
        # 表现：HTTP 200 OK 但 LangChain parse 失败（TypeError: NoneType is not iterable）
        # 原因：MiniMax-M3 走兼容协议，response_metadata 字段为 None
        # 解决：等 MiniMax 修复，或直接传 raw extra_body
        # 暂时禁用此优化（保留 _tools_cache_control 字段以备将来启用）
        self._tools_cache_control = None
        # self._tools_cache_control = {"type": "ephemeral"}  # 5min TTL（MiniMax 不支持）

        # 绑定 tools 到 LLM（**只绑决策类**——LLM 看不到查询类，自然不调）
        # bind_tools 返回新模型，新模型会通过 model_copy 共享 _state_ref_slot_ref
        if hasattr(self.llm, "bind_tools"):
            if self._tools_cache_control:
                new_llm = self.llm.bind_tools(
                    self.decision_tools,
                    cache_control=self._tools_cache_control,
                )
            else:
                new_llm = self.llm.bind_tools(self.decision_tools)
            self._llm_with_tools = new_llm
        else:
            new_llm = self.llm
            self._llm_with_tools = new_llm

        # 构建StateGraph（一次性创建，复用）
        self.graph = self._build_graph()
        # 🆕 v1.6.2 P0 A4 优化：缓存 graph 引用，永久复用
        self._graph_compiled = self.graph

    # === 🆕 v2.7+ 预取：批量本地查询，节省 LLM#1 决策循环 ===

    def _prefetch_query_tools(self, player_input: str) -> dict:
        """🆕 v2.7+ 预取 6 个本地查询类 tool，结果打包成 dict

        设计目的：
        - 替代 LLM#1 ReAct 循环（LLM 调 1-4 次 tool 浪费时间）
        - 6 个查询类 tool 全是本地函数（< 5ms/each）
        - 一次预取 + LLM#1 直接看结果决策"够不够" = 单轮 LLM#1

        Returns:
            dict: 各 tool 返回结果，key 是 tool 名
            {"state": {...}, "rules": {...}, "knowledge": [...], "events": [...], ...}
        """
        if not self.tools:
            return {}

        import time as _t
        _t0 = _t.time()

        # tools 顺序（make_tools 返回）：
        # 0: get_state, 1: recall_events, 2: check_rules, 3: query_knowledge,
        # 4: query_narrative_snippets, 5: query_story_segments
        result = {}
        try:
            # 1) get_state（必有）
            result["state"] = self.tools[0].invoke({})

            # 2) recall_events（基于 player_input 关键词查询 + 最近 3 回合）
            try:
                result["events"] = self.tools[1].invoke({
                    "query": player_input or "",
                    "recent_n": 3,
                })
            except Exception as e:
                logger.debug(f"[v2.7 prefetch] recall_events failed: {e}")
                result["events"] = []

            # 3) check_rules（默认全检查）
            try:
                result["rules"] = self.tools[2].invoke({
                    "action": "",
                    "check_type": "all",
                })
            except Exception as e:
                logger.debug(f"[v2.7 prefetch] check_rules failed: {e}")
                result["rules"] = {}

            # 4) query_knowledge（从 player_input 提取关键词）
            keywords = _extract_keywords_compat(player_input or "")
            try:
                result["knowledge"] = self.tools[3].invoke({
                    "keywords": keywords,
                    "scene": getattr(self.state, "current_location", "") or "",
                })
            except Exception as e:
                logger.debug(f"[v2.7 prefetch] query_knowledge failed: {e}")
                result["knowledge"] = []

            # 5) query_narrative_snippets（基于当前场景 + 关键词）
            try:
                result["narrative_snippets"] = self.tools[4].invoke({
                    "scene": getattr(self.state, "current_location", "") or "",
                    "keywords": keywords,
                    "top_k": 2,
                    "player_gender": getattr(self.state, "player_gender", "") or "",
                })
            except Exception as e:
                logger.debug(f"[v2.7 prefetch] query_narrative_snippets failed: {e}")
                result["narrative_snippets"] = []

            # 6) query_story_segments
            try:
                result["story_segments"] = self.tools[5].invoke({
                    "scene": getattr(self.state, "current_location", "") or "",
                    "top_k": 3,
                })
            except Exception as e:
                logger.debug(f"[v2.7 prefetch] query_story_segments failed: {e}")
                result["story_segments"] = []

        except Exception as e:
            logger.warning(f"[v2.7 prefetch] failed: {e}")

        dt = (_t.time() - _t0) * 1000
        logger.info(
            f"[DM-PROF]   prefetch_query_tools: {dt:.0f}ms "
            f"(state={len(result.get('state', {}))} keys, "
            f"events={len(result.get('events', []))}, "
            f"knowledge={len(result.get('knowledge', []))}, "
            f"snippets={len(result.get('narrative_snippets', []))})"
        )
        return result

    def _build_prefetch_message(self, prefetched: dict) -> "SystemMessage":
        """把预取结果打包成 SystemMessage——委托给 prompts.build_prefetch_message"""
        return _build_prefetch_message_impl(prefetched)

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

        # 绑定tools到LLM（🆕 v2.7+ 只 bind 决策类，6 个查询类已预取）
        # ⚠️ 优化 A（tools cache_control）当前**禁用**——MiniMax-M3 不支持
        if hasattr(self.llm, "bind_tools"):
            if self._tools_cache_control:
                llm_with_tools = self.llm.bind_tools(
                    self.decision_tools,
                    cache_control=self._tools_cache_control,
                )
            else:
                llm_with_tools = self.llm.bind_tools(self.decision_tools)
        else:
            llm_with_tools = self.llm
        # 把 state_ref 存到 llm_with_tools（Mock LLM会用）
        # 必须用 [0] = state_ref 修改列表内容，保持引用不断开
        if hasattr(llm_with_tools, "_state_ref_slot_ref"):
            if isinstance(llm_with_tools._state_ref_slot_ref, list):
                llm_with_tools._state_ref_slot_ref[0] = state_ref
            else:
                llm_with_tools._state_ref_slot_ref = [state_ref]

        # 构造节点（闭包绑定llm_with_tools和state_ref）
        # 🆕 v2.7+ 实验结论：pre_fetch 接入 workflow 会让 LLM#2 慢 5-10x（context 暴增）
        # pre_fetch_tools_node 仍存在（代码保留），但**不**接入 workflow
        # 🆕 v2.10.1 W52 P1-1: 工具和 player_input_getter 改为写入 state_ref
        # （dm_agent.nodes.factory.make_dm_nodes 只接 (llm_with_tools, state_ref)）
        state_ref["tools"] = self.tools
        state_ref["player_input_getter"] = lambda: getattr(self, "_last_player_input", "") or ""
        skill_node, situation_node, should_continue, narrative_node, extract_node = make_dm_nodes(
            llm_with_tools, state_ref,
        )

        workflow = StateGraph(DMState)

        # 节点
        workflow.add_node("skill_orchestration", skill_node)
        workflow.add_node("situation_assessment", situation_node)
        workflow.add_node("narrative_fusion", narrative_node)
        workflow.add_node("extract_narrative", extract_node)

        # Tool执行节点（LangGraph内置）—— 🆕 v2.7+ 只执行决策类 tool
        tool_node = ToolNode(self.decision_tools)
        workflow.add_node("call_tools", tool_node)

        # 入口：先跑 DM skills → situation_assessment
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
        """构建 System Prompt——委托给 prompts.build_system_prompt"""
        return _build_system_prompt_impl(self.era_config, self.state, self.selected_identity)

    def _load_dm_persona(self) -> str | None:
        """加载 dm_persona.md——委托给 prompts.load_dm_persona"""
        return _load_dm_persona_impl(self.era_config)

    def _build_current_city_section(self) -> str:
        """城市 sensory 注入——委托给 prompts.build_current_city_section"""
        return _build_current_city_section_impl(self.era_config, self.state)

    def _build_current_location_section(self) -> str:
        """当前位置 + NPC + 命运卡注入——委托给 prompts.build_current_location_section"""
        return _build_current_location_section_impl(self.era_config, self.state)

    def _build_fate_used_section(self) -> str:
        """已用命运卡 + buff 注入——委托给 prompts.build_fate_used_section"""
        return _build_fate_used_section_impl(self.state)

    def _build_recent_context_for_prompt(self) -> str:
        """最近剧情上下文注入——委托给 prompts.build_recent_context_for_prompt"""
        return _build_recent_context_for_prompt_impl(self.state)

    def run(self, player_input: str) -> dict:
        """运行一回合DM Agent

        Args:
            player_input: 玩家输入

        Returns:
            {"narrative": str, "state_changes": dict, "events_to_save": list, "updates": dict|None}
        """
        # 🆕 v2.7+ 性能剖析：per-stage 计时
        _prof_t0 = time.time()
        _prof_stages = []

        def _stage(name, t_start):
            dt = (time.time() - t_start) * 1000
            _prof_stages.append((name, dt))
            logger.info(f"[DM-PROF] {name}: {dt:.0f}ms (total {(time.time()-_prof_t0)*1000:.0f}ms)")
            return time.time()

        # 记录玩家输入到state（供check_rules的insight检查使用）
        self.state._last_player_input = player_input
        # 🐛 v1.6+ 修复：每次 run 同步 selected_identity（避免 selected_identity 不更新）
        self.selected_identity = self.state.selected_identity or ""
        _t = time.time()

        # 构建最新的state_ref（用于Mock LLM实时读取状态）
        state_ref = {
            "view_state": self._make_view_state_dict(),
            "forced_events": self._get_forced_events_for_mock(),
            "triggered_rules": self._get_triggers_for_mock(),
            "pacing_directives": self._get_pacing_for_mock(),
            "insight_candidates": self._get_insights_for_mock(),
            # 🆕 v1.7.36 DramaManager 干预 hint（保留兼容，实际从 bind_state_ref slot 读取）
            "drama_hint": "",
            # 🆕 v1.7.37 Wiki 检索 hint（按需注入）
            "wiki_hint": "",
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
        _t = _stage("prep state_ref", _t)
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
        _t = _stage("_build_system_prompt", _t)

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
        _t = _stage("build graph + initial_state", _t)
        _t_graph = time.time()
        result = self.graph.invoke(initial_state)
        _stage("graph.invoke", _t_graph)

        # 🆕 v1.7.23: narrative 短答重试机制
        # 🆕 v1.7.25: 扩到末尾问号检测（无问号也重试）
        # 背景：LLM 偶尔输出 < 100 字（远低于 prompt 要求的 300-500 字）
        #       或末尾无问号（玩家不知道要决策什么）
        # 现象：玩家看到"你只需要做一件事：在这个年头上活着。"等短答
        # 修复：narrative < 100 字 或 末尾 30 字无问号 时重试 1-2 次
        narrative = result.get("narrative", "")
        import logging
        _log = logging.getLogger("history_footnote.dm_agent")
        # 🆕 v1.7.25 工具函数：检测末尾问号
        def _narr_ends_with_question(text: str) -> bool:
            if not text:
                return False
            tail = text[-30:].strip()
            return ("?" in tail) or ("？" in tail)
        # 判断是否需要重试
        need_retry = False
        retry_reason = ""
        # 🆕 v2.3 字数约束（按时间模式，详见 system_base.md "字数控制" 章节）
        # 默认上限 800 字；时间模式信息在 skill_pacing.time_mode 里
        skill_pacing = state_ref.get("skill_pacing", {}) if isinstance(state_ref, dict) else {}
        time_mode = skill_pacing.get("time_mode", "now_time") if isinstance(skill_pacing, dict) else "now_time"
        # 🆕 v2.10.1 W52 候选 E：narrative 后处理已抽到 narrative_postprocess.py
        from history_footnote.dm_agent.narrative_postprocess import (
            postprocess_narrative,
            check_narrative_quality,
        )
        need_retry, retry_reason = check_narrative_quality(narrative, time_mode)
        if need_retry:
            _log.warning(
                f"[v2.3] narrative {retry_reason}，触发重试"
            )
            def _retry_fn() -> str:
                nonlocal result
                result = self.graph.invoke(initial_state)
                return result.get("narrative", "")
            narrative, _status = postprocess_narrative(
                narrative, time_mode, retry_fn=_retry_fn, max_retries=2
            )

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
            logger.exception("[v1.7.2] LLM 重试失败")
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

