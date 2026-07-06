"""🆕 v1.7.34 Drama Manager（戏剧管理器）

依据 RPG 引擎调研报告：
> 监控玩家行为，在不降低玩家自主性的前提下干预叙事走向。

核心机制：
1. **Player Model**（玩家建模）：记录偏好/进度/节奏
2. **Possibility Space**（可能性空间）：所有可能叙事节点
3. **Intervention Decisions**（干预决策）：何时引导玩家

Left 4 Dead 的 AI Director 是最成功实践：
- 监控压力/弹药/健康
- 动态调整生成数量
- 放松时紧张，紧张时喘息

Questwright 的 Drama Manager：
- 节奏感知
- 角色均衡
- NPC 记忆
- 背景故事回响

本实现：3 维度干预决策
- PACE 节奏：玩家最近 N 轮太紧张/太轻松？
- BALANCE 均衡：某些 NPC 太久没出现？
- MEMORY 记忆：玩家之前的选择是否应该回响？
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from history_footnote.game_state import GameState


_LOG = logging.getLogger("history_footnote.drama_manager")


# ============= 玩家模型 =============

@dataclass
class PlayerModel:
    """玩家行为模型"""
    # 玩家行为时间窗口（最近 5 轮）
    recent_actions: deque = field(default_factory=lambda: deque(maxlen=5))
    # 偏好统计
    action_counts: dict = field(default_factory=lambda: defaultdict(int))
    # 情感状态（基于事件推断）
    emotion_state: str = "neutral"  # relaxed/normal/tense/distressed
    # 当前关注点
    current_focus: str = ""  # 玩家当前在做哪类事
    # 选择历史（重大选择）
    major_choices: list = field(default_factory=list)
    # 跑动时间
    total_rounds: int = 0
    # 主动 / 被动 比例
    initiative_ratio: float = 0.5  # 主动 0-1
    # 城市旅行频次
    city_travel_count: int = 0

    def record_action(self, action_verb: str, action_object: str = "", is_initiative: bool = True) -> None:
        """记录一个玩家动作"""
        self.recent_actions.append({
            "verb": action_verb,
            "object": action_object,
            "is_initiative": is_initiative,
            "round": self.total_rounds,
        })
        self.action_counts[action_verb] += 1
        self.total_rounds += 1
        if is_initiative:
            # 主动动作比率
            initiative_count = sum(1 for a in self.recent_actions if a.get("is_initiative"))
            self.initiative_ratio = initiative_count / max(len(self.recent_actions), 1)
        # 更新关注点
        self.current_focus = action_verb

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recent_actions"] = list(self.recent_actions)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PlayerModel":
        recent = d.get("recent_actions", [])
        d = dict(d)
        d["recent_actions"] = deque(recent, maxlen=5)
        d["action_counts"] = defaultdict(int, d.get("action_counts", {}))
        return cls(**d)


# ============= 干预类型 =============

class InterventionType:
    NONE = "none"  # 不干预
    PACE_HINT = "pace_hint"  # 节奏提示（"最近太紧张了"）
    NPC_REINTRO = "npc_reintro"  # 重新引入 NPC
    MEMORY_ECHO = "memory_echo"  # 旧选择回响
    DRAMA_INTRODUCE = "drama_introduce"  # 主动引入新剧情
    DRAMA_PAUSE = "drama_pause"  # 暂停戏剧


@dataclass
class Intervention:
    """干预决策"""
    type: str  # InterventionType.*
    priority: int  # 0-100
    reason: str
    action: str  # 注入到 LLM 的提示
    payload: dict = field(default_factory=dict)  # 附加数据


# ============= Drama Manager =============

class DramaManager:
    """戏剧管理器（监控 + 干预）"""

    # 节奏阈值
    TENSE_THRESHOLD = 0.7  # initiative_ratio > 0.7 = 紧张
    RELAXED_THRESHOLD = 0.3  # initiative_ratio < 0.3 = 放松
    NPC_REINTRO_DISTANCE = 8  # NPC 8 轮没出现 → 重新引入

    def __init__(self, state: GameState, config: dict | None = None):
        self.state = state
        self.config = config or {}
        # 玩家模型（持久化在 state.player_model）
        self.player_model = self._load_player_model()
        # NPC 出现时间
        self.npc_last_seen: dict[str, int] = {}
        # 干预历史
        self.intervention_history: list[dict] = []

    def _load_player_model(self) -> PlayerModel:
        """从 state 加载 player_model（如不存在则创建）"""
        pm_data = getattr(self.state, "player_model", None)
        if pm_data:
            return PlayerModel.from_dict(pm_data)
        return PlayerModel()

    def save(self) -> None:
        """保存 player_model 到 state"""
        self.state.player_model = self.player_model.to_dict()

    # === 监控 ===

    def record_player_action(self, verb: str, obj: str = "", is_initiative: bool = True) -> None:
        """记录玩家动作"""
        self.player_model.record_action(verb, obj, is_initiative)
        self.save()

    def record_npc_seen(self, npc_id: str) -> None:
        """记录 NPC 出现"""
        self.npc_last_seen[npc_id] = self.state.round_number

    # === 评估（可能 0-3 个干预）===

    def evaluate(self) -> list[Intervention]:
        """评估当前状态，返回干预列表

        3 维度评估：
        1. PACE 节奏（initiative_ratio + 重大事件数）
        2. BALANCE 均衡（NPC 出现频次）
        3. MEMORY 记忆（旧选择回响）
        """
        interventions = []
        # 1. 节奏感知
        pace_iv = self._evaluate_pace()
        if pace_iv:
            interventions.append(pace_iv)
        # 2. NPC 均衡
        bal_iv = self._evaluate_balance()
        if bal_iv:
            interventions.append(bal_iv)
        # 3. 记忆回响
        mem_iv = self._evaluate_memory()
        if mem_iv:
            interventions.append(mem_iv)
        # 保存
        for iv in interventions:
            self.intervention_history.append({
                "round": self.state.round_number,
                "type": iv.type,
                "reason": iv.reason,
            })
        return interventions

    def _evaluate_pace(self) -> Optional[Intervention]:
        """节奏评估"""
        ir = self.player_model.initiative_ratio
        if ir > self.TENSE_THRESHOLD:
            return Intervention(
                type=InterventionType.DRAMA_PAUSE,
                priority=70,
                reason=f"玩家太紧张（initiative={ir:.0%}）",
                action="应给玩家一段安静时光——日常、家人、小事件",
                payload={"pace": "tense", "ir": ir},
            )
        if ir < self.RELAXED_THRESHOLD and self.player_model.total_rounds > 5:
            return Intervention(
                type=InterventionType.DRAMA_INTRODUCE,
                priority=70,
                reason=f"玩家太放松（initiative={ir:.0%}）",
                action="应引入一些紧张/戏剧性事件（不能直接触发，但可以暗示）",
                payload={"pace": "relaxed", "ir": ir},
            )
        return None

    def _evaluate_balance(self) -> Optional[Intervention]:
        """NPC 均衡评估"""
        if not self.npc_last_seen:
            return None
        # 找出最久没出现的 NPC
        most_stale = None
        most_stale_dist = 0
        for npc_id, last_seen in self.npc_last_seen.items():
            dist = self.state.round_number - last_seen
            if dist > most_stale_dist:
                most_stale_dist = dist
                most_stale = npc_id
        if most_stale_dist > self.NPC_REINTRO_DISTANCE:
            return Intervention(
                type=InterventionType.NPC_REINTRO,
                priority=60,
                reason=f"{most_stale} 已 {most_stale_dist} 轮没出现",
                action=f"可让 {most_stale} 通过传闻/信/偶遇再次出现",
                payload={"npc": most_stale, "distance": most_stale_dist},
            )
        return None

    def _evaluate_memory(self) -> Optional[Intervention]:
        """记忆回响评估"""
        if not self.player_model.major_choices:
            return None
        # 找出 3 轮前的重大选择
        for choice in self.player_model.major_choices[-3:]:
            choice_round = choice.get("round", 0)
            distance = self.state.round_number - choice_round
            if distance >= 5 and distance <= 10:
                return Intervention(
                    type=InterventionType.MEMORY_ECHO,
                    priority=80,
                    reason=f"旧选择 '{choice.get('summary', '')}' 应回响",
                    action=f"在 narrative 中引用玩家之前的选择：{choice.get('summary', '')}",
                    payload={"choice": choice},
                )
        return None

    # === 注入到 LLM context ===

    def build_llm_intervention_hint(self, interventions: list[Intervention]) -> str:
        """把干预列表转成 LLM prompt 提示"""
        if not interventions:
            return ""
        lines = ["【Drama Manager 干预建议（不是硬要求）】"]
        for iv in interventions:
            lines.append(f"- [{iv.type}] {iv.reason}")
            lines.append(f"  建议：{iv.action}")
        return "\n".join(lines)


# ============= 烟雾测试 =============

if __name__ == "__main__":
    from history_footnote.game_state import GameState

    s = GameState()
    s.round_number = 10
    dm = DramaManager(s, config={})

    # 模拟玩家太紧张
    for i in range(5):
        dm.record_player_action(verb="TRAVEL", obj="suzhou", is_initiative=True)
        dm.record_player_action(verb="SELL", obj="silk_bolt", is_initiative=True)

    print(f"player_model: {dm.player_model.to_dict()}")
    interventions = dm.evaluate()
    print(f"\ninterventions ({len(interventions)}):")
    for iv in interventions:
        print(f"  - [{iv.type}] {iv.reason}")
        print(f"    建议：{iv.action}")

    hint = dm.build_llm_intervention_hint(interventions)
    print(f"\n=== LLM 提示 ===\n{hint}")
