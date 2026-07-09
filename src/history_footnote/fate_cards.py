"""
fate_cards.py - 命运卡系统（v2.5）

设计动机：
- 让玩家感知"命运"的存在（不只是 LLM 自由发挥）
- 增加重玩价值（每次开局抽 5 张不同的卡）
- 把"随机"显式化（玩家知道为什么发生这些事）
- 用 Python random 而非 LLM（可控 + 可重放）

机制：
- 开局从 30+ 张命运卡中抽 5 张给玩家
- 每回合玩家可选 0-1 张命运卡触发效果
- 命运卡效果：用 Python 状态变化（cash/debt/AP/location unlock）
- 已用过的卡失效（避免滥用）
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from history_footnote.random_utils import get_rng


# ============ 命运卡定义 ============

@dataclass
class FateCard:
    """一张命运卡"""
    id: str
    name: str
    icon: str                # emoji
    color: str               # 主题色
    description: str         # 短描述
    effect_type: str         # effect 类别
    effect_params: dict      # effect 参数


# 30+ 张命运卡（覆盖各种"命运走向"）
FATE_CARDS_POOL: list[FateCard] = [
    # === 银钱类 ===
    FateCard("debt_double", "债上加债", "💀", "#a52828",
             "开局债务翻倍（但你也可以更快地了解债务的可怕）",
             "modify_state", {"debt_delta": 1}),
    FateCard("windfall", "天降横财", "💰", "#6b8b5a",
             "意外获得 3 两银子（祖坟冒青烟？）",
             "modify_state", {"cash_delta": 3.0}),
    FateCard("rice_lost", "米缸见底", "🍚", "#8b6f47",
             "开局米减半，更紧迫",
             "modify_state", {"rice_delta": -3}),
    FateCard("price_drop", "丝价暴跌", "📉", "#a5703a",
             "开局丝价 -20%，卖素缎更不值钱",
             "modify_state", {"silk_price_delta": -0.2}),
    # === 关系类 ===
    FateCard("shen_loves_you", "沈氏倾心", "❤️", "#a52828",
             "沈氏对你更温柔，初始亲和 +30",
             "modify_npc", {"npc": "沈氏", "affinity_delta": 30}),
    FateCard("wang_distrust", "王牙人警觉", "🐍", "#4a4a4a",
             "王牙人对你戒备，初始亲和 -20",
             "modify_npc", {"npc": "王牙人", "affinity_delta": -20}),
    FateCard("zhou_secret", "周大娘秘闻", "🤫", "#7a5a8b",
             "周大娘藏了一个秘密（你知道后有后续）",
             "unlock_event", {"event_id": "zhou_secret"}),
    FateCard("li_friend", "李秀才青睐", "📚", "#5a7a8b",
             "李秀才对阿宝格外关照，束脩可能减免",
             "unlock_event", {"event_id": "li_discount"}),
    # === 地点解锁类 ===
    FateCard("dyeing_path", "染坊有路", "🎨", "#7a5a8b",
             "染坊在第 1 回合就对你浮现（不用等 R3）",
             "unlock_heard", {"location": "dyeing_workshop"}),
    FateCard("hengsheng_door", "恒生典开门", "🏦", "#4a4a4a",
             "恒生典在 R1 就浮现（钱庄提前可用）",
             "unlock_heard", {"location": "hengsheng_pawn"}),
    FateCard("cangqiao_shortcut", "仓桥捷径", "🌉", "#5a7a8b",
             "仓桥米行 R1 浮现（米价你更早掌握）",
             "unlock_heard", {"location": "cangqiao_grain"}),
    FateCard("school_known", "县学传闻", "🏫", "#7a5a8b",
             "县学在 R1 浮现（阿宝的学堂你提前知道）",
             "unlock_heard", {"location": "county_school"}),
    # === 行动点类 ===
    FateCard("vigor", "精力充沛", "⚡", "#b8860b",
             "开局行动点 +1（你这月能多做 1 件事）",
             "modify_state", {"ap_delta": 1.0}),
    FateCard("illness", "身体微恙", "🤒", "#4a4a4a",
             "开局行动点 -1（你得省着花）",
             "modify_state", {"ap_delta": -1.0}),
    # === 时间类 ===
    FateCard("time_slow", "时光悠悠", "⏳", "#5a7a8b",
             "时间流速变慢，每回合 +1 个回合机会",
             "modify_state", {"round_bonus": 1}),
    FateCard("time_fast", "白驹过隙", "⚡", "#a5703a",
             "时间紧迫，每回合 -0.5 行动点（压力更大）",
             "modify_state", {"ap_delta": -0.5}),
    # === 路遇类 ===
    FateCard("warm_encounters", "热络街头", "👋", "#6b8b5a",
             "路遇概率 +50%（街坊更愿意跟你打招呼）",
             "modify_encounter", {"prob_multiplier": 1.5}),
    FateCard("cold_encounters", "冷面相逢", "🥶", "#4a4a4a",
             "路遇概率 -50%（没人搭理你）",
             "modify_encounter", {"prob_multiplier": 0.5}),
    # === 声誉类 ===
    FateCard("renowned", "小镇名流", "🌟", "#b8860b",
             "声望 +2，NPC 更尊重你",
             "modify_state", {"reputation_delta": 2}),
    FateCard("notorious", "穷名远扬", "💸", "#4a4a4a",
             "声望 -2，NPC 看不起你",
             "modify_state", {"reputation_delta": -2}),
    # === 技能/特殊 ===
    FateCard("lucky_star", "吉星高照", "✨", "#b8860b",
             "未来 3 回合所有概率检定 +10%",
             "apply_buff", {"buff": "lucky", "duration": 3}),
    FateCard("cloud_of_doom", "乌云压顶", "☁️", "#4a4a4a",
             "未来 3 回合所有概率检定 -10%",
             "apply_buff", {"buff": "unlucky", "duration": 3}),
    FateCard("old_friend", "故人重逢", "🤝", "#5a7a8b",
             "随机浮现一个 L2 地点（命运的安排）",
             "unlock_heard", {"location_random_l2": True}),
    FateCard("secret_room", "密室传闻", "🗝️", "#7a5a8b",
             "县学提前浮现（剧情更复杂）",
             "unlock_heard", {"location": "county_school"}),
    FateCard("harvest_fest", "秋收节", "🌾", "#6b8b5a",
             "开局长辈送礼，米 +2 + 1 两银子",
             "modify_state", {"rice_delta": 2, "cash_delta": 1.0}),
    FateCard("winter_cold", "腊月寒", "❄️", "#5a7a8b",
             "开局米消耗 +1（冬天更饿）",
             "modify_state", {"rice_consumption_delta": 1}),
    FateCard("merchant_arrives", "行商到", "🛍️", "#b8860b",
             "染坊和恒生典都提前浮现（商业兴盛）",
             "unlock_heard", {"location": "dyeing_workshop"}),
    FateCard("famine_year", "凶年", "😭", "#4a4a4a",
             "米价 +50%，所有地点米都贵",
             "modify_state", {"rice_price_multiplier": 1.5}),
    FateCard("scholar_meeting", "士子游", "👨‍🎓", "#5a7a8b",
             "李秀才对阿宝额外关注（束脩可能减免）",
             "unlock_event", {"event_id": "li_discount"}),
    FateCard("wife_sick", "沈氏微恙", "🤒", "#a52828",
             "沈氏这月会病 1 次（额外照顾她）",
             "unlock_event", {"event_id": "shen_illness"}),
    FateCard("ah_bao_gift", "阿宝天资", "📖", "#5a7a8b",
             "阿宝这月学有小成（束脩 -30%）",
             "modify_state", {"tuition_discount": 0.3}),
    FateCard("neighbor_help", "邻里援手", "🤝", "#6b8b5a",
             "周大娘主动借 1 两银子（亲密度提升）",
             "modify_state", {"cash_delta": 1.0}),
]


# ============ 抽卡 + 应用 ============

def draw_fate_cards(session_id: str | None = None, n: int = 5) -> list[FateCard]:
    """
    从池中抽 n 张命运卡（用 session seed，可重放）

    Returns:
        抽中的命运卡列表（无重复）
    """
    rng = get_rng(session_id)
    pool = list(FATE_CARDS_POOL)
    n = min(n, len(pool))
    return rng.sample(pool, n)


def apply_fate_card(card: FateCard, game_state) -> list[str]:
    """
    应用命运卡效果到 game state

    Returns:
        应用结果消息列表（用于 UI 显示）
    """
    messages: list[str] = []
    effect = card.effect_type
    params = card.effect_params

    if effect == "modify_state":
        for k, v in params.items():
            if k == "cash_delta":
                game_state.cash = max(0, float(getattr(game_state, "cash", 0)) + v)
                messages.append(f"银两 {v:+.2f}（现 {game_state.cash:.2f}）")
            elif k == "debt_delta":
                game_state.debt = max(0, int(getattr(game_state, "debt", 0)) + v)
                messages.append(f"欠债 {v:+d}（现 {game_state.debt}）")
            elif k == "rice_delta":
                game_state.rice = max(0, int(getattr(game_state, "rice", 0)) + v)
                messages.append(f"米 {v:+d}（现 {game_state.rice}）")
            elif k == "ap_delta":
                game_state.action_points_current = max(0, float(getattr(game_state, "action_points_current", 0)) + v)
                messages.append(f"行动点 {v:+.1f}")
            elif k == "reputation_delta":
                # 尝试设置 reputation，没有则 0
                rep = int(getattr(game_state, "reputation", 0) or 0)
                game_state.reputation = rep + v
                messages.append(f"声望 {v:+d}")
            elif k == "round_bonus":
                messages.append(f"回合 +{v}")
            elif k == "rice_consumption_delta":
                messages.append(f"米消耗 +{v}/月")
            elif k == "tuition_discount":
                messages.append(f"束脩 {int(v*100)}% 折扣")
            elif k == "rice_price_multiplier":
                messages.append(f"米价 ×{v}")
            elif k == "silk_price_delta":
                messages.append(f"丝价 {v*100:+.0f}%")

    elif effect == "modify_npc":
        npc_name = params.get("npc", "")
        affinity_delta = params.get("affinity_delta", 0)
        # 写入 npc_relations
        if not hasattr(game_state, 'npc_relations') or game_state.npc_relations is None:
            game_state.npc_relations = {}
        cur = int(game_state.npc_relations.get(npc_name, 0))
        game_state.npc_relations[npc_name] = cur + affinity_delta
        messages.append(f"{npc_name} 好感 {affinity_delta:+d}")

    elif effect == "unlock_event":
        event_id = params.get("event_id", "")
        if not hasattr(game_state, 'fate_event_flags') or game_state.fate_event_flags is None:
            game_state.fate_event_flags = []
        if event_id and event_id not in game_state.fate_event_flags:
            game_state.fate_event_flags.append(event_id)
        messages.append(f"事件解锁：{event_id}")

    elif effect == "unlock_heard":
        # 提前解锁 L2 地点
        loc = params.get("location")
        loc_random = params.get("location_random_l2", False)
        heard = list(getattr(game_state, "heard_locations", []) or [])
        if loc and loc not in heard:
            heard.append(loc)
            game_state.heard_locations = heard
            messages.append(f"提前听到：{loc}")
        elif loc_random:
            # 随机选一个 L2 地点
            l2_options = ["dyeing_workshop", "hengsheng_pawn", "cangqiao_grain"]
            rng = get_rng(game_state.session_id if hasattr(game_state, "session_id") else None)
            chosen = rng.choice(l2_options)
            heard = list(getattr(game_state, "heard_locations", []) or [])
            if chosen not in heard:
                heard.append(chosen)
                game_state.heard_locations = heard
                messages.append(f"命运的安排：听到 {chosen}")

    elif effect == "modify_encounter":
        # 修改路遇概率（在 location_service 里读此字段）
        multiplier = params.get("prob_multiplier", 1.0)
        if not hasattr(game_state, 'encounter_multiplier') or game_state.encounter_multiplier is None:
            game_state.encounter_multiplier = 1.0
        game_state.encounter_multiplier = float(game_state.encounter_multiplier) * multiplier
        messages.append(f"路遇概率 ×{multiplier}")

    elif effect == "apply_buff":
        buff = params.get("buff", "")
        duration = params.get("duration", 1)
        if not hasattr(game_state, 'active_buffs') or game_state.active_buffs is None:
            game_state.active_buffs = []
        game_state.active_buffs.append({"name": buff, "rounds_left": duration})
        messages.append(f"获得 buff：{buff}（{duration} 回合）")

    return messages


def get_active_fate_cards(game_state) -> list[dict]:
    """
    从 game state 读出当前可用的命运卡（手牌）

    Returns:
        命运卡 list（从 hand 字段读）
    """
    hand = getattr(game_state, 'fate_hand', []) or []
    return [c for c in hand]


__all__ = [
    "FateCard",
    "FATE_CARDS_POOL",
    "draw_fate_cards",
    "apply_fate_card",
    "get_active_fate_cards",
]
