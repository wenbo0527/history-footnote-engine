"""🆕 v2.10.1 W52 P1-1 PR#2: DM Agent Prompt 构建函数模块

把 DMAgent 类中 7 个 _build_* / _load_* 纯提示构建方法拆出：
- build_prefetch_message(prefetched) -> SystemMessage
- build_system_prompt(era_config, state, selected_identity) -> str
- load_dm_persona(era_config) -> str | None
- build_current_city_section(era_config, state) -> str
- build_current_location_section(era_config, state) -> str
- build_fate_used_section(state) -> str
- build_recent_context_for_prompt(state) -> str

DMAgent 类中保留同名方法作为 thin wrapper（向后兼容）。

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-1
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.messages import SystemMessage

logger = logging.getLogger("history_footnote.dm_agent.prompts")


def build_prefetch_message(prefetched: dict) -> "SystemMessage":
    """把预取结果打包成 SystemMessage（注入到 LLM#1 的 messages 头部）

    内容裁剪原则：
    - state: 全部（关键决策依据）
    - rules: 全部（命中条件）
    - events: 最多 5 条（避免超长）
    - knowledge: 最多 3 条，每条 title + content 截断 200 字
    - narrative_snippets: 最多 2 条，snippet_text 截断 200 字
    - story_segments: 最多 3 条，text 截断 150 字
    """
    from langchain_core.messages import SystemMessage

    def _truncate(value: str, max_len: int = 200) -> str:
        if not value or len(value) <= max_len:
            return value
        return value[:max_len] + "…"

    def _clip_list(items: list, key: str, max_n: int, max_text_len: int = 200) -> list:
        clipped = []
        for item in (items or [])[:max_n]:
            if isinstance(item, dict):
                new_item = {}
                for k, v in item.items():
                    if isinstance(v, str) and k in (
                        "content", "snippet_text", "text", "title", "npc_use_case"
                    ):
                        new_item[k] = _truncate(v, max_text_len)
                    else:
                        new_item[k] = v
                clipped.append(new_item)
            else:
                clipped.append(item)
        return clipped

    clipped = {
        "state": prefetched.get("state", {}),
        "rules": prefetched.get("rules", {}),
        "events": (prefetched.get("events") or [])[:5],
        "knowledge": _clip_list(prefetched.get("knowledge", []), "content", max_n=3, max_text_len=200),
        "narrative_snippets": _clip_list(
            prefetched.get("narrative_snippets", []), "snippet_text", max_n=2, max_text_len=200
        ),
        "story_segments": _clip_list(
            prefetched.get("story_segments", []), "text", max_n=3, max_text_len=150
        ),
    }

    content = (
        "\n\n[__PRE_FETCHED_TOOLS__] 以下是已预先查询的本地工具结果（无需再调用这些查询类 tool）：\n"
        "查询类工具: get_state / recall_events / check_rules / query_knowledge / query_narrative_snippets / query_story_segments\n"
        "决策类工具: roll_dice / offer_identity_switch / save_event（这些仍可正常调用）\n\n"
        f"```json\n{json.dumps(clipped, ensure_ascii=False, indent=2)}\n```\n\n"
        "请基于以上信息直接生成 narrative。"
        "如需调决策类 tool（roll_dice / offer_identity_switch / save_event）仍可正常调用。"
    )
    return SystemMessage(content=content)


def load_dm_persona(era_config: dict) -> str | None:
    """加载 dm_persona.md 文件"""
    persona_path = Path("eras") / era_config.get("era_id", "") / "dm_persona.md"
    if persona_path.exists():
        return persona_path.read_text(encoding="utf-8")
    return None


def build_current_city_section(era_config: dict, state) -> str:
    """根据玩家当前所在城市，从 era.world.cities 注入 sensory 描述

    玩家在盛泽时：返回空字符串（不输出该段）
    玩家在 4 城市之一：返回该城市的 sensory + 差异描述
    """
    cities = era_config.get("world", {}).get("cities", {})
    current_city_id = getattr(state, "current_city", "") or ""
    if not current_city_id or current_city_id not in cities:
        return ""
    city = cities[current_city_id]
    arrival = city.get("narrative_arrival", "")
    sensory = city.get("sensory", {})
    functions = city.get("functions", [])
    danger = city.get("danger_level", 0)
    opportunity = city.get("opportunity_level", 0)
    lines = [
        f"## 🏙️ 当前所在城市：{city.get('name', current_city_id)}",
        f"距离盛泽：{city.get('distance_from_shengze', '?')}  船资：{city.get('travel_cost', '?')}",
        "",
    ]
    if arrival:
        lines.append(f"**到达时**：{arrival}")
        lines.append("")
    if sensory:
        senses = []
        for k in ("sight", "sound", "smell"):
            v = sensory.get(k, "")
            if v:
                cn = {"sight": "👁️ 视觉", "sound": "👂 听觉", "smell": "👃 嗅觉"}[k]
                senses.append(f"- {cn}：{v}")
        if senses:
            lines.append("**感官细节**：")
            lines.extend(senses)
            lines.append("")
    if functions:
        lines.append(f"**可做事项**（{len(functions)} 项）：{', '.join(functions)}")
        lines.append("")
    lines.append(f"**危险等级**：{danger}/5  **机会等级**：{opportunity}/5")
    return "\n".join(lines)


def build_fate_used_section(state) -> str:
    """🆕 v2.6.1 注入已用命运卡 + 当前 buff

    为什么必要：
    - 玩家用了"天降横财"（+3 两）→ DM 不知道 → 下一回合写"揭不开锅" → 矛盾
    - 玩家用了"沈氏倾心"（+30 好感）→ DM 不知道 → 写"沈氏瞪你" → 矛盾
    - 玩家用了"再试一次"buff → DM 不知道 → 失败时不重试 → 失去意义
    """
    try:
        lines = []
        hand = list(getattr(state, "fate_hand", []) or [])
        used_cards = [c for c in hand if c.get("used")]

        if used_cards:
            lines.append("## 🎴 命运已用（DM 必读）")
            lines.append("**已用卡**：")
            for c in used_cards:
                name = c.get("name", "")
                icon = c.get("icon", "")
                desc = c.get("description", "")
                lines.append(f"- {icon} {name}：{desc}")

        # 当前 buff
        active_buffs = list(getattr(state, "active_buffs", []) or [])
        if active_buffs:
            if not lines:
                lines.append("## 🎴 命运已用（DM 必读）")
            else:
                lines.append("")
            lines.append("**当前生效 buff**：")
            for b in active_buffs:
                name = b.get("name", "")
                rounds = b.get("rounds_left", 0)
                params = b.get("params", {}) or {}
                extra = ""
                if name == "lucky":
                    extra = "（所有检定 +10%）"
                elif name == "unlucky":
                    extra = "（所有检定 -10%）"
                elif name == "shield":
                    reduction = int((params.get("failure_reduction", 0.5)) * 100)
                    extra = f"（本回合失败代价 -{reduction}%）"
                elif name == "persuasion":
                    value = params.get("value", 15)
                    extra = f"（本回合所有 NPC 亲和 +{value}）"
                elif name == "second_chance":
                    extra = "（失败时自动重投 1 次）"
                lines.append(f"- ✨ {name}：剩 {rounds} 回合 {extra}")

        # 命运事件标记
        event_flags = list(getattr(state, "fate_event_flags", []) or [])
        if event_flags:
            if not lines:
                lines.append("## 🎴 命运已用（DM 必读）")
            else:
                lines.append("")
            lines.append("**已触发事件**：")
            flag_zh = {
                "zhou_secret": "🤫 周大娘的秘密",
                "li_discount": "📚 李秀才减束脩",
                "shen_illness": "🤒 沈氏生病",
            }
            for f in event_flags:
                lines.append(f"- {flag_zh.get(f, f)}")

        return "\n".join(lines)
    except Exception as e:
        logger.exception(f"[v2.6.1] build_fate_used_section 失败: {e}")
        return ""


def build_current_location_section(era_config: dict, state) -> str:
    """🆕 v2.4 文字地图系统：注入"当前位置" sensory + 邻居 + NPC 关系

    为什么重要：
    - LLM 必须知道"玩家在 home 还是 tooth_market"才能写出符合空间的叙事
    - 不注入会导致叙事跑出位置（"你去了染坊"但玩家实际在 home）
    - 同时注入 neighbors（"可移动到"），让 LLM 知道"可以建议玩家去哪里"
    - 注入 heard 地点（"听过没去过"），让 LLM 能引用"NPC 提起过"作为解锁钩子
    - 🆕 v2.4.1 注入 NPC 当前位置 + 关系网（让 LLM 知道"王牙人在牙行"+ "他和沈氏是客户关系"）
    - 🆕 v2.6.1 注入已用命运卡（让 LLM 知道"天降横财已用"→ 不要再写'揭不开锅'）
    """
    try:
        from history_footnote.location_service import build_location_service
        svc = build_location_service(era_config)
        current_loc_id = getattr(state, "current_location", "") or svc.get_default()
        visited = list(getattr(state, "visited_locations", []) or [])
        heard = list(getattr(state, "heard_locations", []) or [])
        # 1) 地点段
        loc_section = svc.build_prompt_context(current_loc_id, visited, heard)
        # 2) NPC 段（v2.4.1 新增）
        npc_section = svc.build_npc_prompt_section(current_loc_id, max_relationships=4)
        # 3) 已用命运卡段（🆕 v2.6.1 新增）
        fate_used_section = build_fate_used_section(state)
        return "\n\n".join([s for s in [loc_section, npc_section, fate_used_section] if s])
    except Exception as e:
        logger.exception(f"[v2.6.1] build_current_location_section 失败: {e}")
        return ""


def build_recent_context_for_prompt(state) -> str:
    """🆕 v1.6.4 P0 Bug 修复：构建最近叙事上下文

    问题：之前 system prompt 只有 recent_scenes（场景标签如"织机前/茶馆"），
    导致 LLM 不知道上回合完整对话内容（如谁在对话、玩家承诺了什么、状态如何变化），
    从而出现 NPC 混淆（张寡妇 → 陈三）、上下文断裂等问题。

    修复：把最近 N 回合的【摘要 + 玩家输入 + 关键状态】注入到 system prompt。
    """
    recent = getattr(state, "narrative_recent", [])
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
        for ev in (state.event_log or []):
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
        vars_recent = getattr(state, "variables", {}) or {}
        if vars_recent:
            # 只显示非零值
            non_zero = {k: v for k, v in vars_recent.items() if v not in (0, 0.0, "")}
            if non_zero:
                lines.append("**当前关键变量**：")
                for k, v in list(non_zero.items())[:5]:
                    lines.append(f"  - {k}: {v}")

    # 🆕 v2.7.2 追加「结构化剧情事实锚点」段
    facts = state.get_facts_for_prompt() if hasattr(state, "get_facts_for_prompt") else []
    if facts:
        try:
            from history_footnote.narrative_facts_extractor import build_facts_injection
            from history_footnote.narrative_facts_extractor import NarrativeFact
            fact_objs = [NarrativeFact.from_dict(f) for f in facts]
            last_input = ""
            if (state.event_log or []):
                for ev in reversed(state.event_log):
                    if ev.get("player_action"):
                        last_input = ev["player_action"]
                        break
            facts_md = build_facts_injection(fact_objs, player_input=last_input)
            if facts_md:
                lines.append("")
                lines.append(facts_md)
        except Exception as e:
            logger.warning(f"[v2.7.2] fact 注入失败: {e}")

    return "\n".join(lines) + "\n"


def build_system_prompt(era_config: dict, state, selected_identity: str) -> str:
    """构建 DM 的 System Prompt——从 era_config 填充"""
    # 优先用 player_identities[selected_identity]，否则用 default_identity
    identities = era_config.get("world", {}).get("player_identities", {})
    identity = identities.get(selected_identity, {})
    if not identity:
        default_id = era_config.get("world", {}).get("default_identity", "")
        identity = identities.get(default_id, {})
    timeline = era_config.get("world", {}).get("timeline", {})
    iron_laws = era_config.get("world", {}).get("iron_laws", [])
    plausibility_rules = era_config.get("world", {}).get("plausibility_rules", [])

    # 加载 dm_persona.md（如有）
    persona_md = load_dm_persona(era_config)
    if persona_md:
        return persona_md

    # 否则用模板生成
    recent_context = build_recent_context_for_prompt(state)

    # 🆕 v1.7.3：system prompt 拆分到 dm/prompts/system_base.md
    from history_footnote.dm.prompts import load_system_base, fill_template
    # 🆕 v1.7.1：注入 Character Wiki 摘要（NPC 关系/承诺/决策时间线）
    wiki_summary = ""
    try:
        from history_footnote.character_wiki import (
            CharacterWiki, render_wiki_summary,
        )
        wiki = CharacterWiki.from_dict(state.character_wiki or {})
        wiki_summary = render_wiki_summary(wiki)
    except Exception:
        logger.exception("[v1.7.3] wiki 摘要生成失败")

    return fill_template(
        load_system_base(),
        era_name=era_config.get('era_name', '万历十五年'),
        recent_context=recent_context,
        timeline_description=timeline.get('description', ''),
        iron_laws=[f"- {law['fact']}" for law in iron_laws],
        identity_role=identity.get('role', '小人物'),
        identity_class=identity.get('social_class', ''),
        can_access=', '.join(identity.get('action_boundaries', {}).get('can_access', [])),
        cannot_access=', '.join(identity.get('action_boundaries', {}).get('cannot_access', [])),
        can_interact_with=', '.join(identity.get('action_boundaries', {}).get('can_interact_with', [])),
        cannot_influence=', '.join(identity.get('action_boundaries', {}).get('cannot_influence', [])),
        plausibility_rules=[f"{i+1}. {rule}" for i, rule in enumerate(plausibility_rules)],
        character_wiki_summary=wiki_summary,
        current_city=build_current_city_section(era_config, state),
        current_location=build_current_location_section(era_config, state),
    )