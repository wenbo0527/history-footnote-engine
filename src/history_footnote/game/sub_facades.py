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
from pathlib import Path
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


# ============= 🆕 v2.8.0 ChapterFacade =============

class ChapterFacade:
    """章节管理子 facade（v2.8.0 段一）

    参考 v1.7.40 Sub-Facades 模式，复用 DramaManager.player_model
    段一只提供蓝图加载、章节初始化、收束查询、信息查询
    """

    def __init__(
        self,
        state: "GameState",
        era_config: dict,
        root_dir: Optional[Path] = None,
        drama_manager: Optional["DramaManager"] = None,
    ):
        self.state = state
        self.era_config = era_config
        # root_dir 默认是项目根（含 eras/ 目录）
        # 蓝图路径 = root_dir / eras / {era_id} / chapter{N}_blueprint.json
        if root_dir is None:
            self.root_dir = Path(".")
        else:
            self.root_dir = root_dir
        self._drama = drama_manager
        self._closure = None  # 懒加载

    @property
    def _blueprint_dir(self) -> Path:
        """蓝图目录：root_dir / eras / {era_id}"""
        era_id = self.state.era_id or "wanli1587"
        return self.root_dir / "eras" / era_id

    @property
    def drama_manager(self):
        return self._drama

    @drama_manager.setter
    def drama_manager(self, value: "DramaManager") -> None:
        """允许后续注入"""
        self._drama = value
        self._closure = None

    @property
    def closure(self):
        """懒加载收束判定器"""
        if self._closure is None:
            from history_footnote.chapter.closure import ChapterClosure
            self._closure = ChapterClosure(self.state, self._drama)
        return self._closure

    # ============= 蓝图加载 =============

    def load_blueprint(self, chapter_id: int) -> "ChapterBlueprint":
        """从 chapter{N}_blueprint.json 加载蓝图"""
        from history_footnote.chapter.types import ChapterBlueprint
        path = self._blueprint_dir / f"chapter{chapter_id}_blueprint.json"
        if not path.exists():
            raise FileNotFoundError(f"蓝图文件不存在: {path}")
        json_str = path.read_text(encoding="utf-8")
        blueprint = ChapterBlueprint.from_json(json_str)
        return blueprint

    def blueprint_exists(self, chapter_id: int) -> bool:
        """检查蓝图文件是否存在"""
        path = self._blueprint_dir / f"chapter{chapter_id}_blueprint.json"
        return path.exists()

    # ============= 🆕 v2.8.0 段二 元属性 =============

    def resolve_chapter_meta(self, chapter_id: int):
        """从 era_config 解析章节元属性

        段二纯规则引擎产出，不调 LLM
        段三会扩展：LLM 可读这个 meta 作为硬约束
        """
        from history_footnote.chapter.meta_resolver import ChapterMetaResolver
        resolver = ChapterMetaResolver(self.era_config or {})
        return resolver.resolve(chapter_id)

    def get_or_resolve_meta(self, chapter_id: int, blueprint: "ChapterBlueprint" = None):
        """优先从 blueprint 读 meta，缺失则用规则引擎解析

        段二逻辑：
        1. blueprint.meta 存在 → 用它
        2. 否则 → 调 resolve_chapter_meta
        """
        from history_footnote.chapter.types import ChapterMeta
        if blueprint is not None and blueprint.meta is not None:
            return blueprint.meta
        return self.resolve_chapter_meta(chapter_id)

    # ============= 🆕 v2.8.0 段三 W11 路径系统 =============

    @property
    def path_registry(self):
        """路径注册表（懒加载）"""
        if not hasattr(self, "_path_registry") or self._path_registry is None:
            from history_footnote.chapter.paths import PathRegistry
            self._path_registry = PathRegistry(self.era_config or {})
        return self._path_registry

    def get_path(self, path_id: str):
        """查询路径定义"""
        return self.path_registry.get(path_id)

    def get_paths_for_chapter(self, chapter_id: int):
        """查询指定章节的可用路径"""
        return self.path_registry.get_applicable_to_chapter(chapter_id)

    def get_main_paths(self):
        """查询所有主路径"""
        return self.path_registry.get_main_paths()

    def get_active_paths(self) -> list:
        """查询当前活跃路径（从 state.path_state）"""
        ps = getattr(self.state, "path_state", None)
        if ps is None:
            return []
        return list(ps.active_paths)

    def get_path_status(self, path_id: str) -> str:
        """查询路径状态（locked/active/dormant）"""
        ps = getattr(self.state, "path_state", None)
        if ps is None:
            return "locked"
        return ps.get_status(path_id)

    # ============= 🆕 v2.8.0 段三 W12 路径切换 =============

    @property
    def path_switcher(self):
        """路径切换触发器（懒加载）"""
        if not hasattr(self, "_path_switcher") or self._path_switcher is None:
            from history_footnote.chapter.path_switcher import PathSwitcher
            self._path_switcher = PathSwitcher(self.state, self.path_registry)
        return self._path_switcher

    def check_path_events(self) -> list:
        """跑 4 触发器，返回 PathEvent 列表

        不直接修改 state，由 Coordinator 决定何时 apply
        """
        return self.path_switcher.check()

    def apply_path_events(self, events: list) -> None:
        """应用 PathEvent 列表到 state.path_state"""
        from history_footnote.chapter.path_switcher import PathSwitcher
        PathSwitcher.apply_events(self.state, events)

    def record_path_choice(self, path_id: str) -> None:
        """记录玩家最近一次选择（供触发器 1 检测）"""
        recent = getattr(self.state, "recent_path_choices", []) or []
        recent.append(path_id)
        # 只保留最近 5 次
        self.state.recent_path_choices = recent[-5:]

    # ============= 🆕 v2.8.0 段二 LLM 蓝图生成 =============

    def convert_llm_to_blueprint(
        self,
        llm_output: dict,
        chapter_id: int = None,
        player_build: str = None,
    ) -> "ChapterBlueprint":
        """LLM JSON → ChapterBlueprint（带校验+兑底+Build 分化）

        段二 W6 完整流程：
        1. 解析元属性（从 chapter_id 或 llm_output）
        2. schema_converter 转换（含节点裁剪）
        3. validator 校验
        4. 校验失败 → fallback 兑底（内容保留+结构换默认）
        5. 🆕 v2.8.0 段四 W14：Build 分化（按 player_build 覆盖 node.scene/options）
        6. 返回最终 Blueprint

        Args:
            llm_output: LLM 生成的 dict
            chapter_id: 章节序号（从 llm_output.meta.chapter_id 也可读）
            player_build: 玩家 Build（默认从 state.player_build 读）

        Returns:
            ChapterBlueprint 实例
        """
        from history_footnote.chapter.types import ChapterMeta
        from history_footnote.chapter.schema_converter import SchemaConverter
        from history_footnote.chapter.validator import ChapterValidator
        from history_footnote.chapter.fallback import ChapterFallback

        # 1. 解析元属性
        if chapter_id is None:
            chapter_id = llm_output.get("meta", {}).get("chapter_id", 1) if isinstance(llm_output, dict) else 1
        chapter_meta = self.resolve_chapter_meta(chapter_id)

        # 段四 W14：默认从 state 读 player_build
        if player_build is None:
            player_build = getattr(self.state, "player_build", "") or ""

        # 2. schema 转换
        converter = SchemaConverter(self.era_config or {})
        try:
            blueprint = converter.convert(llm_output, chapter_meta)
        except ValueError as e:
            _LOG.error("SchemaConverter 失败: %s，直接兑底", e)
            blueprint = ChapterFallback.fallback(llm_output, chapter_meta, [str(e)])

        # 3. 校验
        validator = ChapterValidator(self.era_config or {})
        errors = validator.validate(llm_output)

        # 4. 兑底（如果校验失败）
        if errors:
            blueprint = ChapterFallback.fallback(llm_output, chapter_meta, errors)

        # 5. 段四 W14：Build 分化
        if player_build:
            converter.apply_build_differentiation(blueprint, llm_output, player_build)

        return blueprint

    # ============= 🆕 v2.8.0 段二 W7 Prompt 上下文 =============

    def build_prompt_context(self, chapter_id: int) -> dict:
        """构建喂给 LLM 的完整 prompt 上下文

        段二 W7：4 个上下文区 + 4 条 focus_points 规则
        喂给 LLM → 生成 llm_output → 调 convert_llm_to_blueprint

        Args:
            chapter_id: 章节序号

        Returns:
            dict: 完整上下文（chapter_meta / chapter_history / focus_points / player / available_*）
        """
        from history_footnote.chapter.prompt_builder import ChapterPromptBuilder
        chapter_meta = self.resolve_chapter_meta(chapter_id)
        builder = ChapterPromptBuilder(self.state, self.era_config or {})
        return builder.build(chapter_meta)

    # ============= 章节初始化 =============

    def init_chapter(self, chapter_id: int) -> "ChapterBlueprint":
        """初始化章节（首次进入时调用）"""
        blueprint = self.load_blueprint(chapter_id)
        cs = self.state.chapter_state
        cs.current_chapter = chapter_id
        cs.current_node = 1
        cs.chapter_start_round = self.state.round_number
        cs.blueprint = blueprint.to_dict()
        cs.last_closure_status = "INIT"
        # 🆕 v2.8.0 段三 W13：标记章节刚初始化（PathSwitcher 触发器 4 用）
        cs.just_initialized = True
        return blueprint

    # ============= 收束查询 =============

    def check_closure(self) -> str:
        """查询当前收束状态

        优先级：
        1. 如果刚初始化（last_closure_status == "INIT" 且章节第 1 回合）→ 返回 INIT
        2. 否则调用 closure.check() 计算新状态
        """
        cs = self.state.chapter_state
        # 刚初始化那一回合保持 INIT 状态
        if cs.last_closure_status == "INIT" and cs.chapter_start_round == self.state.round_number:
            return "INIT"
        status = self.closure.check()
        cs.last_closure_status = status
        return status

    # ============= 章节信息查询 =============

    def get_chapter_info(self) -> dict:
        """获取当前章节信息"""
        cs = self.state.chapter_state
        blueprint_dict = cs.blueprint or {}
        nodes = blueprint_dict.get("nodes", [])
        return {
            "current_chapter": cs.current_chapter,
            "current_node": cs.current_node,
            "total_nodes": len(nodes) if nodes else 4,
            "chapter_title": blueprint_dict.get("chapter_title", ""),
            "chapter_subtitle": blueprint_dict.get("chapter_subtitle", ""),
            "rounds_in_chapter": self.closure._rounds_in_chapter(),
            "last_closure_status": cs.last_closure_status,
        }

    def get_chapter_history(self) -> list:
        return list(self.state.chapter_state.chapter_history)

    def get_progress_text(self) -> str:
        """获取章节进度文本（前端展示用）"""
        info = self.get_chapter_info()
        if info["current_chapter"] == 0:
            return "未进入章节"
        title = info["chapter_title"]
        title_short = title.split("·")[-1].strip() if "·" in title else title
        return f"第 {info['current_chapter']} 章 · {title_short} · 节点 {info['current_node']}/{info['total_nodes']}"
