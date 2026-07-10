"""v2.8.0 段五 W16 PlateEngine（板块格局引擎）

设计目标：
- 维护 tension_fields（板块张力场）
- 处理 transmission_rules（传导规则）
- 推进 shift_events 状态变化
- 给 PathSwitcher 触发器 3 喂数据

约束：
- 0 LLM 调用
- 纯规则引擎
- 嵌套 dataclass PlateState

核心流程（每回合）：
1. process_pending_transmissions()：处理到期的待传导事件
2. tick(rounds=1)：板块格局自然衰减（向 baseline 回归）
3. detect_shift_events()：检测张力突破阈值的板块
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from history_footnote.chapter.plates import (
    Plate,
    PlateRegistry,
    PlateState,
    PlateStatus,
    TransmissionRule,
)

_LOG = logging.getLogger("history_footnote.chapter.plate_engine")


# 阈值
SHIFT_THRESHOLD = 0.7         # 张力 > 0.7 触发 shift_event
COLLAPSE_THRESHOLD = 0.9      # 张力 > 0.9 触发 collapse
TENSION_DECAY_PER_ROUND = 0.01  # 每回合张力自然衰减（向 baseline 回归）


@dataclass
class PlateShiftEvent:
    """板块格局变动事件"""
    plate_id: str
    old_tension: float
    new_tension: float
    old_status: str
    new_status: str
    round: int
    reason: str = ""


class PlateEngine:
    """板块格局引擎（v2.8.0 段五 W16）

    用法：
        engine = PlateEngine(state, registry)
        engine.tick(current_round=5)            # 推进一回合
        events = engine.detect_shift_events()    # 检测变动
    """

    def __init__(self, state, plate_registry: PlateRegistry):
        self.state = state
        self.registry = plate_registry

    # ============= 主入口 =============

    def tick(self, current_round: int) -> list[PlateShiftEvent]:
        """推进一回合：处理传导 + 自然衰减

        Returns:
            板块格局变动事件列表
        """
        events: list[PlateShiftEvent] = []

        # 1. 处理到期的待传导事件
        transmission_events = self._process_pending_transmissions(current_round)
        events.extend(transmission_events)

        # 2. 检测张力变化（自动生成 shift events）
        shift_events = self._detect_shift_events(current_round)
        events.extend(shift_events)

        # 3. 自然衰减（每回合向 baseline 回归 0.01）
        self._decay_to_baseline()

        return events

    # ============= 处理传导 =============

    def _process_pending_transmissions(self, current_round: int) -> list[PlateShiftEvent]:
        """处理到期的待传导事件"""
        events: list[PlateShiftEvent] = []
        ps = self.state.plate_state
        if not ps:
            return events

        # 找出到期的（round <= current_round）
        to_process = [t for t in ps.pending_transmissions if t.get("round", 0) <= current_round]
        for t in to_process:
            from_p = t.get("from", "")
            to_p = t.get("to", "")
            factor = t.get("factor", 0.3)
            if not from_p or not to_p:
                continue
            # 传导：to 张力 += from 张力 * factor
            from_tension = ps.get_tension(from_p)
            to_tension = ps.get_tension(to_p)
            old_to_tension = to_tension
            new_to_tension = min(1.0, to_tension + from_tension * factor)

            # 记录 old/new status
            old_status = PlateStatus.from_tension(old_to_tension).value
            new_status = PlateStatus.from_tension(new_to_tension).value

            ps.set_tension(to_p, new_to_tension)
            events.append(PlateShiftEvent(
                plate_id=to_p,
                old_tension=old_to_tension,
                new_tension=new_to_tension,
                old_status=old_status,
                new_status=new_status,
                round=current_round,
                reason=f"传导 from {from_p} (factor={factor})",
            ))
            _LOG.info(
                "板块传导: %s tension %.2f → %.2f (status: %s → %s)",
                to_p, old_to_tension, new_to_tension, old_status, new_status,
            )

        # 清空已处理的
        ps.pending_transmissions = [
            t for t in ps.pending_transmissions if t.get("round", 0) > current_round
        ]
        return events

    def add_transmission(self, from_plate: str, to_plate: str, current_round: int) -> None:
        """登记一次板块传导（按 transmission_rules 查 factor + delay_rounds）"""
        ps = self.state.plate_state
        if not ps:
            return

        # 查 transmission_rules
        for rule in self.registry.get_transmission_rules_from(from_plate):
            if rule.to_plate == to_plate:
                deliver_round = current_round + rule.delay_rounds
                ps.add_pending_transmission(
                    from_p=from_plate,
                    to_p=to_plate,
                    factor=rule.factor,
                    round_num=deliver_round,
                )
                _LOG.info(
                    "登记传导: %s → %s (factor=%.2f, delay=%d, deliver_round=%d)",
                    from_plate, to_plate, rule.factor, rule.delay_rounds, deliver_round,
                )
                return

    # ============= 检测变动 =============

    def _detect_shift_events(self, current_round: int) -> list[PlateShiftEvent]:
        """检测张力突破阈值的板块"""
        events: list[PlateShiftEvent] = []
        ps = self.state.plate_state
        if not ps:
            return events

        for plate_id, tension in ps.tensions.items():
            if tension >= COLLAPSE_THRESHOLD:
                # 板块瓦解
                event = PlateShiftEvent(
                    plate_id=plate_id,
                    old_tension=tension,
                    new_tension=tension,
                    old_status=ps.get_status(plate_id),
                    new_status=PlateStatus.COLLAPSED.value,
                    round=current_round,
                    reason=f"张力 {tension:.2f} >= {COLLAPSE_THRESHOLD}，板块瓦解",
                )
                events.append(event)
                ps.add_shift_event({
                    "type": "collapse",
                    "plate_id": plate_id,
                    "tension": tension,
                    "round": current_round,
                })
            elif tension >= SHIFT_THRESHOLD:
                event = PlateShiftEvent(
                    plate_id=plate_id,
                    old_tension=tension,
                    new_tension=tension,
                    old_status=ps.get_status(plate_id),
                    new_status=PlateStatus.SHIFTING.value,
                    round=current_round,
                    reason=f"张力 {tension:.2f} >= {SHIFT_THRESHOLD}，板块格局变动",
                )
                events.append(event)
                ps.add_shift_event({
                    "type": "shift",
                    "plate_id": plate_id,
                    "tension": tension,
                    "round": current_round,
                })
        return events

    # ============= 自然衰减 =============

    def _decay_to_baseline(self) -> None:
        """每回合张力向 baseline 回归（TENSION_DECAY_PER_ROUND）"""
        ps = self.state.plate_state
        if not ps:
            return

        for plate_id, baseline in ps.equilibrium_baseline.items():
            current = ps.get_tension(plate_id)
            if abs(current - baseline) < 0.01:
                continue
            if current > baseline:
                new_tension = max(baseline, current - TENSION_DECAY_PER_ROUND)
            else:
                new_tension = min(baseline, current + TENSION_DECAY_PER_ROUND)
            ps.set_tension(plate_id, new_tension)

    # ============= 直接修改张力 =============

    def boost_tension(self, plate_id: str, amount: float, current_round: int) -> Optional[PlateShiftEvent]:
        """手动增加某板块张力（玩家行为或事件触发）

        Returns:
            PlateShiftEvent 如果张力突破阈值
        """
        ps = self.state.plate_state
        if not ps:
            return None
        old_tension = ps.get_tension(plate_id)
        new_tension = min(1.0, old_tension + amount)
        old_status = ps.get_status(plate_id)
        ps.set_tension(plate_id, new_tension)
        new_status = ps.get_status(plate_id)

        _LOG.info(
            "boost_tension: %s %.2f → %.2f (reason: %s)",
            plate_id, old_tension, new_tension, "manual",
        )

        if new_status != old_status:
            # 同步记录到 shift_events
            event_type = "collapse" if new_tension >= COLLAPSE_THRESHOLD else "shift"
            ps.add_shift_event({
                "type": event_type,
                "plate_id": plate_id,
                "tension": new_tension,
                "old_tension": old_tension,
                "round": current_round,
            })
            return PlateShiftEvent(
                plate_id=plate_id,
                old_tension=old_tension,
                new_tension=new_tension,
                old_status=old_status,
                new_status=new_status,
                round=current_round,
                reason=f"boost +{amount:.2f}",
            )
        return None

    def reduce_tension(self, plate_id: str, amount: float) -> None:
        """手动减少某板块张力"""
        ps = self.state.plate_state
        if not ps:
            return
        old = ps.get_tension(plate_id)
        new = max(0.0, old - amount)
        ps.set_tension(plate_id, new)

    # ============= 工具 =============

    def get_current_statuses(self) -> dict:
        """获取所有板块当前状态（dict 形式）"""
        ps = self.state.plate_state
        if not ps:
            return {}
        return {pid: ps.get_status(pid) for pid in ps.tensions}

    def get_shifting_plates(self) -> list[str]:
        """获取当前 shifting/collapsed 状态的板块（用于 PathSwitcher 触发器 3）"""
        ps = self.state.plate_state
        if not ps:
            return []
        return [
            pid for pid, status in ps.statuses.items()
            if status in (PlateStatus.SHIFTING.value, PlateStatus.COLLAPSED.value)
        ]
