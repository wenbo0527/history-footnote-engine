"""游戏记忆管理——三层记忆体系

设计参考：设计文档v1.0.md 第3.3节"记忆管理"

三层记忆：
- 工作记忆：LLM对话上下文（LangGraph MessagesState管理，不在本模块）
- 情节记忆：JSON事件图谱（save_event / recall_events / 多路召回）
- 语义记忆：知识库（在 knowledge_base.py，本模块只做引用）

多路召回（解决"鸡生蛋"问题）：
- 时间召回：最近3回合始终注入
- 关键词召回：基于玩家输入的关键词
- 关联召回：基于当前场景/相关实体
- 因果召回：基于已触发事件链
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GameEvent:
    """一则游戏事件"""

    round: int
    type: str  # player_action / dm_narrative / historical_event / insight_unlocked
    summary: str
    player_action: str = ""
    consequences: list[str] = field(default_factory=list)
    affected_variables: dict[str, float] = field(default_factory=dict)
    relationship_changes: dict[str, str] = field(default_factory=dict)
    insight_unlocked: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GameEvent":
        return cls(**data)


class GameMemory:
    """游戏记忆管理器

    Phase 1用内存存储 + 定期持久化到JSON文件。
    Phase 2可升级为SQLite/Redis。
    """

    def __init__(self, save_dir: Path | None = None):
        self.events: list[GameEvent] = []
        self.save_dir = save_dir

    # === 写入 ===

    def save_event(self, event: GameEvent) -> None:
        """DM主动调用save_event记录事件

        DM是叙事的生成者，它最清楚发生了什么——比用LLM从叙事中提取更准。
        """
        self.events.append(event)
        self._persist()

    def save_events_batch(self, events: list[GameEvent]) -> None:
        """批量保存"""
        self.events.extend(events)
        self._persist()

    # === 多路召回 ===

    def recall_events(
        self,
        query: str = "",
        recent_n: int = 3,
        by_entity: str = "",
        by_cause: str = "",
    ) -> list[dict]:
        """多路召回相关历史事件

        Args:
            query: 关键词查询
            recent_n: 时间召回数量（最近N回合始终注入）
            by_entity: 关联实体（如NPC id / 地点）
            by_cause: 因果链追溯（如某trigger_id）

        Returns:
            事件摘要列表（dict格式）
        """
        results = []

        # 1. 时间召回：最近N回合
        for e in self.events[-recent_n:]:
            results.append(self._summarize(e))

        # 2. 关键词召回
        if query:
            keywords = re.split(r"[，,。\s]+", query)
            keywords = [k for k in keywords if len(k) >= 2]
            for e in self.events:
                if e in self.events[-recent_n:]:
                    continue  # 已包含
                text = f"{e.summary} {e.player_action}"
                if any(kw in text for kw in keywords):
                    results.append(self._summarize(e))

        # 3. 关联实体召回
        if by_entity:
            for e in self.events:
                if by_entity in e.relationship_changes:
                    if e not in self.events[-recent_n:]:
                        results.append(self._summarize(e))

        # 4. 因果链召回
        if by_cause:
            for e in self.events:
                if by_cause in str(e.metadata):
                    results.append(self._summarize(e))

        # 去重（按event引用）
        seen = set()
        unique = []
        for e in self.events:
            if id(e) in seen:
                continue
            seen.add(id(e))

        # 简化：直接按时间排序
        return results[:10]  # 最多返回10条

    def get_recent(self, rounds: int = 3, current_round: int | None = None) -> list[dict]:
        """获取最近N回合的事件摘要（时间召回）

        这是始终注入的，不需要查询参数。
        """
        if current_round is None and self.events:
            current_round = self.events[-1].round

        if current_round is None:
            return []

        target_rounds = set(range(max(1, current_round - rounds + 1), current_round + 1))
        recent = [e for e in self.events if e.round in target_rounds]
        return [self._summarize(e) for e in recent]

    # === 持久化 ===

    def _persist(self) -> None:
        """持久化到磁盘（如有save_dir）"""
        if self.save_dir is None:
            return
        self.save_dir.mkdir(parents=True, exist_ok=True)
        path = self.save_dir / "events.json"
        path.write_text(
            json.dumps([e.to_dict() for e in self.events], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_from_disk(self, path: Path) -> None:
        """从磁盘加载"""
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.events = [GameEvent.from_dict(d) for d in data]

    # === 辅助 ===

    @staticmethod
    def _summarize(e: GameEvent) -> dict:
        return {
            "round": e.round,
            "type": e.type,
            "summary": e.summary,
            "player_action": e.player_action,
        }

    def count(self) -> int:
        return len(self.events)
