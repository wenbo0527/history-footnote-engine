"""🆕 v2.10.1 W52 P1-2 followup: GameLoop 身份切换模块

把 GameLoop 类中 5 个身份切换方法拆出：
- inject_identity_switch_offers(loop) -> None
- handle_identity_decision(loop, accept) -> bool
- apply_identity_switch(loop, offer) -> None
- show_available_offers(loop) -> None
- set_pending_offer(loop, offer) -> None

GameLoop 类中保留同名方法作为 thin wrapper。

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-2 followup
"""
from __future__ import annotations


def filter_available_offers(era_config: dict, selected_identity: str) -> list[dict]:
    """根据 from_identity 过滤当前可用的 offer 列表"""
    offers = era_config.get("world", {}).get("identity_switch_offers", [])
    return [o for o in offers if o.get("from_identity") == selected_identity]


def inject_identity_switch_offers(loop) -> None:
    """把 identity_switch_offers 注入到 DM 的 LLM state_ref 中

    这样 DM 在每次 Tool 调用时都能感知到当前可用的 offer 选项。
    """
    available = filter_available_offers(loop.era_config, loop.selected_identity)
    if not available:
        return
    if hasattr(loop.dm, "llm") and hasattr(loop.dm.llm, "_state_ref_slot_ref"):
        current_ref = loop.dm.llm._state_ref_slot_ref[0]
        current_ref["identity_switch_offers"] = available


def apply_identity_switch(loop, offer: dict) -> None:
    """应用身份切换——更新 state、identity_config、DM Agent

    Args:
        offer: offer_identity_switch 的返回值
    """
    from history_footnote.game_memory import GameEvent

    to_identity = offer.get("to_identity")
    if not to_identity:
        print("[ERROR] offer 缺少 to_identity")
        return

    # 1. 更新 state
    old_identity = loop.selected_identity
    loop.state.selected_identity = to_identity
    # player_gender 不变（性别锁定）

    # 2. 更新 GameLoop 的 identity_config
    identities = loop.era_config.get("world", {}).get("player_identities", {})
    loop.selected_identity = to_identity
    loop.identity_config = identities.get(to_identity, {})

    # 3. 重新注入 offers（新身份可能有新 offer）
    inject_identity_switch_offers(loop)

    # 4. 记录到事件日志
    summary = f"身份切换：{old_identity} → {to_identity}（{offer.get('reason', '')}）"
    event = GameEvent(
        round=loop.state.round_number,
        type="identity_switch",
        summary=summary,
        metadata={
            "from": old_identity,
            "to": to_identity,
            "cost": offer.get("cost", ""),
            "benefit": offer.get("benefit", ""),
        },
    )
    loop.memory.save_event(event)

    # 5. 显示反馈
    to_label = loop.identity_config.get("label", to_identity)
    print(f"\n{'=' * 60}")
    print(f"🎭 身份已切换：{identities.get(old_identity, {}).get('label', old_identity)} → {to_label}")
    print(f"{'=' * 60}")
    new_role = loop.identity_config.get("role", "")
    new_desc = loop.identity_config.get("description", "")
    print(f"\n新身份：{new_role}")
    print(f"\n{new_desc[:200]}...")

    # 6. 清除 pending offer
    loop.pending_identity_offer = None


def handle_identity_decision(loop, accept: bool) -> bool:
    """处理 /accept 或 /declines

    DM 通过 Tool 发起的 offer 存在 loop.pending_identity_offer
    """
    if loop.pending_identity_offer is None:
        print("[INFO] 当前没有待处理的身份切换 offer")
        return True

    if accept:
        apply_identity_switch(loop, loop.pending_identity_offer)
    else:
        print(f"[INFO] 你拒绝了身份切换 offer：{loop.pending_identity_offer.get('to_label', '新身份')}")
        print("  继续当前身份的游戏。")
        loop.pending_identity_offer = None
    return True


def show_available_offers(loop) -> None:
    """显示所有可用的身份切换 offer（不依赖 DM）"""
    available = filter_available_offers(loop.era_config, loop.selected_identity)
    if not available:
        print("[INFO] 当前身份暂无可用的身份切换选项")
        return

    print(f"\n=== 当前身份可用的切换选项 ===\n")
    for i, o in enumerate(available, 1):
        print(f"  {i}. {o.get('id')}")
        print(f"     目标身份: {o.get('to_identity')}")
        cond = o.get("trigger_condition", {})
        cond_str = ", ".join(f"{k}={v}" for k, v in cond.items())
        print(f"     触发条件: {cond_str}")
        print(f"     代价: {o.get('cost_description', '')}")
        print(f"     收益: {o.get('benefit_description', '')}")
        print()


def set_pending_offer(loop, offer: dict) -> None:
    """设置待处理的 offer（DM Agent 通过 Tool 调用）"""
    if offer.get("offered"):
        loop.pending_identity_offer = offer
        print(f"\n{'─' * 60}")
        print(f"[OFFER] {offer.get('message', '身份切换')}")
        print(f"  目标: {offer.get('to_label', offer.get('to_identity'))}")
        print(f"  原因: {offer.get('reason', '')}")
        print(f"  代价: {offer.get('cost', '')}")
        print(f"  收益: {offer.get('benefit', '')}")
        print(f"\n  接受请输入 /accept")
        print(f"  拒绝请输入 /decline")
        print(f"{'─' * 60}\n")