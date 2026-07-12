"""🆕 v2.10.1 W52 P1-2 PR#2: GameLoop 随机事件模块

把 GameLoop 中 2 个事件方法拆出：
- check_random_events(random_events, state, dice, scene) → list[dict]
- apply_event_effects(triggered_events, state) → list[str]

GameLoop 类中保留同名方法作为 thin wrapper。

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-2
"""
from __future__ import annotations

from typing import Any


def check_random_events(
    random_events: list[dict],
    state,
    dice,
    scene: str,
) -> list[dict]:
    """检查并触发随机事件

    Args:
        random_events: 随机事件定义列表
        state: GameState
        dice: Dice 工具（chance / weighted_choice / check）
        scene: 当前场景名

    Returns:
        触发的随机事件列表（包含 dice 结果、效果等）
    """
    triggered = []
    for event in random_events:
        cond = event.get("trigger_condition", {})

        # 场景匹配
        if cond.get("scene") and cond.get("scene") != scene:
            continue

        # 回合数
        if state.round_number < cond.get("min_round", 1):
            continue

        # 概率判定
        if not dice.chance(event.get("probability", 0)):
            continue

        # 触发：加权选一个 outcome
        outcomes = event.get("outcomes", [])
        if not outcomes:
            continue

        chosen = dice.weighted_choice(outcomes)

        # 如果 outcome 需要 dice 判定
        if chosen.get("requires_dice"):
            dice_expr = chosen.get("dice", "d20")
            dc = chosen.get("dc", 10)
            check_result = dice.check(dc, dice_expr, purpose=chosen.get("description", ""))
            chosen["dice_result"] = check_result

        triggered.append({
            "event_id": event["id"],
            "outcome": chosen,
        })

    return triggered


def apply_event_effects(
    triggered_events: list[dict],
    state,
) -> list[str]:
    """应用随机事件的效果（更新 state.variables）

    Returns:
        事件效果描述列表（用于打印给玩家）
    """
    messages = []
    for ev in triggered_events:
        outcome = ev["outcome"]
        effect = outcome.get("effect", {})
        for var_key, delta in effect.items():
            # 解析 "+0.5" "-0.3"
            if isinstance(delta, str):
                if delta.startswith("+"):
                    delta = float(delta[1:])
                elif delta.startswith("-"):
                    delta = -float(delta[1:])
            if var_key in state.variables:
                state.variables[var_key] += delta
                messages.append(f"  [随机事件效果] {var_key} {delta:+.1f}")

        # 如果是 dice 判定
        if "dice_result" in outcome:
            dice_res = outcome["dice_result"]
            roll = dice_res["result"]
            crit = " 💥大成功" if roll.is_critical_success else (" 💀大失败" if roll.is_critical_fail else "")
            if dice_res["success"]:
                messages.append(f"  [判定] {roll}{crit} vs DC{dice_res['dc']} → 成功！{outcome.get('success', '')}")
            else:
                messages.append(f"  [判定] {roll}{crit} vs DC{dice_res['dc']} → 失败。{outcome.get('fail', '')}")

    return messages