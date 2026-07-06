"""🆕 v1.7.30 月度结算引擎（Settlement）

每 N 回合（默认 3 回合 = 1 月）触发一次月度结算：
1. monthly_burn —— 玩家月支出
2. deposit_interest —— 存款月息 0.3%
3. debt_interest —— 欠债月息 1.5%
4. workshop_rent —— 4 城市铺面租金累加
5. rice_consumption —— 玩家 + 同城家人 粮食消耗

所有结算统一调 `state.apply_financial_change()`，自动入 financial_log。

设计文档：docs/architecture/EventId规范.md §月度结算
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


# 月度结算默认触发间隔（3 回合 = 1 月）
DEFAULT_MONTHLY_ROUNDS = 3

# 利率（万历年间参考值）
DEPOSIT_MONTHLY_RATE = 0.003   # 存款月息 0.3%（年化 3.6%）
DEBT_MONTHLY_RATE = 0.015      # 欠债月息 1.5%（年化 18%——高利贷级别，参考万历私贷）
RICE_PER_PERSON_PER_MONTH = 0.3  # 每人每月 0.3 石


@dataclass
class SettlementRule:
    """单个结算规则"""
    name: str
    apply: Callable
    enabled: bool = True


def _settle_monthly_burn(state) -> Optional[dict]:
    """月基础开销（玩家维持生活的支出）"""
    if state.monthly_burn <= 0:
        return None
    return state.apply_financial_change(
        -state.monthly_burn, "monthly_burn",
        "月基础开销", state.current_city,
    )


def _settle_deposit_interest(state) -> Optional[dict]:
    """存款月息 0.3%"""
    if state.cash <= 0:
        return None
    interest = round(state.cash * DEPOSIT_MONTHLY_RATE, 4)
    if interest < 0.01:  # < 1 分钱不记录
        return None
    return state.apply_financial_change(
        interest, "deposit_interest",
        f"存款月息 {DEPOSIT_MONTHLY_RATE*100:.1f}%", state.current_city,
    )


def _settle_debt_interest(state) -> Optional[dict]:
    """欠债月息 1.5%（高利贷）"""
    if state.debt <= 0:
        return None
    interest = round(state.debt * DEBT_MONTHLY_RATE, 4)
    return state.apply_financial_change(
        -interest, "debt_interest",
        f"欠债月息 {DEBT_MONTHLY_RATE*100:.1f}%", state.current_city,
    )


def _settle_workshop_rent(state) -> Optional[dict]:
    """4 城市铺面/作坊租金（累加）"""
    total_rent = 0.0
    city_summary = []
    for city, props in state.city_properties.items():
        city_rent = sum(p.get("rent_per_month", 0) for p in props)
        if city_rent > 0:
            city_summary.append(f"{city}={city_rent}")
            total_rent += city_rent
    if total_rent <= 0:
        return None
    return state.apply_financial_change(
        total_rent, "workshop_rent",
        f"铺面租金（{', '.join(city_summary)}）", state.current_city,
    )


def _settle_rice_consumption(state) -> Optional[dict]:
    """存粮消耗：玩家 + 同城家人口粮"""
    if state.rice <= 0:
        return None
    # 同城家人（含自己）
    family_count = 1  # 玩家自己
    for m in state.family_members:
        if m.get("location") == state.current_city and m.get("alive", True):
            family_count += 1
    consumption = family_count * RICE_PER_PERSON_PER_MONTH
    if state.rice < consumption:
        # 存粮不足，吃光
        consumed = state.rice
        state.rice = 0
        entry = {
            "type": "rice_consumption",
            "date": state.current_date,
            "round": state.round_number,
            "amount": -consumed,
            "note": f"{family_count}人月粮（存粮不足）",
            "location": state.current_city,
        }
    else:
        state.rice -= consumption
        entry = {
            "type": "rice_consumption",
            "date": state.current_date,
            "round": state.round_number,
            "amount": -consumption,
            "note": f"{family_count}人月粮",
            "location": state.current_city,
        }
    # 统一入 financial_log（便于审计）
    state.financial_log.append(entry)
    return entry


# 默认规则集
DEFAULT_RULES = [
    SettlementRule(name="monthly_burn", apply=_settle_monthly_burn),
    SettlementRule(name="deposit_interest", apply=_settle_deposit_interest),
    SettlementRule(name="debt_interest", apply=_settle_debt_interest),
    SettlementRule(name="workshop_rent", apply=_settle_workshop_rent),
    SettlementRule(name="rice_consumption", apply=_settle_rice_consumption),
]


def settle_monthly(state, rules: list = None) -> list[dict]:
    """执行月度结算

    Args:
        state: GameState
        rules: 规则列表（默认 DEFAULT_RULES）

    Returns:
        结算日志（每条规则 1 条；规则未触发时为 None）
    """
    if rules is None:
        rules = DEFAULT_RULES
    log = []
    for rule in rules:
        if not rule.enabled:
            continue
        try:
            entry = rule.apply(state)
            if entry:
                log.append(entry)
        except Exception as e:
            # 单条规则失败不阻断其他规则
            log.append({
                "type": "error",
                "rule": rule.name,
                "error": str(e),
                "round": state.round_number,
            })
    return log


def should_settle(state, monthly_rounds: int = DEFAULT_MONTHLY_ROUNDS) -> bool:
    """判断本回合是否需要触发月度结算

    规则：每 N 回合结算一次。
    last_settle_round 存于 state._last_settle_round（默认 0 → 第 1 个 N 回合就触发）
    """
    last = getattr(state, "_last_settle_round", 0)
    return (state.round_number - last) >= monthly_rounds


def mark_settled(state) -> None:
    """标记本回合已结算（写入 _last_settle_round）"""
    state._last_settle_round = state.round_number


def format_settlement_narrative(log: list[dict]) -> str:
    """把结算日志格式化成 narrative 文案（玩家可见）"""
    if not log:
        return ""
    lines = ["📅 **月末结算**"]
    for entry in log:
        if entry.get("type") == "error":
            lines.append(f"  ⚠️  {entry['rule']} 结算失败：{entry['error']}")
            continue
        amount = entry.get("amount", 0)
        note = entry.get("note", "")
        type_ = entry.get("type", "")
        sign = "+" if amount > 0 else ""
        # 类型 → emoji
        type_emoji = {
            "monthly_burn": "📉",
            "deposit_interest": "💰",
            "debt_interest": "💸",
            "workshop_rent": "🏘️",
            "rice_consumption": "🍚",
        }.get(type_, "📌")
        lines.append(f"  {type_emoji} {sign}{amount:.2f} 两 · {note}")
    return "\n".join(lines)
