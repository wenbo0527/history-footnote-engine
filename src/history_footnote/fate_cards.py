"""
fate_cards.py - 命运卡系统（v2.6 主动使用机制）

设计动机：
- v2.5 卡只在开局触发 → 玩家"用不到" → 没存在感
- v2.6 卡可**主动使用** + **应急弹出** → 战略资源

机制：
- 开局从 32 张命运卡中抽 5 张给玩家
- 玩家在自己回合可**主动使用**（immediate 卡）
- 关键时刻（失败/危机）系统**应急弹出**（emergency 卡）
- 新回合开始可使用**回合卡**（round_start 卡）
- 命运卡效果：Python 状态变化 + 持续 buff
- 已用过的卡失效（避免滥用）
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from history_footnote.random_utils import get_rng


# ============ 命运卡定义 ============

# 🆕 v2.6 use_type 分类：
# - "immediate"  : 玩家在自己回合主动点（最常用）
# - "round_start": 新回合开始时点（buff/AP 调整）
# - "emergency"  : 应急弹出（失败/危机时点）
# - "any"        : 三种 context 都能用

# 🆕 v2.6 use_constraints 字段：
# - min_round: 最少第几回合能用
# - context_required: list of allowed contexts
# - min_cash: 需要的 cash
# - min_affinity: {npc_name: min_value}
# - max_uses: 最多使用次数（默认 1）

# 🆕 v2.6 use_hint 字段：
# - 玩家提示"什么时候用效果最好"


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
    # 🆕 v2.6 主动使用字段
    use_type: str = "immediate"   # immediate / round_start / emergency / any
    use_constraints: dict = field(default_factory=dict)
    use_hint: str = ""           # 何时用最好


# ============ 32 张命运卡（v2.6 重新分类）============

# 分类规则：
# - 银钱/数值类：immediate（任何时候可用）
# - 关系类：immediate（任何时候可用）
# - 地点解锁类：immediate
# - 时间/AP 类：round_start（新回合开始时用）
# - 路遇/buff 类：emergency（关键时刻用）
# - 失败/危机：emergency

FATE_CARDS_POOL: list[FateCard] = [
    # ============ 银钱类 (immediate) ============
    FateCard("debt_double", "债上加债", "debt_double", "#a52828",
             "债务 +1（但你也可以更快地了解债务的可怕）",
             "modify_state", {"debt_delta": 1},
             use_type="immediate",
             use_hint="开局即用：债务立刻+1"),
    FateCard("windfall", "天降横财", "windfall", "#6b8b5a",
             "获得 3 两银子（祖坟冒青烟？）",
             "modify_state", {"cash_delta": 3.0},
             use_type="immediate",
             use_hint="现金不够时用：cash+3"),
    FateCard("rice_lost", "米缸见底", "rice_lost", "#8b6f47",
             "米 -3，更紧迫",
             "modify_state", {"rice_delta": -3},
             use_type="immediate",
             use_hint="开局即用：米-3"),
    FateCard("price_drop", "丝价暴跌", "price_drop", "#a5703a",
             "丝价 -20%，卖素缎更不值钱",
             "modify_state", {"silk_price_delta": -0.2},
             use_type="immediate",
             use_hint="开局即用：丝价-20%"),

    # ============ 关系类 (immediate) ============
    FateCard("shen_loves_you", "沈氏倾心", "shen_loves_you", "#a52828",
             "沈氏对你更温柔，亲和 +30",
             "modify_npc", {"npc": "沈氏", "affinity_delta": 30},
             use_type="immediate",
             use_hint="R1 沈氏质问时用：减少吵架概率"),
    FateCard("wang_distrust", "王牙人警觉", "wang_distrust", "#4a4a4a",
             "王牙人对你戒备，亲和 -20",
             "modify_npc", {"npc": "王牙人", "affinity_delta": -20},
             use_type="immediate",
             use_hint="开局即用：王牙人亲和-20"),
    FateCard("zhou_secret", "周大娘秘闻", "zhou_secret", "#7a5a8b",
             "周大娘藏了一个秘密（解锁后有后续）",
             "unlock_event", {"event_id": "zhou_secret"},
             use_type="immediate",
             use_hint="R1 周大娘叙旧时用：解锁隐藏事件"),
    FateCard("li_friend", "李秀才青睐", "li_friend", "#5a7a8b",
             "李秀才对阿宝格外关照",
             "unlock_event", {"event_id": "li_discount"},
             use_type="immediate",
             use_hint="R5+ 阿宝束脩时用：可能减免"),

    # ============ 地点解锁类 (immediate) ============
    FateCard("dyeing_path", "染坊有路", "dyeing_path", "#7a5a8b",
             "染坊提前浮现（不用等 R3）",
             "unlock_heard", {"location": "dyeing_workshop"},
             use_type="immediate",
             use_hint="R1 用：染坊在第 1 回合就浮现"),
    FateCard("hengsheng_door", "恒生典开门", "hengsheng_door", "#4a4a4a",
             "恒生典提前浮现（钱庄提前可用）",
             "unlock_heard", {"location": "hengsheng_pawn"},
             use_type="immediate",
             use_hint="现金<1 时用：钱庄可抵押"),
    FateCard("cangqiao_shortcut", "仓桥捷径", "cangqiao_shortcut", "#5a7a8b",
             "仓桥米行提前浮现",
             "unlock_heard", {"location": "cangqiao_grain"},
             use_type="immediate",
             use_hint="米<3 时用：米行浮现"),
    FateCard("school_known", "县学传闻", "school_known", "#7a5a8b",
             "县学提前浮现",
             "unlock_heard", {"location": "county_school"},
             use_type="immediate",
             use_hint="R3+ 阿宝出事时用：可去县学"),

    # ============ 时间/AP 类 (round_start) ============
    FateCard("vigor", "精力充沛", "vigor", "#b8860b",
             "行动点 +1（这月能多做 1 件事）",
             "modify_state", {"ap_delta": 1.0},
             use_type="round_start",
             use_hint="回合开始时用：AP+1.0"),
    FateCard("illness", "身体微恙", "illness", "#4a4a4a",
             "行动点 -1（得省着花）",
             "modify_state", {"ap_delta": -1.0},
             use_type="round_start",
             use_hint="回合开始时用：AP-1.0"),
    FateCard("time_slow", "时光悠悠", "time_slow", "#5a7a8b",
             "时间流速变慢，+1 回合机会",
             "modify_state", {"round_bonus": 1},
             use_type="round_start",
             use_hint="回合开始时用：+1 回合机会"),
    FateCard("time_fast", "白驹过隙", "time_fast", "#a5703a",
             "时间紧迫，每回合 -0.5 行动点",
             "modify_state", {"ap_delta": -0.5},
             use_type="round_start",
             use_hint="回合开始时用：AP-0.5"),

    # ============ 应急/buff 类 (emergency) ============
    FateCard("lucky_star", "吉星高照", "lucky_star", "#b8860b",
             "未来 3 回合所有概率检定 +10%",
             "apply_buff", {"buff": "lucky", "duration": 3},
             use_type="emergency",
             use_hint="硬闯县衙/借贷前用：3 回合内所有检定+10%"),
    FateCard("cloud_of_doom", "乌云压顶", "cloud_of_doom", "#4a4a4a",
             "未来 3 回合所有概率检定 -10%",
             "apply_buff", {"buff": "unlucky", "duration": 3},
             use_type="emergency",
             use_hint="敌方 buff，hard mode 玩家用"),
    FateCard("warm_encounters", "热络街头", "warm_encounters", "#6b8b5a",
             "路遇概率 +50%（街坊更愿意打招呼）",
             "modify_encounter", {"prob_multiplier": 1.5},
             use_type="emergency",
             use_hint="R3+ 找不到 NPC 时用：路遇概率×1.5"),
    FateCard("cold_encounters", "冷面相逢", "cold_encounters", "#4a4a4a",
             "路遇概率 -50%",
             "modify_encounter", {"prob_multiplier": 0.5},
             use_type="emergency",
             use_hint="想安静过日子时用：路遇概率×0.5"),

    # ============ 应急/失败减伤 (emergency) ============
    FateCard("renowned", "小镇名流", "renowned", "#b8860b",
             "声望 +2，NPC 更尊重你",
             "modify_state", {"reputation_delta": 2},
             use_type="immediate",
             use_hint="去县衙/借债时用：声望+2 降低刁难"),
    FateCard("notorious", "穷名远扬", "notorious", "#4a4a4a",
             "声望 -2，NPC 看不起你",
             "modify_state", {"reputation_delta": -2},
             use_type="immediate",
             use_hint="开局即用：声望-2"),
    FateCard("old_friend", "故人重逢", "old_friend", "#5a7a8b",
             "随机浮现一个 L2 地点（命运的安排）",
             "unlock_heard", {"location_random_l2": True},
             use_type="immediate",
             use_hint="不知道去哪时用：浮现一个 L2"),
    FateCard("secret_room", "密室传闻", "secret_room", "#7a5a8b",
             "县学提前浮现",
             "unlock_heard", {"location": "county_school"},
             use_type="immediate",
             use_hint="阿宝出事时用：去县学找李秀才"),
    FateCard("harvest_fest", "秋收节", "harvest_fest", "#6b8b5a",
             "长辈送礼：米 +2 + 1 两银子",
             "modify_state", {"rice_delta": 2, "cash_delta": 1.0},
             use_type="immediate",
             use_hint="米<3 时用：米+2, 银+1"),
    FateCard("winter_cold", "腊月寒", "winter_cold", "#5a7a8b",
             "米消耗 +1/月",
             "modify_state", {"rice_consumption_delta": 1},
             use_type="immediate",
             use_hint="开局即用：米消耗+1"),
    FateCard("merchant_arrives", "行商到", "merchant_arrives", "#b8860b",
             "染坊和恒生典都提前浮现",
             "unlock_heard", {"location": "dyeing_workshop"},
             use_type="immediate",
             use_hint="R1 用：商业兴盛"),
    FateCard("famine_year", "凶年", "famine_year", "#4a4a4a",
             "米价 +50%",
             "modify_state", {"rice_price_multiplier": 1.5},
             use_type="immediate",
             use_hint="开局即用：米价×1.5"),
    FateCard("scholar_meeting", "士子游", "scholar_meeting", "#5a7a8b",
             "李秀才对阿宝额外关注",
             "unlock_event", {"event_id": "li_discount"},
             use_type="immediate",
             use_hint="R3+ 阿宝束脩时用：减免"),
    FateCard("wife_sick", "沈氏微恙", "wife_sick", "#a52828",
             "沈氏这月会病 1 次",
             "unlock_event", {"event_id": "shen_illness"},
             use_type="immediate",
             use_hint="沈氏健康事件触发"),
    FateCard("ah_bao_gift", "阿宝天资", "ah_bao_gift", "#5a7a8b",
             "阿宝这月学有小成（束脩 -30%）",
             "modify_state", {"tuition_discount": 0.3},
             use_type="immediate",
             use_hint="R3+ 阿宝束脩时用：30% 折扣"),
    FateCard("neighbor_help", "邻里援手", "neighbor_help", "#6b8b5a",
             "周大娘主动借 1 两银子",
             "modify_state", {"cash_delta": 1.0},
             use_type="immediate",
             use_hint="现金<1 时用：周大娘+1两"),

    # ============ 🆕 v2.6 新增：纯主动卡（之前没有）============
    # 这些是"真正需要主动使用"的卡
    FateCard("shield", "护身符", "shield", "#5a7a8b",
             "本回合所有失败减半（cash-2 后使用）",
             "apply_shield", {"duration": 1, "failure_reduction": 0.5, "cost": 2.0},
             use_type="emergency",
             use_constraints={"min_cash": 2.0},
             use_hint="危机时刻用：本回合所有失败代价减半（需 2 两）"),
    FateCard("second_chance", "再试一次", "second_chance", "#b8860b",
             "失败时可重投 1 次（需 R3 之后）",
             "apply_buff", {"buff": "second_chance", "duration": 99},
             use_type="emergency",
             use_constraints={"min_round": 3},
             use_hint="硬闯/借钱失败时用：自动重试 1 次"),
    FateCard("pause_time", "时光凝滞", "pause_time", "#7a5a8b",
             "本回合时间凝滞，可多做 1 个动作",
             "modify_state", {"ap_delta": 0.5},
             use_type="round_start",
             use_constraints={"min_round": 2},
             use_hint="回合开始时用：AP+0.5"),
    FateCard("persuasion", "三寸不烂", "persuasion", "#5a7a8b",
             "本回合与 NPC 交涉时亲和+15",
             "apply_buff", {"buff": "persuasion", "duration": 1, "value": 15},
             use_type="round_start",
             use_constraints={"min_round": 1},
             use_hint="回合开始时用：本回合所有 NPC 亲和+15"),
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


def can_use_card(card: dict, state, context: str = "immediate") -> tuple[bool, str]:
    """
    检查卡是否可使用（v2.6 新增）

    Args:
        card: 卡数据（dict）
        state: game state
        context: "immediate" / "round_start" / "emergency"

    Returns:
        (can_use, reason_if_not)
    """
    # 已用过
    if card.get("used"):
        return False, "已使用过"

    # use_type 检查
    use_type = card.get("use_type", "immediate")
    if use_type != "any" and use_type != context:
        if context == "immediate" and use_type != "immediate":
            return False, f"该卡为 {use_type} 类型，不能立即使用"
        if context == "round_start" and use_type not in ("round_start", "any"):
            return False, "需在回合开始时使用"
        if context == "emergency" and use_type not in ("emergency", "any"):
            return False, "需在应急时使用"

    # use_constraints 检查
    constraints = card.get("use_constraints") or {}

    # 1. 回合数
    min_round = constraints.get("min_round", 0)
    cur_round = getattr(state, "round_number", 0)
    if cur_round < min_round:
        return False, f"R{min_round} 后才能用"

    # 2. cash
    min_cash = constraints.get("min_cash", 0)
    cur_cash = float(getattr(state, "cash", 0) or 0)
    if cur_cash < min_cash:
        return False, f"需 {min_cash} 两银子（现 {cur_cash:.1f}）"

    # 3. affinity
    min_aff = constraints.get("min_affinity", {})
    npc_relations = getattr(state, "npc_relations", {}) or {}
    for npc, min_val in min_aff.items():
        cur_aff = int(npc_relations.get(npc, 0))
        if cur_aff < min_val:
            return False, f"需 {npc} 好感 {min_val}+（现 {cur_aff}）"

    return True, ""


def apply_fate_card(card: FateCard, game_state, context: str = "immediate") -> tuple[list[str], bool]:
    """
    应用命运卡效果到 game state（v2.6 升级：返回 reason_if_not）

    Returns:
        (messages, success)
    """
    # 转成 dict 来用 can_use_card
    card_dict = {
        "id": card.id, "name": card.name, "use_type": card.use_type,
        "use_constraints": card.use_constraints, "used": False,
    }
    can, reason = can_use_card(card_dict, game_state, context)
    if not can:
        return [f"❌ {reason}"], False

    messages: list[str] = []
    effect = card.effect_type
    params = card.effect_params

    if effect == "modify_state":
        for k, v in params.items():
            if k == "cash_delta":
                old = float(getattr(game_state, "cash", 0))
                game_state.cash = max(0, old + v)
                messages.append(f"银两 {v:+.2f}（现 {game_state.cash:.2f}）")
            elif k == "debt_delta":
                old = int(getattr(game_state, "debt", 0))
                game_state.debt = max(0, old + v)
                messages.append(f"欠债 {v:+d}（现 {game_state.debt}）")
            elif k == "rice_delta":
                old = int(getattr(game_state, "rice", 0))
                game_state.rice = max(0, old + v)
                messages.append(f"米 {v:+d}（现 {game_state.rice}）")
            elif k == "ap_delta":
                old = float(getattr(game_state, "action_points_current", 0))
                game_state.action_points_current = max(0, old + v)
                messages.append(f"行动点 {v:+.1f}")
            elif k == "reputation_delta":
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
        loc = params.get("location")
        loc_random = params.get("location_random_l2", False)
        heard = list(getattr(game_state, "heard_locations", []) or [])
        if loc and loc not in heard:
            heard.append(loc)
            game_state.heard_locations = heard
            messages.append(f"提前听到：{loc}")
        elif loc_random:
            l2_options = ["dyeing_workshop", "hengsheng_pawn", "cangqiao_grain"]
            rng = get_rng(game_state.session_id if hasattr(game_state, "session_id") else None)
            chosen = rng.choice(l2_options)
            heard = list(getattr(game_state, "heard_locations", []) or [])
            if chosen not in heard:
                heard.append(chosen)
                game_state.heard_locations = heard
                messages.append(f"命运的安排：听到 {chosen}")

    elif effect == "modify_encounter":
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
        # 移除同名旧 buff
        game_state.active_buffs = [
            b for b in game_state.active_buffs if b.get("name") != buff
        ]
        game_state.active_buffs.append({
            "name": buff,
            "rounds_left": duration,
            "params": params,
        })
        messages.append(f"获得 buff：{buff}（{duration} 回合）")

    elif effect == "apply_shield":
        # 🆕 v2.6 护盾效果
        duration = params.get("duration", 1)
        reduction = params.get("failure_reduction", 0.5)
        cost = params.get("cost", 0)
        if cost > 0:
            game_state.cash = max(0, float(getattr(game_state, "cash", 0)) - cost)
            messages.append(f"护盾消耗 {cost:.1f} 两")
        if not hasattr(game_state, 'active_buffs') or game_state.active_buffs is None:
            game_state.active_buffs = []
        game_state.active_buffs.append({
            "name": "shield",
            "rounds_left": duration,
            "params": {"failure_reduction": reduction},
        })
        messages.append(f"本回合护盾：失败代价 -{int(reduction*100)}%")

    return messages, True


def get_active_fate_cards(game_state) -> list[dict]:
    """
    从 game state 读出当前可用的命运卡（手牌）

    Returns:
        命运卡 list（从 hand 字段读）
    """
    hand = getattr(game_state, 'fate_hand', []) or []
    return [c for c in hand]


# ============ 应急检查 ============

# 应急弹出的触发条件（规则化判断）
EMERGENCY_TRIGGERS = {
    "cash_critical": lambda s: float(getattr(s, "cash", 0) or 0) < 1.0,
    "debt_danger": lambda s: int(getattr(s, "debt", 0) or 0) >= 2,
    "low_health": lambda s: int(getattr(s, "rice", 0) or 0) < 1,
    "fate_doom": lambda s: any(
        b.get("name") == "unlucky" for b in (getattr(s, "active_buffs", []) or [])
    ),
    "hard_choice": lambda s: int(getattr(s, "round_number", 0)) >= 5 and float(getattr(s, "cash", 0) or 0) < 3,
}


def check_emergency_situation(state) -> tuple[bool, str]:
    """
    检查当前是否处于应急状态

    Returns:
        (is_emergency, trigger_name)
    """
    for trigger_name, check in EMERGENCY_TRIGGERS.items():
        try:
            if check(state):
                return True, trigger_name
        except Exception:
            continue
    return False, ""


def get_emergency_cards(state) -> list[dict]:
    """
    获取当前可用的应急卡（自动满足 use_type=emergency 且未用）

    Returns:
        应急卡 list（每张含 can_use / reason）
    """
    hand = list(getattr(state, "fate_hand", []) or [])
    result = []
    for card in hand:
        if card.get("used"):
            continue
        use_type = card.get("use_type", "immediate")
        if use_type not in ("emergency", "any"):
            continue
        can, reason = can_use_card(card, state, "emergency")
        if can:
            card_copy = dict(card)
            card_copy["_can_use"] = True
            card_copy["_reason"] = ""
            result.append(card_copy)
    return result


def get_immediate_cards(state) -> list[dict]:
    """获取所有可立即使用的卡"""
    hand = list(getattr(state, "fate_hand", []) or [])
    result = []
    for card in hand:
        if card.get("used"):
            continue
        can, reason = can_use_card(card, state, "immediate")
        if can:
            card_copy = dict(card)
            card_copy["_can_use"] = True
            card_copy["_reason"] = ""
            result.append(card_copy)
    return result


__all__ = [
    "FateCard",
    "FATE_CARDS_POOL",
    "draw_fate_cards",
    "can_use_card",
    "apply_fate_card",
    "get_active_fate_cards",
    "check_emergency_situation",
    "get_emergency_cards",
    "get_immediate_cards",
    "EMERGENCY_TRIGGERS",
]
