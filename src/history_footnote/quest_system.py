"""🆕 v1.7.34 声明式任务系统（QuestSystem）

依据 RPG 引擎调研报告（Godot Questify）：
> 任务"探索古堡"的完成条件 = 玩家"使用古老钥匙打开城堡大门"

设计：
- 任务数据：JSON 声明式（id, name, description, conditions, rewards）
- 条件类型：on_event / on_state / on_choice
- 自动追踪状态，条件满足时推进叙事
- 把"叙事逻辑"与"游戏逻辑"解耦

任务分类：
- main（主线）
- side（支线）
- daily（日常）
- event（世界事件）
- achievement（成就）

任务状态：
- locked（前置未满足）
- available（可接）
- active（进行中）
- completed（已完成）
- failed（失败）
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

from history_footnote.event_bus import EventBus, GameEvent
from history_footnote.game_state import GameState


_LOG = logging.getLogger("history_footnote.quest_system")


class QuestStatus(Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class ConditionType(Enum):
    ON_EVENT = "on_event"  # 事件触发
    ON_STATE = "on_state"  # 状态条件（如 cash >= 5）
    ON_CHOICE = "on_choice"  # 玩家选择


# ============= 任务定义 =============

@dataclass
class QuestCondition:
    """任务完成条件"""
    type: str  # ConditionType
    # on_event: {"event_id": "fin.sell_silk", "min_count": 3}
    # on_state: {"field": "cash", "op": ">=", "value": 5.0}
    # on_choice: {"verb": "GIVE", "object": "沈氏"}
    config: dict = field(default_factory=dict)

    def evaluate(self, state: GameState, event_bus: EventBus) -> bool:
        """评估条件是否满足"""
        if self.type == ConditionType.ON_EVENT:
            return self._eval_on_event(state, event_bus)
        if self.type == ConditionType.ON_STATE:
            return self._eval_on_state(state)
        if self.type == ConditionType.ON_CHOICE:
            return self._eval_on_choice(state, event_bus)
        return False

    def _eval_on_event(self, state: GameState, event_bus: EventBus) -> bool:
        event_id = self.config.get("event_id", "")
        min_count = self.config.get("min_count", 1)
        if not event_id:
            return False
        history = event_bus.get_history(event_type=event_id, limit=1000)
        return len(history) >= min_count

    def _eval_on_state(self, state: GameState) -> bool:
        field_name = self.config.get("field", "")
        op = self.config.get("op", ">=")
        value = self.config.get("value", 0)
        if not hasattr(state, field_name):
            return False
        actual = getattr(state, field_name)
        if op == ">=":
            return actual >= value
        if op == "<=":
            return actual <= value
        if op == ">":
            return actual > value
        if op == "<":
            return actual < value
        if op == "==":
            return actual == value
        return False

    def _eval_on_choice(self, state: GameState, event_bus: EventBus) -> bool:
        verb = self.config.get("verb", "")
        obj = self.config.get("object", "")
        target = self.config.get("target", "")
        pm = state.player_model if hasattr(state, "player_model") else {}
        recent = pm.get("recent_actions", []) if isinstance(pm, dict) else []
        for a in recent[-3:]:
            if a.get("verb") == verb:
                if obj and a.get("object") != obj:
                    continue
                if target and a.get("target") != target:
                    continue
                return True
        return False


@dataclass
class Quest:
    """任务定义"""
    id: str
    name: str
    description: str
    category: str = "side"  # main/side/daily/event/achievement
    # 前置条件（任务 ID 列表）
    prerequisites: list = field(default_factory=list)
    # 完成条件（多条件 AND 关系）
    conditions: list = field(default_factory=list)  # list[QuestCondition]
    # 奖励
    rewards: dict = field(default_factory=dict)  # {cash: 0.5, discover: "item.name", ...}
    # 失败条件
    fail_conditions: list = field(default_factory=list)
    # 史实锚点（"万历十五年"等）
    historical_anchor: str = ""
    # 是否自动接（条件满足后自动 ACTIVE）
    auto_accept: bool = False
    # 状态
    status: str = "locked"
    progress: int = 0  # 已完成条件数
    # 元数据
    metadata: dict = field(default_factory=dict)

    def is_locked(self) -> bool:
        return self.status == QuestStatus.LOCKED.value

    def is_active(self) -> bool:
        return self.status == QuestStatus.ACTIVE.value

    def is_completed(self) -> bool:
        return self.status == QuestStatus.COMPLETED.value

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Quest":
        conditions = [QuestCondition(**c) if isinstance(c, dict) else c for c in d.get("conditions", [])]
        fail_conditions = [QuestCondition(**c) if isinstance(c, dict) else c for c in d.get("fail_conditions", [])]
        d = dict(d)
        d["conditions"] = conditions
        d["fail_conditions"] = fail_conditions
        return cls(**d)


# ============= 任务系统 =============

class QuestSystem:
    """声明式任务系统

    数据流：
    1. 启动时加载 era.quests 节点
    2. 订阅 EventBus（接收事件）
    3. 评估每个 active 任务的 conditions
    4. 条件满足 → 触发 rewards + 标记 completed
    """

    def __init__(self, state: GameState, event_bus: EventBus, quest_defs: list | None = None):
        self.state = state
        self.event_bus = event_bus
        # 加载任务定义
        self.quests: dict[str, Quest] = {}
        if quest_defs:
            for q in quest_defs:
                self.quests[q.id] = Quest.from_dict(q) if isinstance(q, dict) else q
        # 加载已持久化的状态
        self.quest_states: dict[str, dict] = getattr(state, "quest_states", {}) or {}
        # 同步状态
        for qid, qst in self.quest_states.items():
            if qid in self.quests:
                self.quests[qid].status = qst.get("status", "locked")
                self.quests[qid].progress = qst.get("progress", 0)
        # 🆕 v1.7.34 修复：默认所有任务为 AVAILABLE（无前置）
        for q in self.quests.values():
            if q.status == QuestStatus.LOCKED.value and not q.prerequisites:
                q.status = QuestStatus.AVAILABLE.value
        # 订阅事件
        self.event_bus.subscribe("*", self._on_event, priority=10)

    # === 任务定义管理 ===

    def add_quest(self, quest: Quest) -> None:
        """添加任务"""
        self.quests[quest.id] = quest
        # 初始化状态
        if quest.id not in self.quest_states:
            self.quest_states[quest.id] = {
                "status": quest.status,
                "progress": 0,
            }

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        return self.quests.get(quest_id)

    def get_active_quests(self) -> list[Quest]:
        return [q for q in self.quests.values() if q.is_active()]

    def get_available_quests(self) -> list[Quest]:
        return [q for q in self.quests.values() if q.status == QuestStatus.AVAILABLE.value]

    # === 玩家操作 ===

    def accept_quest(self, quest_id: str) -> bool:
        """玩家接受任务（AVAILABLE → ACTIVE）"""
        q = self.quests.get(quest_id)
        if not q or q.status != QuestStatus.AVAILABLE.value:
            return False
        q.status = QuestStatus.ACTIVE.value
        self.quest_states[quest_id] = {"status": q.status, "progress": 0}
        # 发布任务开始事件
        self.event_bus.publish(GameEvent(
            id="quest.started",
            type="quest",
            data={"quest_id": quest_id, "name": q.name},
        ))
        return True

    def complete_quest(self, quest_id: str) -> bool:
        """完成任务（ACTIVE → COMPLETED）"""
        q = self.quests.get(quest_id)
        if not q or q.status != QuestStatus.ACTIVE.value:
            return False
        q.status = QuestStatus.COMPLETED.value
        self.quest_states[quest_id] = {"status": q.status, "progress": q.progress}
        # 应用奖励
        self._apply_rewards(q)
        # 发布完成事件
        self.event_bus.publish(GameEvent(
            id="quest.completed",
            type="quest",
            data={"quest_id": quest_id, "name": q.name, "rewards": q.rewards},
        ))
        return True

    # === 事件处理 ===

    def _on_event(self, event: GameEvent) -> None:
        """事件处理：评估每个 active 任务的 conditions"""
        if event.type == "quest":
            return  # quest 事件不触发自己
        # 检查每个 active 任务
        for q in self.get_active_quests():
            self._check_quest_progress(q)

    def _check_quest_progress(self, quest: Quest) -> None:
        """检查任务进度"""
        if not quest.conditions:
            return
        completed_count = 0
        for cond in quest.conditions:
            if cond.evaluate(self.state, self.event_bus):
                completed_count += 1
        quest.progress = completed_count
        # 检查完成
        if completed_count >= len(quest.conditions):
            self.complete_quest(quest.id)
            return
        # 检查失败
        for cond in quest.fail_conditions:
            if cond.evaluate(self.state, self.event_bus):
                quest.status = QuestStatus.FAILED.value
                self.quest_states[quest.id] = {"status": quest.status, "progress": quest.progress}
                self.event_bus.publish(GameEvent(
                    id="quest.failed",
                    type="quest",
                    data={"quest_id": quest.id, "name": quest.name},
                ))
                return
        # 更新状态
        self.quest_states[quest.id] = {
            "status": quest.status,
            "progress": quest.progress,
        }

    def _apply_rewards(self, quest: Quest) -> None:
        """应用任务奖励"""
        rewards = quest.rewards
        if "cash" in rewards:
            self.state.apply_financial_change(
                float(rewards["cash"]),
                "quest_reward",
                f"任务 {quest.name} 奖励",
                self.state.current_city,
            )
        if "discover_item" in rewards:
            item = rewards["discover_item"]
            self.state.add_discovery("item", {
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "owner": self.state.current_city,
                "description": f"任务 {quest.name} 奖励",
                "source": "quest",
            })

    # === 存档 ===

    def save(self) -> None:
        """保存任务状态到 state"""
        self.state.quest_states = self.quest_states

    # === 查询 ===

    def get_progress_summary(self) -> dict:
        """获取任务进度概览"""
        active = self.get_active_quests()
        available = self.get_available_quests()
        completed = [q for q in self.quests.values() if q.is_completed()]
        return {
            "active": [{"id": q.id, "name": q.name, "progress": f"{q.progress}/{len(q.conditions)}"} for q in active],
            "available": [{"id": q.id, "name": q.name} for q in available],
            "completed": [{"id": q.id, "name": q.name} for q in completed],
            "total": len(self.quests),
        }


# ============= 内置任务模板（万历十五年）=============

WANLI_QUESTS = [
    Quest(
        id="quest.first_silk",
        name="初次织绸",
        description="织一匹湖绫，掌握基本技艺。",
        category="side",
        conditions=[
            QuestCondition(type=ConditionType.ON_EVENT, config={"event_id": "discover.item", "min_count": 1}),
        ],
        rewards={"cash": 0.5},
    ),
    Quest(
        id="quest.first_sell",
        name="第一次卖绸",
        description="把织好的湖绫卖给牙行，换取银两。",
        category="side",
        conditions=[
            QuestCondition(type=ConditionType.ON_EVENT, config={"event_id": "fin.sell_silk", "min_count": 1}),
        ],
        rewards={"discover_item": {"name": "吴掌柜", "type": "broker"}},
    ),
    Quest(
        id="quest.first_travel",
        name="初访苏州",
        description="从盛泽出发，去苏州看看。",
        category="side",
        conditions=[
            QuestCondition(type=ConditionType.ON_EVENT, config={"event_id": "city.arrive.suzhou", "min_count": 1}),
        ],
        rewards={"discover_item": {"name": "阊门码头", "type": "landmark"}},
    ),
    Quest(
        id="quest.family_meet",
        name="家人团圆",
        description="回家见沈氏。",
        category="side",
        conditions=[
            QuestCondition(type=ConditionType.ON_EVENT, config={"event_id": "fam.meet.fm_wife", "min_count": 1}),
        ],
        rewards={},
    ),
]


# ============= 烟雾测试 =============

if __name__ == "__main__":
    from history_footnote.event_bus import get_event_bus, reset_event_bus
    from history_footnote.game_state import GameState

    reset_event_bus()
    bus = get_event_bus()
    s = GameState()
    s.round_number = 1
    s.current_city = "shengze"
    s.cash = 5.0
    qs = QuestSystem(s, bus, WANLI_QUESTS)
    print(f"任务总数: {len(qs.quests)}")
    print(f"  - quest.first_silk: {qs.get_quest('quest.first_silk').description}")

    # 接受所有 available 任务
    for q in qs.quests.values():
        if q.status == QuestStatus.AVAILABLE.value:
            qs.accept_quest(q.id)
    print(f"\n接受后 active 任务: {len(qs.get_active_quests())}")

    # 模拟玩家动作
    bus.publish(GameEvent(id="discover.item", type="discover", data={"name": "湖绫"}))
    bus.publish(GameEvent(id="discover.item", type="discover", data={"name": "湖绫"}))
    print(f"发现 2 个 item 后，任务进度：")
    for q in qs.get_active_quests():
        print(f"  {q.id}: {q.progress}/{len(q.conditions)}")

    # 卖湖绫
    bus.publish(GameEvent(id="fin.sell_silk", type="fin", data={"amount": 0.7}))
    print(f"卖 1 次后，任务进度：")
    for q in qs.get_active_quests():
        print(f"  {q.id}: {q.progress}/{len(q.conditions)} status={q.status}")

    # 概览
    print(f"\n=== 概览 ===")
    for k, v in qs.get_progress_summary().items():
        print(f"  {k}: {v}")
