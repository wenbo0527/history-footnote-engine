"""v2.8.0 段三 W12 PathSwitcher（4 触发器）

设计目标：
- 实现 4 个路径状态变化的触发器
- 每个触发器返回 PathEvent 列表（不直接修改 state）
- 段三 W13 由 Coordinator 调 apply_events 应用变更

4 触发器：
1. 选项触发：连续 3 次选择同一路径选项 → 切换主路径焦点
2. 解锁条件触发：locked_path 解锁条件满足 → 激活路径
3. 板块格局触发：plate_shift 事件 → 强制激活/锁定
4. 章节转化触发：新章节初始化时重排路径优先级

约束：
- 0 LLM 调用
- 纯函数式（输入 state + registry → 输出 PathEvent 列表）
- 不直接修改 state.path_state（应用由 Coordinator 负责）

PathEvent：
- type: SWITCH_MAIN / UNLOCK / LOCK / COMPLETE / REORDER
- path_id: str
- priority: int
- reason: str
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from history_footnote.chapter.paths import (
    NarrativePath,
    PathRegistry,
    PathState,
    PathStatus,
)

_LOG = logging.getLogger("history_footnote.chapter.path_switcher")


# 触发器阈值
OPTION_CONSECUTIVE_THRESHOLD = 3   # 连续 3 次同选项触发主路径切换
PATH_AFFINITY_SWITCH_THRESHOLD = 0.5  # 路径亲和度达到此值时升级为主路径


@dataclass
class PathEvent:
    """路径事件——触发器产出"""
    type: str  # SWITCH_MAIN / UNLOCK / LOCK / COMPLETE / REORDER
    path_id: str
    priority: int = 50
    reason: str = ""
    payload: dict = field(default_factory=dict)


class PathSwitcher:
    """路径切换触发器（v2.8.0 段三 W12）

    用法：
        switcher = PathSwitcher(state, registry)
        events = switcher.check()  # 返回 PathEvent 列表
        # Coordinator 在 W13 调 apply_events(events)
    """

    def __init__(self, state, path_registry: PathRegistry):
        self.state = state
        self.registry = path_registry

    def check(self) -> list[PathEvent]:
        """主入口：跑所有 4 个触发器，返回事件列表"""
        events: list[PathEvent] = []
        events.extend(self._check_option_trigger())
        events.extend(self._check_unlock_conditions())
        events.extend(self._check_plate_shifts())
        events.extend(self._check_chapter_transition())
        if events:
            _LOG.info("PathSwitcher 产出 %d 个事件", len(events))
        return events

    # ============= 触发器 1：选项触发 =============

    def _check_option_trigger(self) -> list[PathEvent]:
        """触发器 1：连续 N 次选择同一路径选项 → 切换主路径

        检测方式：state.recent_path_choices 记录最近选择的路径
        （该字段由段三 W13 协调器记录；W12 先用 state.recent_path_choices）
        """
        events: list[PathEvent] = []
        recent = getattr(self.state, "recent_path_choices", []) or []
        if len(recent) < OPTION_CONSECUTIVE_THRESHOLD:
            return events

        # 取最后 3 次选择
        last_n = recent[-OPTION_CONSECUTIVE_THRESHOLD:]
        if len(set(last_n)) != 1:
            return events  # 不全是同一路径

        target_path = last_n[0]
        ps = self.state.path_state
        if not ps:
            return events

        # 当前主路径不是 target → 触发切换
        if ps.main_path_focus == target_path:
            return events

        events.append(PathEvent(
            type="SWITCH_MAIN",
            path_id=target_path,
            priority=80,
            reason=f"连续 {OPTION_CONSECUTIVE_THRESHOLD} 次选择 {target_path}",
            payload={"trigger": "option_consecutive"},
        ))
        return events

    # ============= 触发器 2：解锁条件触发 =============

    def _check_unlock_conditions(self) -> list[PathEvent]:
        """触发器 2：locked_path 解锁条件满足 → 激活

        段三简化：unlock_condition 字段为字符串，常见值：
        - "always"：总是解锁
        - "value_threshold"：价值维度偏移超阈值（段三简化：只看是否非空）
        - "chapter_reached"：达到指定章节
        - 其他：视为不可解锁
        """
        events: list[PathEvent] = []
        ps = self.state.path_state
        if not ps:
            return events

        for path_id in list(ps.locked_paths):
            path = self.registry.get(path_id)
            if not path:
                continue
            if self._check_unlock_condition(path):
                events.append(PathEvent(
                    type="UNLOCK",
                    path_id=path_id,
                    priority=70,
                    reason=f"路径 {path_id} 解锁条件满足",
                    payload={"unlock_condition": path.unlock_condition},
                ))
        return events

    def _check_unlock_condition(self, path: NarrativePath) -> bool:
        """段三简化版：单条件判断"""
        cond = path.unlock_condition
        if cond == "always":
            return True
        if cond == "value_threshold":
            # 简化：价值维度有任一 > 0.5 偏移即解锁
            vd = getattr(self.state, "value_dimensions", {}) or {}
            for v in vd.values():
                try:
                    if abs(float(v)) > 0.5:
                        return True
                except (TypeError, ValueError):
                    continue
            return False
        if cond.startswith("chapter_reached:"):
            # 格式：chapter_reached:5
            try:
                required_chapter = int(cond.split(":", 1)[1])
                # 检查 chapter_history 是否有 >= required_chapter
                history = getattr(self.state.chapter_state, "chapter_history", []) or []
                completed = max([h.get("chapter", 0) for h in history], default=0)
                return completed >= required_chapter
            except (ValueError, IndexError):
                return False
        # 不可识别的条件 → 不解锁
        return False

    # ============= 触发器 3：板块格局触发（v2.8.0 段五 W17 完整实现）============

    def _check_plate_shifts(self) -> list[PathEvent]:
        """触发器 3：板块格局变化 → 路径被强制激活/锁定

        段五 W17 完整实现：
        1. 检测 state.plate_state.shift_events
        2. 板块 shifting/collapsed → 相关路径被强制激活
        3. 板块 stable → 相关路径降级为 dormant

        简化版：板块张力高 → 路径激活（板块更"需要"玩家介入）
        """
        events: list[PathEvent] = []
        ps = getattr(self.state, "plate_state", None)
        if ps is None:
            return events

        # 1. 找出 shifting/collapsed 板块
        shifting_plates = [
            pid for pid, status in ps.statuses.items()
            if status in ("shifting", "collapsed")
        ]

        if not shifting_plates:
            return events

        # 2. 遍历所有路径，看哪些路径的 plate_dependency 在 shifting 列表
        #    （plate_dependency 在 segments 三 W11 已定义）
        for path in self.registry.get_all():
            if not path.plate_dependency:
                continue
            # plate_dependency 可能是单个 plate_id 或 "central_plains,jiangnan"
            deps = [d.strip() for d in path.plate_dependency.split(",")]
            # 依赖板块中至少 1 个 shifting → 激活
            if any(dep in shifting_plates for dep in deps):
                if path.id in self.state.path_state.locked_paths:
                    # 板块需要 → 解锁
                    events.append(PathEvent(
                        type="UNLOCK",
                        path_id=path.id,
                        priority=85,  # 比选项触发的 80 更高
                        reason=f"依赖板块 {path.plate_dependency} shifting/collapsed",
                        payload={"trigger": "plate_shift"},
                    ))
            else:
                # 依赖板块未 shifting（如 stable）→ 路径可能降级
                # 简化：只对 main 路径做降级
                if path.type == "main" and path.id in self.state.path_state.active_paths:
                    # 路径依赖板块已稳定 → 降级为 dormant
                    events.append(PathEvent(
                        type="REORDER",
                        path_id=path.id,
                        priority=45,
                        reason=f"依赖板块 {path.plate_dependency} 已稳定",
                        payload={"new_status": "dormant", "trigger": "plate_stable"},
                    ))
        return events

    # ============= 触发器 4：章节转化触发 =============

    def _check_chapter_transition(self) -> list[PathEvent]:
        """触发器 4：新章节初始化时重排路径优先级

        检测方式：state.chapter_state.just_initialized 标记
        """
        events: list[PathEvent] = []
        cs = getattr(self.state, "chapter_state", None)
        if cs is None:
            return events
        if not getattr(cs, "just_initialized", False):
            return events

        # 当前章节适用路径 vs 玩家当前活跃路径 → 重排
        current_chapter = cs.current_chapter
        applicable = self.registry.get_applicable_to_chapter(current_chapter)
        ps = self.state.path_state
        if not ps:
            return events

        applicable_ids = {p.id for p in applicable}
        # 1. 不再适用的 active 路径 → 降级为 dormant
        for path_id in list(ps.active_paths):
            if path_id not in applicable_ids:
                events.append(PathEvent(
                    type="REORDER",
                    path_id=path_id,
                    priority=40,
                    reason=f"章节 {current_chapter} 不适用，降级为 dormant",
                    payload={"new_status": "dormant"},
                ))
        # 2. 适用但不在 active 的路径 → 升级为 active
        for path_id in applicable_ids:
            path = self.registry.get(path_id)
            if path and path_id not in ps.active_paths and path_id not in ps.completed_paths and path_id not in ps.dormant_paths:
                # 检查 unlock 条件
                if self._check_unlock_condition(path):
                    events.append(PathEvent(
                        type="REORDER",
                        path_id=path_id,
                        priority=40,
                        reason=f"章节 {current_chapter} 适用，激活",
                        payload={"new_status": "active"},
                    ))
        return events

    # ============= 应用 =============

    @staticmethod
    def apply_events(state, events: list[PathEvent]) -> None:
        """应用事件到 state.path_state（Coordinator 在 W13 调）"""
        ps = getattr(state, "path_state", None)
        if ps is None:
            return

        for ev in events:
            ev_type = ev.type
            pid = ev.path_id
            if ev_type == "SWITCH_MAIN":
                # 切换主路径焦点
                ps.main_path_focus = pid
            elif ev_type == "UNLOCK":
                # 从 locked_paths 移到 active_paths
                if pid in ps.locked_paths:
                    ps.locked_paths.remove(pid)
                if pid not in ps.active_paths:
                    ps.active_paths.append(pid)
                # 默认 affinity 0.5
                ps.path_affinity.setdefault(pid, 0.5)
            elif ev_type == "LOCK":
                # 锁定：active → locked
                if pid in ps.active_paths:
                    ps.active_paths.remove(pid)
                if pid not in ps.locked_paths:
                    ps.locked_paths.append(pid)
            elif ev_type == "COMPLETE":
                # active → completed
                if pid in ps.active_paths:
                    ps.active_paths.remove(pid)
                if pid in ps.dormant_paths:
                    ps.dormant_paths.remove(pid)
                if pid not in ps.completed_paths:
                    ps.completed_paths.append(pid)
            elif ev_type == "REORDER":
                # active ↔ dormant 切换
                new_status = ev.payload.get("new_status", "dormant")
                if new_status == "dormant":
                    if pid in ps.active_paths:
                        ps.active_paths.remove(pid)
                    if pid not in ps.dormant_paths:
                        ps.dormant_paths.append(pid)
                elif new_status == "active":
                    if pid in ps.dormant_paths:
                        ps.dormant_paths.remove(pid)
                    if pid not in ps.active_paths:
                        ps.active_paths.append(pid)
