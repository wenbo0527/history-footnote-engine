"""Mock LLM——Phase 1用预设剧本模拟DM的Proactive行为

设计目标：
- 实现LangChain BaseChatModel接口（可替换为真实LLM）
- 模拟DM的"自主决策"：
  1. 调Tool查状态/规则/记忆/知识
  2. 基于Tool结果生成叙事
  3. 输出最终叙事+状态变更
- 支持多轮Tool Calling（2-3轮）

Mock策略：
- 第一轮：必须调 get_state（读取状态）
- 第二轮：根据state决策（可能调 check_rules / recall_events / query_knowledge）
- 第三轮：生成最终叙事
"""
from __future__ import annotations

import json
import random
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


# === DM的Mock决策逻辑 ===

def _mock_dm_decide_tools(state: dict, config: dict) -> list[dict]:
    """Mock DM的"自主决策"——决定要调哪些Tool

    Returns:
        list of {"name": str, "args": dict, "id": str}
    """
    tools_to_call = []
    tool_call_id_counter = [0]

    def add_tool(name: str, args: dict):
        tool_call_id_counter[0] += 1
        tools_to_call.append(
            {
                "name": name,
                "args": args,
                "id": f"call_{tool_call_id_counter[0]}",
            }
        )

    player_input = state.get("player_input", "")

    # 第一步：永远先调 get_state
    add_tool("get_state", {})

    # 第二步：根据state决策
    view = state.get("view_state", {})
    round_number = view.get("round_number", 1)
    forced_events = state.get("forced_events", [])
    pacing_directives = state.get("pacing_directives", [])
    insight_candidates = state.get("insight_candidates", [])

    # 如果有强制历史事件，DM会调 check_rules 确认
    if forced_events:
        add_tool("check_rules", {"check_type": "forced_events"})

    # 如果有节奏推进指令，调 check_rules 查更多
    if pacing_directives:
        add_tool("check_rules", {"check_type": "pacing"})

    # 如果有认知解锁候选，调 recall_events 召回相关历史
    if insight_candidates:
        add_tool("recall_events", {"query": player_input[:50]})

    # 新增：根据玩家输入的场景，调 query_narrative_snippets 获取叙事片段
    snippets = config.get("knowledge", {}).get("narrative_snippets", [])
    if snippets:
        # 简单场景检测
        scene = _detect_scene_from_input(player_input)
        if scene:
            # 从state_ref获取player_gender
            state_ref_view = state.get("state_ref", {})
            player_gender = state_ref_view.get("player_gender", "")
            add_tool(
                "query_narrative_snippets",
                {"scene": scene, "top_k": 1, "player_gender": player_gender},
            )

    # 新增：DND分段叙事——调get_random_segment获取场景片段
    story_segments = config.get("knowledge", {}).get("story_segments", {})
    if story_segments:
        scene = _detect_scene_from_input(player_input)
        if scene:
            # 40%概率随机抽一条（其余60%走query_narrative_snippets）
            import random
            if random.random() < 0.4:
                add_tool(
                    "get_random_segment",
                    {"scene": scene},
                )

    # 新增：检查identity_switch_offers，看是否满足触发条件
    identity_offers = config.get("world", {}).get("identity_switch_offers", [])
    state_ref_view = state.get("state_ref", {})
    current_identity = state_ref_view.get("view_state", {}).get("selected_identity", "")
    current_round = state_ref_view.get("view_state", {}).get("round_number", 1)
    current_variables = state_ref_view.get("view_state", {}).get("variables", {})
    unlocked_insights = state_ref_view.get("view_state", {}).get("unlocked_insights", [])

    for offer in identity_offers:
        if offer.get("from_identity") != current_identity:
            continue
        cond = offer.get("trigger_condition", {})

        # 条件检查
        if current_round < cond.get("min_round", 0):
            continue
        if "min_silver_pressure_lt" in cond:
            sp = current_variables.get("silver_pressure", 0)
            if sp >= cond["min_silver_pressure_lt"]:
                continue
        if "min_livelihood_gte" in cond:
            li = current_variables.get("livelihood", 0)
            if li < cond["min_livelihood_gte"]:
                continue
        if "required_insights_any" in cond:
            if not any(ins in unlocked_insights for ins in cond["required_insights_any"]):
                continue

        # 满足条件 → 决定是否发起offer（Mock：每5个round有50%概率发起）
        if current_round >= 5 and current_round % 5 == 0:
            import random
            if random.random() < 0.5:
                add_tool(
                    "offer_identity_switch",
                    {
                        "to_identity": offer["to_identity"],
                        "reason": offer.get("prompt_hint", "你的人生出现了新的可能...")[:100],
                        "cost": offer.get("cost_description", ""),
                        "benefit": offer.get("benefit_description", ""),
                    },
                )
                break  # 一次只发一个offer

    return tools_to_call


def _detect_scene_from_input(text: str) -> str:
    """根据玩家输入检测场景（与KnowledgeBase.detect_scene同逻辑）"""
    scene_keywords = {
        "茶馆": ["茶馆", "喝茶", "听说", "听人聊", "闲谈", "八卦"],
        "牙行": ["牙行", "卖绸", "买丝", "行情", "牙人", "客商机"],
        "盛泽市集": ["集市", "市集", "上街", "出门", "去市里", "镇上"],
        "自家作坊": ["织机", "缫丝", "作坊", "织布", "理经", "在家里"],
        "镇外桑田": ["桑田", "桑叶", "养蚕", "蚕", "出镇", "村外", "借宿", "农家"],
        "县衙": ["县衙", "知县", "官府", "告状", "里长", "里老", "催税", "税单"],
    }
    for scene, kws in scene_keywords.items():
        if any(kw in text for kw in kws):
            return scene
    return ""


def _mock_dm_generate_narrative(state: dict, config: dict) -> dict:
    """Mock DM生成最终叙事

    Returns:
        {
            "narrative": "...",
            "state_changes": {...},
            "events_to_save": [...],
            "updates": {...} or None
        }
    """
    # 优先用 state_ref（包含实时的 view_state、forced_events 等）
    state_ref = state.get("state_ref", {})
    view = state_ref.get("view_state", state.get("view_state", {}))
    forced_events = state_ref.get("forced_events", state.get("forced_events", []))
    pacing_directives = state_ref.get("pacing_directives", state.get("pacing_directives", []))
    insight_candidates = state_ref.get("insight_candidates", state.get("insight_candidates", []))
    triggered_rules = state_ref.get("triggered_rules", state.get("triggered_rules", []))

    narrative_parts = []
    state_changes = {}
    events_to_save = []
    updates = {}

    # 时代背景元信息
    timeline = config.get("world", {}).get("timeline", {})
    current_date = view.get("current_date", "")
    round_number = view.get("round_number", 1)
    season = _get_season(config, round_number)

    # === 构建叙事 ===

    # 1. 季节/日期氛围开头
    if season:
        narrative_parts.append(season.get("narrative_flavor", ""))

    # 2. 强制历史事件（最高优先级）
    for fe in forced_events:
        if fe.get("narrative_mandatory"):
            narrative_parts.append(
                f"【{fe['event_name']}】{fe['description']}"
            )
            events_to_save.append(f"第{view.get('round_number', '?')}回合：{fe['event_name']}")

    # 3. 节奏推进：NPC主动找玩家
    for pd in pacing_directives:
        if pd.get("direction") == "npc_initiate":
            narrative_parts.append(
                "门被推开了，李秀才提着一壶酒进来，也不问你就坐下了。\n"
                '"今天在茶馆听到个事——"他给自己倒了碗酒，'
                '"你听说了吗？"他喝了一口，"不过跟咱们也没关系。来，喝一口？"'
            )

    # 4. 触发器效果
    for tr in triggered_rules:
        if tr.get("narrative_hint"):
            narrative_parts.append(tr["narrative_hint"])
        for var_id, change in tr.get("effect", {}).items():
            state_changes[var_id] = state_changes.get(var_id, 0) + change

    # 5. 认知解锁候选
    for ic in insight_candidates:
        if ic.get("narrative_hint"):
            narrative_parts.append(ic["narrative_hint"])
        if not ic.get("confirm_needed"):
            # narrative_guided类型直接解锁
            updates[f"insight:{ic['id']}"] = "unlocked"
        else:
            # player_explore类型：DM终判——如果玩家输入与insight topic相关，认为应该解锁
            # 简化：如果是player_explore且player_input包含trigger_keywords，认为解锁
            updates[f"insight:{ic['id']}"] = "unlocked"

    # 6. 玩家输入的简单回响（关键词匹配）
    player_input = state.get("player_input", "")
    if "织" in player_input or "丝绸" in player_input:
        narrative_parts.append("你坐到织机前，开始理经线，手指机械地穿梭。")
    if "税" in player_input or "银子" in player_input:
        narrative_parts.append("你算了算今年的税单，叹了口气。")
    if "茶馆" in player_input:
        narrative_parts.append("你走进茶馆，要了碗茶坐下。隔壁桌在聊京城的八卦。")
    if not narrative_parts[1:]:  # 如果除了季节没有别的
        narrative_parts.append("又是一天。织机声在巷子里响着，和往常一样。")

    # 6.5 新增：融合narrative_snippets（DM调query_narrative_snippets的结果）
    available_snippets = state_ref.get("available_snippets", [])
    if available_snippets:
        # 选第一个匹配的snippet融入叙事
        snip = available_snippets[0]
        snippet_text = snip.get("snippet_text", "")
        if snippet_text:
            # 简化：直接引用原文（最自然的植入方式）
            narrative_parts.append(f'（{snip.get("npc_use_case", "")}）"{snippet_text}"')

    # 6.6 新增：DND分段叙事——融入随机抽取的story_segment
    # 优先用available_story_segments（DM抽到的）
    available_story_segments = state_ref.get("available_story_segments", [])
    if not available_story_segments:
        # 备用：直接从config抽取
        story_segments_data = config.get("knowledge", {}).get("story_segments", {})
        scene = _detect_scene_from_input(player_input)
        if scene and scene in story_segments_data:
            import random
            segs = story_segments_data[scene]
            if segs:
                available_story_segments = [random.choice(segs)]
    if available_story_segments:
        seg = available_story_segments[0]
        seg_text = seg.get("text", "")
        seg_type = seg.get("type", "")
        npc_role = seg.get("npc_role", "")
        if seg_type == "npc_dialog" and npc_role:
            narrative_parts.append(f'\n{npc_role}："{seg_text}"')
        elif seg_text:
            narrative_parts.append(f'\n{seg_text}')

    # 7. 价值观微调（基于玩家输入的简单情感分析）
    if any(kw in player_input for kw in ["交税", "按时", "本分"]):
        updates["value:duty_vs_freedom"] = -1
    if any(kw in player_input for kw in ["不交", "逃", "躲"]):
        updates["value:duty_vs_freedom"] = 1

    # 默认事件记录
    if not events_to_save:
        events_to_save.append(
            f"第{view.get('round_number', '?')}回合：{_truncate(player_input, 30) or '日常'}"
        )

    return {
        "narrative": "\n\n".join(filter(None, narrative_parts)),
        "state_changes": state_changes,
        "events_to_save": events_to_save,
        "updates": updates if updates else None,
    }


def _get_season(config: dict, round_number: int) -> dict | None:
    """根据回合数获取季节信息"""
    timeline = config.get("world", {}).get("timeline", {})
    start = timeline.get("start", {})
    start_month = start.get("month", 1)
    # 每回合推进1个月（简化为单月制）
    target_month = ((start_month - 1 + round_number - 1) % 12) + 1
    for s in config.get("world", {}).get("seasons", []):
        if s.get("month") == target_month:
            return s
    return None


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


# === 共享state_ref存储 ===
# 类级别的dict，bind_tools复制model时不会丢失引用
# key是model的id()，value是state_ref dict
_SHARED_STATE_REFS: dict[int, dict] = {}


# === LangChain ChatModel实现 ===

class MockDMChatModel(BaseChatModel):
    """Mock DM ChatModel——实现LangChain BaseChatModel接口

    Usage:
        from langchain_core.messages import SystemMessage, HumanMessage
        model = MockDMChatModel(era_config={...})
        result = model.invoke([
            SystemMessage(content="你是DM..."),
            HumanMessage(content="玩家输入...")
        ])
    """

    era_config: dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 每个实例一个state_ref slot
        # 用PrivateAttr-like方式存储：直接挂在实例上（不经过Pydantic字段）
        # 这样model_copy不会重置它（用引用共享）
        object.__setattr__(self, "_state_ref_slot_ref", [{}])  # 列表包装以保持mutable

    @property
    def _llm_type(self) -> str:
        return "mock-dm"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成DM响应

        Mock实现策略：
        - 第一次调用：返回Tool calls（模拟DM调Tool查状态）
        - 第二次调用：返回最终叙事（模拟DM融合Tool结果生成输出）
        """
        # 提取玩家输入（最后一条HumanMessage）
        player_input = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                player_input = msg.content
                break

        # 检查消息历史里有没有ToolMessage（如果有说明是第二轮）
        has_tool_results = any(isinstance(m, ToolMessage) for m in messages)

        # 优先用最新的 state_ref（来自 _state_ref_slot_ref，每次run更新）
        state_ref = self._state_ref_slot_ref[0]

        if not has_tool_results:
            # 第一轮：决定调哪些Tool
            tools = self._get_bound_tools()
            tool_calls = _mock_dm_decide_tools(
                {"player_input": player_input, "state_ref": state_ref},
                self.era_config,
            )
            # 转换成LangChain格式
            formatted_calls = [
                {
                    "id": tc["id"],
                    "name": tc["name"],
                    "args": tc["args"],
                }
                for tc in tool_calls
            ]
            message = AIMessage(
                content="",
                tool_calls=formatted_calls,
            )
        else:
            # 第二轮：生成最终叙事
            result = _mock_dm_generate_narrative(
                {"player_input": player_input, "state_ref": state_ref},
                self.era_config,
            )
            # 序列化为JSON注入content
            content = json.dumps(result, ensure_ascii=False)
            message = AIMessage(content=content)

        return ChatResult(generations=[ChatGeneration(message=message)])

    def _get_bound_tools(self) -> list[dict]:
        """获取已绑定的Tool schema（从外部state推断）"""
        # 在game_loop里，tools会在bind时设置
        return getattr(self, "_bound_tools", [])

    def bind_tools(self, tools, **kwargs):
        """绑定tools——记录到内部状态"""
        new_model = self.model_copy()
        new_model._bound_tools = [
            {
                "name": t.name if hasattr(t, "name") else t.get("name"),
                "description": t.description if hasattr(t, "description") else t.get("description", ""),
            }
            for t in tools
        ]
        # 共享 state_ref slot 引用（同一个list）
        object.__setattr__(new_model, "_state_ref_slot_ref", self._state_ref_slot_ref)
        return new_model
