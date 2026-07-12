"""🆕 v2.10.1 W52 P1-2 PR#3: GameLoop 存档/读档模块

把 GameLoop 中 3 个存档方法拆出：
- save_to_slot(slot, session, save_manager, state, memory) → None
- load_from_slot(slot, session, save_manager) → bool
- auto_save(session, save_manager, state, memory) → None

GameLoop 类中保留同名方法作为 thin wrapper。

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-2
"""
from __future__ import annotations


def save_to_slot(slot: str, session, save_manager, state, memory) -> None:
    """保存到指定 slot

    slot 支持：
    - "default" / 不传 → 存到 slot1（首次手动存档）
    - "1" / "2" / "3" → 存到 slot1/slot2/slot3
    - "auto" → 存到 auto（一般不手动）
    """
    if slot == "default":
        target = "slot1"
    elif slot in ("1", "slot1"):
        target = "slot1"
    elif slot in ("2", "slot2"):
        target = "slot2"
    elif slot in ("3", "slot3"):
        target = "slot3"
    elif slot == "auto":
        target = "auto"
    else:
        print(f"[ERROR] 非法slot名: {slot}（支持 1/2/3/auto）")
        return

    # 构造 state_data
    state_data = state.to_dict()
    # 同步 event_log
    state_data["event_log"] = [e.to_dict() for e in memory.events]
    # 摘要
    summary = f"第{state.round_number}回合 {state.current_date}"
    if state.event_log:
        summary += f" - {state.event_log[-1].get('summary', '')[:30]}"

    slot_info = save_manager.save_state(session, target, state_data, summary)
    print(f"[INFO] 已存档到 {target}（回合{slot_info.round_number} {slot_info.current_date}）")


def load_from_slot(slot: str, session, save_manager) -> bool:
    """从指定 slot 读档

    Returns:
        True = 成功读档（需要重启游戏循环）
        False = 失败
    """
    if slot in ("1", "slot1"):
        target = "slot1"
    elif slot in ("2", "slot2"):
        target = "slot2"
    elif slot in ("3", "slot3"):
        target = "slot3"
    elif slot in ("auto", "default"):
        target = "auto"
    else:
        print(f"[ERROR] 非法slot名: {slot}")
        return False

    if target not in session.slots:
        print(f"[ERROR] {target} 没有存档")
        return False

    loaded = save_manager.load_state(session, target)
    if not loaded:
        print(f"[ERROR] 读取{target}失败")
        return False

    print(f"[INFO] 从 {target} 读档成功（回合{loaded.get('round_number')} {loaded.get('current_date')}）")
    print("[INFO] 读档需要重启游戏，请在外部重新运行：")
    print(f"       python -m history_footnote load {session.session_id} --slot {target}")
    return True


def auto_save(session, save_manager, state, memory) -> None:
    """每回合自动存档到 auto.json"""
    state_data = state.to_dict()
    state_data["event_log"] = [e.to_dict() for e in memory.events]
    save_manager.save_state(
        session,
        "auto",
        state_data,
        summary=f"自动存档 - 回合{state.round_number}",
    )