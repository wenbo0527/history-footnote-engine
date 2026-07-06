"""🆕 v1.7.40 Sub-Facades（架构进一步简化）

GameEngineFacade 内部聚合 7 子系统 → 现在每个子系统有独立 Sub-Facade

设计：
- QuestFacade：管理 QuestSystem + 任务进度查询
- DramaFacade：管理 DramaManager + 玩家模型
- WikiFacade：管理 WikiRetriever + cache + summarize
- EventFacade：管理 EventBus + 事件历史
- StateFacade：管理 GameState + 状态摘要

GameEngineFacade 聚合这 5 个 Sub-Facade。
"""
from __future__ import annotations

import logging
from typing import Optional

from history_footnote.game_state import GameState
from history_footnote.event_bus import EventBus, GameEvent
from history_footnote.drama_manager import DramaManager, PlayerModel
from history_footnote.quest_system import QuestSystem, Quest
from history_footnote.wiki_retriever import WikiRetriever
from history_footnote.wiki_tools import search_wiki, search_wiki_by_action


_LOG = logging.getLogger("history_footnote.sub_facades")


# ============= QuestFacade =============

class QuestFacade:
    """任务管理子 facade"""

    def __init__(self, state: GameState, event_bus: EventBus, quest_system: QuestSystem):
        self.state = state
        self.event_bus = event_bus
        self.quest_system = quest_system

    def get_active_quests(self) -> list[Quest]:
        return self.quest_system.get_active_quests()

    def get_summary(self) -> dict:
        return self.quest_system.get_progress_summary()

    def get_completion_rate(self) -> float:
        s = self.quest_system.get_progress_summary()
        return len(s["completed"]) / max(s["total"], 1)

    def save(self) -> None:
        self.quest_system.save()

    @property
    def total(self) -> int:
        return len(self.quest_system.quests)

    @property
    def completed_count(self) -> int:
        return len(self.quest_system.get_progress_summary()["completed"])


# ============= DramaFacade =============

class DramaFacade:
    """戏剧管理子 facade"""

    def __init__(self, state: GameState, drama_manager: DramaManager):
        self.state = state
        self.drama_manager = drama_manager

    def record_action(self, verb: str, obj: str = "", is_initiative: bool = True) -> None:
        self.drama_manager.record_player_action(verb, obj, is_initiative)
        self.drama_manager.save()

    def evaluate(self) -> list:
        return self.drama_manager.evaluate()

    def get_interventions(self) -> list:
        return list(self.drama_manager.intervention_history)

    def get_player_model(self) -> PlayerModel:
        return self.drama_manager.player_model

    def get_summary(self) -> dict:
        pm = self.drama_manager.player_model
        return {
            "total_rounds": pm.total_rounds,
            "initiative_ratio": pm.initiative_ratio,
            "current_focus": pm.current_focus,
            "interventions_count": len(self.drama_manager.intervention_history),
            "action_counts": dict(pm.action_counts),
        }

    def save(self) -> None:
        self.drama_manager.save()


# ============= WikiFacade =============

class WikiFacade:
    """Wiki 检索子 facade"""

    def __init__(self, wiki_retriever: WikiRetriever):
        self.wiki_retriever = wiki_retriever
        self._cache: dict = {}
        self._cache_max = 100
        self._hits = 0
        self._total = 0

    def search(self, query: str = "", action_verb: str = "", target: str = "",
               city: str = "", intent: str = "", top_k: int = 3) -> list:
        """检索 Wiki（带 cache）"""
        cache_key = (action_verb, target, city, top_k) if action_verb else ("raw", query, intent, city, top_k)
        self._total += 1
        if cache_key in self._cache:
            self._hits += 1
            return self._cache[cache_key]
        # 实际检索
        if action_verb and not intent:
            verb_intent_map = {
                "TRAVEL": "route", "MEET": "gossip", "SELL": "gossip",
                "BUY": "gossip", "CRAFT": "gossip", "IDLE": "gossip",
            }
            intent = verb_intent_map.get(action_verb, "")
        if not query and action_verb:
            query = f"{action_verb} {target}".strip()
        if action_verb:
            result = search_wiki_by_action(
                action_verb=action_verb, target=target, city=city, top_k=top_k
            )
            fragments = result.get("fragments", [])
        else:
            result = search_wiki(query=query, intent=intent, city=city, top_k=top_k)
            fragments = result.get("fragments", [])
        # 缓存
        if len(self._cache) >= self._cache_max:
            keys_to_delete = list(self._cache.keys())[:self._cache_max // 10]
            for k in keys_to_delete:
                del self._cache[k]
        self._cache[cache_key] = fragments
        return fragments

    def summarize_fragments(self, fragments: list, query: str = "",
                            llm_callable=None) -> list:
        """Wiki 片段 LLM 总结（截断）"""
        summarized = []
        for f in fragments:
            content = f.get("content", "")
            title = f.get("title", "")
            if len(content) <= 500:
                summarized.append(f)
                continue
            if llm_callable is None:
                head = content[:300]
                tail = content[-100:]
                summarized.append({
                    **f,
                    "content": f"{head}\n...\n{tail}",
                    "_summarized": True,
                    "_original_length": len(content),
                })
            else:
                try:
                    summary_text = llm_callable(
                        f"用 200 字内总结以下内容，重点保留：{query or '史实细节'}。\n\n{title}\n{content}"
                    )
                    summarized.append({
                        **f,
                        "content": f"{title}\n{summary_text}",
                        "_summarized": True,
                        "_original_length": len(content),
                    })
                except Exception:
                    summarized.append({
                        **f, "content": content[:500] + "...",
                        "_summarized": True,
                    })
        return summarized

    def get_cache_stats(self) -> dict:
        return {
            "cache_size": len(self._cache),
            "cache_max": self._cache_max,
            "hit_rate": self._hits / max(self._total, 1),
        }

    def clear_cache(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._total = 0


# ============= EventFacade =============

class EventFacade:
    """事件管理子 facade"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def publish(self, event_id: str, event_type: str = "", data: dict = None,
                source: str = "manual", priority: int = 50) -> int:
        if not event_type and event_id:
            event_type = event_id.split(".")[0]
        return self.event_bus.publish(GameEvent(
            id=event_id, type=event_type, data=data or {},
            source=source, priority=priority,
        ))

    def get_history(self, event_type: str = "", limit: int = 20) -> list:
        return self.event_bus.get_history(event_type=event_type, limit=limit)

    def get_stats(self) -> dict:
        return self.event_bus.get_stats()


# ============= StateFacade =============

class StateFacade:
    """状态管理子 facade"""

    def __init__(self, state: GameState):
        self.state = state

    def get_summary(self) -> dict:
        items = self.state.discoveries.get("items", {}) or {}
        persons = self.state.discoveries.get("persons", {}) or {}
        return {
            "cash": self.state.cash,
            "debt": self.state.debt,
            "city": self.state.current_city,
            "items_count": len(items),
            "persons_count": len(persons),
            "round_number": self.state.round_number,
            "triggered_events": len(self.state.triggered_events or []),
        }

    def get_discoveries(self, kind: str = "") -> list:
        """获取发现列表"""
        if kind:
            bucket = self.state.discoveries.get(kind, {}) or {}
            if isinstance(bucket, dict):
                return list(bucket.values())
            return bucket
        all_items = []
        for k, v in (self.state.discoveries or {}).items():
            if isinstance(v, dict):
                all_items.extend([(k, val) for val in v.values()])
            else:
                all_items.extend([(k, val) for val in v])
        return all_items


# ============= 烟雾测试 =============

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from history_footnote.game_state import GameState
    from history_footnote.event_bus import get_event_bus
    from history_footnote.drama_manager import DramaManager
    from history_footnote.quest_system import QuestSystem, WANLI_QUESTS
    from history_footnote.wiki_retriever import get_wiki_retriever

    s = GameState()
    s.cash = 5.0
    bus = get_event_bus()
    qs = QuestSystem(s, bus, WANLI_QUESTS)
    dm = DramaManager(s, {})
    wr = get_wiki_retriever()

    # Sub-Facade 实例化
    qf = QuestFacade(s, bus, qs)
    df = DramaFacade(s, dm)
    wf = WikiFacade(wr)
    ef = EventFacade(bus)
    sf = StateFacade(s)

    # 1. QuestFacade
    print("=== QuestFacade ===")
    summary = qf.get_summary()
    print(f"  total: {qf.total}")
    print(f"  completed: {qf.completed_count}")
    print(f"  completion_rate: {qf.get_completion_rate():.0%}")

    # 2. DramaFacade
    print("\n=== DramaFacade ===")
    df.record_action("TRAVEL", "suzhou", is_initiative=True)
    s_dr = df.get_summary()
    print(f"  {s_dr}")

    # 3. WikiFacade
    print("\n=== WikiFacade ===")
    frags = wf.search(action_verb="TRAVEL", target="suzhou", city="shengze", top_k=2)
    print(f"  检索 1: {len(frags)} 片段")
    frags2 = wf.search(action_verb="TRAVEL", target="suzhou", city="shengze", top_k=2)
    cache = wf.get_cache_stats()
    print(f"  检索 2: {len(frags2)} 片段, cache: {cache}")

    # 4. EventFacade
    print("\n=== EventFacade ===")
    n = ef.publish("test.event", data={"x": 1}, source="test")
    print(f"  published: {n} handlers")
    history = ef.get_history(limit=5)
    print(f"  history: {len(history)} 条")

    # 5. StateFacade
    print("\n=== StateFacade ===")
    s_summary = sf.get_summary()
    for k, v in s_summary.items():
        print(f"  {k}: {v}")
