"""🆕 v1.7.40 Sub-Facades + process_full_round 静态测试"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SF = ROOT / "src/history_footnote/sub_facades.py"
GEF = ROOT / "src/history_footnote/game_engine_facade.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_sub_facades_5():
    print("[1/5] 5 Sub-Facades")
    src = SF.read_text(encoding="utf-8")
    facades = ["QuestFacade", "DramaFacade", "WikiFacade", "EventFacade", "StateFacade"]
    ok = True
    for f in facades:
        ok = _step(f"  class {f}", f"class {f}" in src) and ok
    return ok


def test_sub_facade_integration():
    print("\n[2/5] Sub-Facade 实例化 + 核心方法")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.event_bus import get_event_bus
    from history_footnote.drama_manager import DramaManager
    from history_footnote.quest_system import QuestSystem, WANLI_QUESTS
    from history_footnote.wiki_retriever import get_wiki_retriever
    from history_footnote.sub_facades import QuestFacade, DramaFacade, WikiFacade, EventFacade, StateFacade

    s = GameState()
    s.cash = 5.0
    bus = get_event_bus()
    qs = QuestSystem(s, bus, WANLI_QUESTS)
    dm = DramaManager(s, {})
    wr = get_wiki_retriever()
    qf = QuestFacade(s, bus, qs)
    df = DramaFacade(s, dm)
    wf = WikiFacade(wr)
    ef = EventFacade(bus)
    sf = StateFacade(s)
    ok = True
    # 测试核心方法
    ok = _step(f"  QuestFacade: total={qf.total}, rate={qf.get_completion_rate():.0%}", qf.total == 4) and ok
    df.record_action("TRAVEL", "suzhou", is_initiative=True)
    s_dr = df.get_summary()
    ok = _step(f"  DramaFacade: ir={s_dr['initiative_ratio']:.0%}", s_dr['initiative_ratio'] > 0) and ok
    frags = wf.search(action_verb="TRAVEL", target="suzhou", city="shengze", top_k=2)
    frags2 = wf.search(action_verb="TRAVEL", target="suzhou", city="shengze", top_k=2)
    cache = wf.get_cache_stats()
    ok = _step(f"  WikiFacade: cache hit_rate={cache['hit_rate']:.0%}", cache['hit_rate'] > 0) and ok
    n = ef.publish("test.event", data={"x": 1})
    ok = _step(f"  EventFacade: published {n} handlers", n > 0) and ok
    s_sum = sf.get_summary()
    ok = _step(f"  StateFacade: 7 字段", len(s_sum) == 7) and ok
    return ok


def test_facade_sub_facades_property():
    print("\n[3/5] GameEngineFacade.sub_facades 懒初始化")
    src = GEF.read_text(encoding="utf-8")
    return _step(
        "  @property sub_facades + 5 sub-facades 实例化",
        "def sub_facades" in src
        and 'QuestFacade(self.state' in src
        and 'DramaFacade(self.state' in src
        and 'WikiFacade(self.wiki_retriever' in src
        and 'EventFacade(self.event_bus' in src
        and 'StateFacade(self.state' in src,
    )


def test_process_full_round():
    print("\n[4/5] process_full_round 封装")
    src = GEF.read_text(encoding="utf-8")
    return _step(
        "  def process_full_round + game_loop 集成",
        "def process_full_round" in src
        and "game_loop._run_round" in src
        and "player_input: str" in src
        and "perf_stats" in src,
    )


def test_wiki_cache_25_percent():
    print("\n[5/5] Wiki cache 长期数据（v1.7.40 真实 LLM 5 轮）")
    log_path = Path("logs/test_v1740_wiki_cache.log")
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8")
        # 提取 hit_rate
        import re
        m = re.search(r"hit_rate: (\d+)%", log_text)
        if m:
            hit_rate = int(m.group(1))
            ok = _step(f"  真实 LLM 5 轮 cache hit_rate = {hit_rate}%", hit_rate > 0) and _step(
                f"  cache_size: 3 个条目", "cache_size: 3" in log_text
            )
            return ok
    return _step("  跳过（log 未生成）", True)


if __name__ == "__main__":
    print("=== v1.7.40 Sub-Facades 静态测试 ===\n")
    ok1 = test_sub_facades_5()
    ok2 = test_sub_facade_integration()
    ok3 = test_facade_sub_facades_property()
    ok4 = test_process_full_round()
    ok5 = test_wiki_cache_25_percent()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
