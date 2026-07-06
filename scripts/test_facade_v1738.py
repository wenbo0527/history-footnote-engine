"""🆕 v1.7.38 Game Engine Facade + Wiki cache 静态测试"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
GEF = ROOT / "src/history_footnote/game_engine_facade.py"
GL = ROOT / "src/history_footnote/game_loop.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_facade_class():
    print("[1/7] GameEngineFacade 类 + 8 核心方法")
    src = GEF.read_text(encoding="utf-8")
    methods = [
        "process_player_input",
        "get_state_summary",
        "get_event_history",
        "get_quest_summary",
        "get_drama_interventions",
        "search_wiki",
        "get_wiki_cache_stats",
        "save_all",
    ]
    ok = True
    for m in methods:
        ok = _step(f"  def {m}", f"def {m}" in src) and ok
    return ok


def test_wiki_cache():
    print("\n[2/7] Wiki cache 机制")
    src = GEF.read_text(encoding="utf-8")
    ok = _step("  _search_wiki_cached 方法", "def _search_wiki_cached" in src) and _step(
        "  _wiki_cache dict", "_wiki_cache" in src
    ) and _step(
        "  LRU eviction", "keys_to_delete" in src
    ) and _step(
        "  hit rate 统计", "hit_rate" in src
    )
    return ok


def test_process_player_input_e2e():
    print("\n[3/7] process_player_input 端到端")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.cash = 5.0
    facade = GameEngineFacade(s, era_config={})

    inputs = ["我织了一匹湖绫", "我搭船去苏州", "我回家告诉沈氏"]
    ok = True
    for inp in inputs:
        result = facade.process_player_input(inp)
        verb = result["player_action"].verb
        events = [e["id"] for e in result["action_result"].events]
        wiki = len(result["wiki_fragments"])
        ok = _step(f"  '{inp[:10]}...' verb={verb}, events={events}, wiki={wiki}", verb != "UNKNOWN") and ok
    return ok


def test_state_summary():
    print("\n[4/7] get_state_summary 9 字段")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.cash = 5.0
    facade = GameEngineFacade(s, era_config={})
    summary = facade.get_state_summary()
    expected = [
        "cash", "debt", "city", "items_count", "persons_count",
        "round_number", "triggered_events", "completed_quests", "active_quests",
        "drama_ir", "bus_stats",
    ]
    ok = True
    for k in expected:
        ok = _step(f"  {k}", k in summary) and ok
    return ok


def test_wiki_cache_hit():
    print("\n[5/7] Wiki cache 命中")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    facade = GameEngineFacade(s, era_config={})
    facade.search_wiki("苏州码头")
    facade.search_wiki("苏州码头")  # hit
    facade.search_wiki("杭州西湖")  # miss
    stats = facade.get_wiki_cache_stats()
    ok = _step(f"  cache_size=2 (期望 2)", stats["cache_size"] == 2) and _step(
        f"  hit_rate ≥ 0.33 (实际 {stats['hit_rate']:.2f})", stats["hit_rate"] >= 0.33
    )
    return ok


def test_game_loop_uses_facade():
    print("\n[6/7] game_loop 用 facade")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  game_loop 创建 GameEngineFacade + _bind_facade",
        "GameEngineFacade(self.state, era_config)" in src
        and "_bind_facade" in src
        and "self.engine = " in src,
    )


def test_subsystem_count():
    print("\n[7/7] 架构简化验证（game_loop 引用子系统数）")
    src = GL.read_text(encoding="utf-8")
    # 计算 game_loop 中 self.event_bus / self.drama_manager / self.quest_system 直接引用
    n_event_bus = src.count("self.event_bus")
    n_drama = src.count("self.drama_manager")
    n_quest = src.count("self.quest_system")
    n_engine = src.count("self.engine")
    print(f"  self.event_bus 引用: {n_event_bus}")
    print(f"  self.drama_manager 引用: {n_drama}")
    print(f"  self.quest_system 引用: {n_quest}")
    print(f"  self.engine 引用: {n_engine}（新增 facade）")
    return _step(
        f"  facade 已绑定（self.engine 出现 ≥ 1）", n_engine >= 1
    )


if __name__ == "__main__":
    print("=== v1.7.38 Game Engine Facade 静态测试 ===\n")
    ok1 = test_facade_class()
    ok2 = test_wiki_cache()
    ok3 = test_process_player_input_e2e()
    ok4 = test_state_summary()
    ok5 = test_wiki_cache_hit()
    ok6 = test_game_loop_uses_facade()
    ok7 = test_subsystem_count()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7]):
        print("\n🎉 7 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=}")
        sys.exit(1)
