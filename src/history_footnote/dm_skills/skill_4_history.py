"""🆕 v2.10.3 SKILL-4 史实锚定（原 dm_skills.py 第 589-683 行）

检查史实锚点 + 决定操作：铺垫 / 触发 / 应对 三层操作。
"""
from __future__ import annotations

from history_footnote.dm_skills.types import HistoricalAnchor


def skill_4_anchor_history(
    era_config: dict,
    state: dict,
    player_input: str,
) -> HistoricalAnchor | None:
    """SKILL-4 史实锚定：检查史实锚点 + 决定操作

    三层操作：
    - 铺垫：临近锚点 → 投放线索
    - 触发：到达日期 → 锐切（🆕 v1.7.29 立即标记）
    - 应对：事件后 → 多选项

    🆕 v1.7.29 修复塌房 6：
    - 触发时（current_round >= trigger_round）立刻把 anchor_id 加进
      state.triggered_events（in-place mutation）
    - 铺垫阶段（foreshadow）不标记（避免误锁）
    - 同一回合的多次"触发"也只标记一次（用 set 检测）
    """
    # ⚠️ Bug #1 修复：合并两个机制
    # 1. 优先用 world.pacing_anchors（v1.4.0 SKILL 专用）
    # 2. fallback 用 mechanics.historical_events（v1.0 旧机制，自动派生）
    # 3. 两者通过 anchor_id == event_id 关联
    custom_anchors = era_config.get("world", {}).get("pacing_anchors", []) or era_config.get("pacing_anchors", [])
    raw_events = era_config.get("mechanics", {}).get("historical_events", [])

    # 派生：从 historical_events 转成 pacing_anchors
    derived_anchors = []
    for ev in raw_events:
        ev_id = ev.get("event_id", "")
        # 如果 custom_anchors 已有同 id 配置，跳过（用 custom）
        if any(a.get("id") == ev_id for a in custom_anchors):
            continue
        # 派生
        derived_anchors.append({
            "id": ev_id,
            "trigger_round": ev.get("round", 0),
            "trigger_date": ev.get("date", ""),
            "description": ev.get("event_name", ""),
            "time_mode": "sharp_cut" if ev.get("scope") == "national" else "now_time",
            "foreshadowing_lead": "",
            "dm_instruction": f"按 {ev.get('description', '')} 推进",
            "derived_from": "historical_events",
        })

    anchors = custom_anchors + derived_anchors
    current_round = state.get("round_number", 1)

    # 🆕 v1.7.29: 用 set 去重，保证同一回合内多次"触发"只标记一次
    triggered_set = set(state.get("triggered_events", []))
    state.setdefault("triggered_events", list(triggered_set))  # 同步 state 中的 list

    for anchor in anchors:
        anchor_id = anchor.get("id", "")
        if not anchor_id:
            continue
        # 已经触发过
        if anchor_id in triggered_set:
            continue

        trigger_round = anchor.get("trigger_round", 0)
        foreshadow_round = anchor.get("foreshadow_round", trigger_round - 3)

        # 已到触发回合 → 锐切
        if current_round >= trigger_round:
            # 🆕 v1.7.29 修复塌房 6：立即标记
            triggered_set.add(anchor_id)
            state["triggered_events"] = list(triggered_set)
            return HistoricalAnchor(
                anchor_id=anchor_id,
                trigger_date=anchor.get("trigger_date", ""),
                description=anchor.get("description", ""),
                time_mode=anchor.get("time_mode", "now_time"),
                dm_instruction=anchor.get("dm_instruction", ""),
                triggered=True,      # 立即标记为已触发
            )

        # 临近锚点 → 铺垫阶段（不标记）
        if current_round >= foreshadow_round:
            return HistoricalAnchor(
                anchor_id=anchor_id,
                trigger_date=anchor.get("trigger_date", ""),
                description=anchor.get("description", ""),
                time_mode="now_time",
                foreshadowing_lead=anchor.get("foreshadowing_lead", ""),
                dm_instruction=f"铺垫：{anchor.get('foreshadowing_lead', '投放相关线索')}",
                triggered=False,
            )

    return None