"""🆕 v1.7.30 dm_agent/make_tools 工厂（10 个 LangChain Tool）

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

import logging
from typing import Annotated, Any, TypedDict

_LOG = logging.getLogger("history_footnote.dm_agent.tools")
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

    # 🆕 v2.8.0 段六 W18：fill_chapter_blueprint（章节蓝图 LLM 生成）
    @tool
    def fill_chapter_blueprint(chapter_id: int = 1) -> dict:
        """通过 LLM 生成章节蓝图（v2.8.0 章节制 L2 层 Tool）

        Args:
            chapter_id: 章节序号（1-based）

        Returns:
            dict: ChapterBlueprint to_dict() 序列化结果
            {
                "chapter_id": int,
                "chapter_title": str,
                "chapter_subtitle": str,
                "nodes": [{"index": int, "role": str, "scene": str, ...}],
                "transition_hint": str,
                "meta": {"act": str, "role": str, ...},
            }

        失败时返回空 dict（让调用方走硬编码兑底）
        """
        try:
            from history_footnote.chapter.dm_tool import fill_chapter_blueprint_via_llm
            from history_footnote.sub_facades import ChapterFacade
            from history_footnote.llm_providers import make_llm_for_purpose

            # 1. 构造 ChapterFacade
            facade = ChapterFacade(
                state=state,
                era_config=era_config or {},
                root_dir=None,  # 让 _blueprint_dir 走 default
                drama_manager=None,
            )

            # 2. 构造章节制 LLM（purpose="chapter_init"，温度 0）
            chapter_llm = make_llm_for_purpose(
                purpose="chapter_init",
                provider="mock",  # 段六 W18 默认 mock（避免测试打真 LLM）
                era_config=era_config or {},
            )

            # 3. 调 LLM 生成
            blueprint = fill_chapter_blueprint_via_llm(
                state=state,
                chapter_id=chapter_id,
                era_config=era_config or {},
                llm_callable=chapter_llm,
                chapter_facade=facade,
            )
            if blueprint is None:
                return {}

            return blueprint.to_dict()
        except Exception as e:
            _LOG.error("fill_chapter_blueprint 失败: %s", e)
            return {}

    # 🆕 v2.8.0 段六+ W20：fill_chapter_summary（章节摘要 LLM 生成）
    @tool
    def fill_chapter_summary(
        chapter_id: int = 1,
        core_event: str = "",
        key_choice: str = "",
        build_summary: str = "",
        path_summary: str = "",
    ) -> dict:
        """通过 LLM 生成章节摘要（v2.8.0 章节制 L2 层 Tool）

        Args:
            chapter_id: 章节序号（1-based）
            core_event: 核心事件（从 state.event_log 提取）
            key_choice: 关键选择（从 state.last_voice_options 提取）
            build_summary: 玩家 Build 画像
            path_summary: 当前活跃路径

        Returns:
            dict: {"summary": str, "length": int, "via": "llm|rule"}
            via="rule" 表示 LLM 失败回退到规则压缩
        """
        try:
            from history_footnote.chapter.dm_tool import fill_chapter_summary_via_llm
            from history_footnote.llm_providers import make_llm_for_purpose

            # 构造章节制 LLM（purpose="chapter_settle"，温度 0）
            summary_llm = make_llm_for_purpose(
                purpose="chapter_settle",
                provider="mock",  # 段六+ W20 默认 mock
                era_config=era_config or {},
            )

            # 调 LLM 生成摘要
            summary = fill_chapter_summary_via_llm(
                state=state,
                chapter_id=chapter_id,
                core_event=core_event or "无显著事件",
                key_choice=key_choice or "无显著选择",
                build_summary=build_summary or "Build 画像不显著",
                path_summary=path_summary or "无活跃路径",
                era_config=era_config or {},
                llm_callable=summary_llm,
                max_words=200,
            )
            return {
                "summary": summary,
                "length": len(summary),
                "via": "llm",
            }
        except Exception as e:
            _LOG.error("fill_chapter_summary 失败: %s", e)
            return {
                "summary": "本章无显著进展",
                "length": 8,
                "via": "rule",
            }

    return [get_state, recall_events, check_rules, query_knowledge, query_narrative_snippets, query_story_segments, get_random_segment, roll_dice, offer_identity_switch, save_event, fill_chapter_blueprint, fill_chapter_summary]


# === 🆕 v2.10.1 W52 P1-1: 轻量关键词提取（无 jieba 依赖） ===
# 原本在 agent.py 行 487-519，v1.7.30 拆 tools.py 时漏移
# 实际被 agent.py._prefetch_query_tools 用，故搬到 tools.py 跟 query_knowledge 工具配套

def extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """🆕 v2.7+ 轻量关键词提取（无 jieba 依赖）

    策略：中文按 2-gram 切分（2 字常见词） + 停用词过滤 + 去重
    - 输入 "我走进织坊检查织机" → ["织坊", "检查", "织机", "走进"]
    - 输入 "我去街上走走" → ["街上", "走走"]
    """
    if not text:
        return []
    text = text.strip()
    if not text:
        return []

    # 1) 2-gram 切分
    keywords = []
    for i in range(len(text) - 1):
        bigram = text[i:i+2]
        # 过滤：单字停用 + 双字都停用
        if any(c in _STOP_WORDS for c in bigram):
            continue
        # 过滤：含标点
        if any(not (c.isalnum() or '\u4e00' <= c <= '\u9fff') for c in bigram):
            continue
        if bigram not in keywords:
            keywords.append(bigram)
        if len(keywords) >= max_keywords:
            break

    # 2) 如果没找到（全是停用词），fallback 原始文本
    if not keywords:
        return [text[:max_keywords*2]]
    return keywords


# 停用词表（中文单字 + 2 字）
_STOP_WORDS = {
    # 单字停用
    "的", "了", "是", "我", "你", "他", "她", "它", "在", "和", "与", "或",
    "也", "都", "就", "要", "有", "没", "不", "这", "那", "些", "吧", "吗",
    "呢", "啊", "哦", "嗯", "把", "让", "给", "从", "向", "到", "为", "对",
    "用", "做", "说", "看", "想", "去", "来", "上", "下", "出", "入", "起",
    "会", "能", "可", "么", "什", "谁", "哪", "怎", "时", "日", "月", "年",
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    # 2 字停用
    "什么", "怎么", "为什么", "可以", "应该", "已经", "正在", "现在",
    "但是", "如果", "因为", "所以", "于是", "然后", "接着", "最后",
    "他们", "我们", "你们", "它们", "这个", "那个", "这样", "那样",
    "知道", "觉得", "认为", "发现", "听说", "感觉", "希望", "打算",
}