"""🆕 v1.7.38 Game Engine Facade（架构简化）

v1.7.32-37 累积了多个子系统：
- EventBus（事件总线）
- DramaManager（节奏感知）
- QuestSystem（任务系统）
- WikiRetriever（Wiki 检索）
- ActionResolver（玩家输入解析）
- EventParser（LLM 输出解析）
- Settlement（月度结算）

之前 game_loop 直接 import 7 个模块，耦合度高。
本 commit 抽 GameEngineFacade 统一接口。

设计：
- GameEngineFacade 类：唯一对外接口
- 内部聚合 7 个子系统
- 提供 8 个核心方法（替代 25+ 个分散调用）
- 让 game_loop 只调 facade，不直接 import 各模块
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from history_footnote.game_state import GameState
from history_footnote.action_resolver import (
    parse_player_input, resolve_action, apply_action_result,
    PlayerAction, ActionResult,
)
from history_footnote.event_bus import GameEvent, get_event_bus, EventBus
from history_footnote.drama_manager import DramaManager, PlayerModel
from history_footnote.quest_system import QuestSystem, Quest, QuestCondition, ConditionType
from history_footnote.wiki_tools import search_wiki_by_action, search_wiki
from history_footnote.wiki_retriever import get_wiki_retriever, WikiRetriever


_LOG = logging.getLogger("history_footnote.game_engine_facade")


class GameEngineFacade:
    """游戏引擎门面（统一接口）

    替代 game_loop 中的 7 个 import + 25+ 个分散调用
    """

    def __init__(self, state: GameState, era_config: dict, root_dir: Optional[Path] = None):
        self.state = state
        self.era_config = era_config
        # 子系统（延迟初始化）
        self._event_bus: Optional[EventBus] = None
        self._drama_manager: Optional[DramaManager] = None
        self._quest_system: Optional[QuestSystem] = None
        self._wiki_retriever: Optional[WikiRetriever] = None
        # Wiki 检索 cache
        self._wiki_cache: dict = {}  # {(verb, target, city): fragments}
        self._wiki_cache_max = 100  # 最多缓存 100 条

    # ============= 子系统访问器 =============

    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus

    @property
    def drama_manager(self) -> DramaManager:
        if self._drama_manager is None:
            self._drama_manager = DramaManager(self.state, self.era_config)
        return self._drama_manager

    @property
    def quest_system(self) -> QuestSystem:
        if self._quest_system is None:
            from history_footnote.quest_system import WANLI_QUESTS
            self._quest_system = QuestSystem(self.state, self.event_bus, WANLI_QUESTS)
        return self._quest_system

    @property
    def wiki_retriever(self) -> WikiRetriever:
        if self._wiki_retriever is None:
            self._wiki_retriever = get_wiki_retriever()
        return self._wiki_retriever

    # ============= 核心 API（8 个方法）=============

    def process_player_input(self, player_input: str) -> dict:
        """处理玩家输入（action_resolver + apply + EventBus + Wiki 检索）

        Returns:
            {
              "player_action": PlayerAction,
              "action_result": ActionResult,
              "wiki_fragments": list,  # Wiki 检索片段
              "drama_hint": str,  # Drama 干预 hint
            }
        """
        # 1. 解析 + 解析动作
        action = parse_player_input(player_input)
        result = resolve_action(self.state, action, self.era_config)
        wiki_fragments = []
        drama_hint = ""

        if result.success:
            # 2. 应用动作
            apply_action_result(self.state, result)
            # 3. 发布事件到总线
            for ev in result.events:
                self.event_bus.publish(GameEvent(
                    id=ev.get("id", ""),
                    type=ev.get("id", "").split(".")[0] if ev.get("id") else "unknown",
                    data=ev,
                    source="action_resolver",
                    priority=50,
                ))
            # 4. DramaManager 记录
            self.drama_manager.record_player_action(
                verb=action.verb,
                obj=action.object,
                is_initiative=action.verb != "IDLE",
            )
            # 5. Wiki 检索（带 cache）
            wiki_fragments = self._search_wiki_cached(
                action_verb=action.verb,
                target=action.target or "",
                city=self.state.current_city or "",
            )
        # 6. DramaManager 评估
        interventions = self.drama_manager.evaluate()
        if interventions:
            drama_hint = self.drama_manager.build_llm_intervention_hint(interventions)
            # 发布 drama 事件
            self.event_bus.publish(GameEvent(
                id="drama.intervention",
                type="drama",
                data={"interventions": [
                    {"type": iv.type, "reason": iv.reason, "action": iv.action}
                    for iv in interventions
                ]},
                source="drama_manager",
                priority=70,
            ))

        return {
            "player_action": action,
            "action_result": result,
            "wiki_fragments": wiki_fragments,
            "drama_hint": drama_hint,
        }

    def get_state_summary(self) -> dict:
        """获取游戏状态摘要

        Returns:
            {
              "cash": float,
              "debt": float,
              "city": str,
              "items_count": int,
              "persons_count": int,
              "round_number": int,
              "triggered_events": int,
              "completed_quests": int,
              "active_quests": int,
              "drama_ir": float,
              "bus_stats": dict,
            }
        """
        items = self.state.discoveries.get("items", {}) or {}
        persons = self.state.discoveries.get("persons", {}) or {}
        summary = self.quest_system.get_progress_summary()
        return {
            "cash": self.state.cash,
            "debt": self.state.debt,
            "city": self.state.current_city,
            "items_count": len(items),
            "persons_count": len(persons),
            "round_number": self.state.round_number,
            "triggered_events": len(self.state.triggered_events or []),
            "completed_quests": len(summary["completed"]),
            "active_quests": len(summary["active"]),
            "drama_ir": self.drama_manager.player_model.initiative_ratio,
            "bus_stats": self.event_bus.get_stats(),
        }

    def get_event_history(self, event_type: str = "", limit: int = 20) -> list:
        """获取事件历史"""
        return self.event_bus.get_history(event_type=event_type, limit=limit)

    def get_quest_summary(self) -> dict:
        """获取任务进度概览"""
        return self.quest_system.get_progress_summary()

    def get_drama_interventions(self) -> list:
        """获取 Drama 干预历史"""
        return list(self.drama_manager.intervention_history)

    def search_wiki(self, query: str, intent: str = "", city: str = "",
                    top_k: int = 3) -> list:
        """检索 Wiki 片段（带 cache）"""
        return self._search_wiki_cached(query=query, intent=intent, city=city, top_k=top_k)

    def get_wiki_cache_stats(self) -> dict:
        """获取 Wiki cache 统计"""
        return {
            "cache_size": len(self._wiki_cache),
            "cache_max": self._wiki_cache_max,
            "hit_rate": getattr(self, "_wiki_hits", 0) / max(getattr(self, "_wiki_total", 1), 1),
        }

    def save_all(self) -> None:
        """保存所有子系统状态"""
        self.quest_system.save()
        self.drama_manager.save()

    # ============= Wiki cache =============

    def _search_wiki_cached(self, action_verb: str = "", target: str = "",
                            city: str = "", query: str = "", intent: str = "",
                            top_k: int = 3) -> list:
        """Wiki 检索（带 cache）"""
        # 构造 cache key
        if action_verb:
            cache_key = (action_verb, target, city, top_k)
        else:
            cache_key = ("raw", query, intent, city, top_k)
        if not hasattr(self, "_wiki_hits"):
            self._wiki_hits = 0
        if not hasattr(self, "_wiki_total"):
            self._wiki_total = 0

        self._wiki_total += 1
        if cache_key in self._wiki_cache:
            self._wiki_hits += 1
            return self._wiki_cache[cache_key]

        # 实际检索
        if action_verb:
            result = search_wiki_by_action(
                action_verb=action_verb, target=target, city=city, top_k=top_k
            )
            fragments = result.get("fragments", [])
        else:
            result = search_wiki(query=query, intent=intent, city=city, top_k=top_k)
            fragments = result.get("fragments", [])

        # 缓存
        if len(self._wiki_cache) >= self._wiki_cache_max:
            # LRU: 删除最早的 10%
            keys_to_delete = list(self._wiki_cache.keys())[:self._wiki_cache_max // 10]
            for k in keys_to_delete:
                del self._wiki_cache[k]
        self._wiki_cache[cache_key] = fragments
        return fragments


# ============= 全局单例 =============

_GLOBAL_FACADE: Optional[GameEngineFacade] = None


def get_engine_facade(state: GameState, era_config: dict) -> GameEngineFacade:
    """获取游戏引擎 facade"""
    global _GLOBAL_FACADE
    if _GLOBAL_FACADE is None:
        _GLOBAL_FACADE = GameEngineFacade(state, era_config)
    return _GLOBAL_FACADE


def reset_engine_facade() -> None:
    global _GLOBAL_FACADE
    _GLOBAL_FACADE = None


# ============= 烟雾测试 =============

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from history_footnote.game_state import GameState

    s = GameState()
    s.cash = 5.0
    facade = GameEngineFacade(s, era_config={})

    # 1. process_player_input
    print("=== process_player_input ===")
    result = facade.process_player_input("我织了一匹湖绫")
    print(f"  verb: {result['player_action'].verb}")
    print(f"  events: {[e['id'] for e in result['action_result'].events]}")
    print(f"  wiki_fragments: {len(result['wiki_fragments'])}")

    result2 = facade.process_player_input("我搭船去苏州")
    print(f"  TRAVEL verb: {result2['player_action'].verb}")
    print(f"  wiki_fragments: {len(result2['wiki_fragments'])}")

    # 2. get_state_summary
    print("\n=== get_state_summary ===")
    summary = facade.get_state_summary()
    for k, v in summary.items():
        if k != "bus_stats":
            print(f"  {k}: {v}")

    # 3. Wiki cache
    print("\n=== Wiki cache ===")
    result_a = facade.search_wiki("苏州码头")
    result_b = facade.search_wiki("苏州码头")  # 应 hit cache
    stats = facade.get_wiki_cache_stats()
    print(f"  cache: {stats}")

    # 4. Quest summary
    print("\n=== Quest summary ===")
    qs = facade.get_quest_summary()
    for k, v in qs.items():
        print(f"  {k}: {v}")
