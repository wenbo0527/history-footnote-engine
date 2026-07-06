"""🆕 v1.7.39 静态测试"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GEF = ROOT / "src/history_footnote/game_engine_facade.py"
GL = ROOT / "src/history_footnote/game_loop.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_search_wiki_signature():
    print("[1/6] search_wiki 新签名（action_verb）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    facade = GameEngineFacade(s, era_config={})
    # action_verb 自动选 intent
    frags = facade.search_wiki(action_verb="TRAVEL", target="suzhou", city="shengze")
    ok = _step(f"  action_verb=TRAVEL → {len(frags)} 片段", len(frags) > 0) and _step(
        "  intent 自动推断为 route", any(f["category"] == "route" for f in frags)
    )
    return ok


def test_wiki_cache_hit():
    print("\n[2/6] Wiki cache 命中（重复调用）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    facade = GameEngineFacade(s, era_config={})
    # 3 次相同调用（应 1 miss + 2 hit）
    facade.search_wiki(action_verb="TRAVEL", target="suzhou", city="shengze")
    facade.search_wiki(action_verb="TRAVEL", target="suzhou", city="shengze")
    facade.search_wiki(action_verb="TRAVEL", target="suzhou", city="shengze")
    stats = facade.get_wiki_cache_stats()
    ok = _step(f"  cache_size=1（key 相同）", stats["cache_size"] == 1) and _step(
        f"  hit_rate ≥ 0.66 (实际 {stats['hit_rate']:.2f})", stats["hit_rate"] >= 0.66
    )
    return ok


def test_summarize_fragments():
    print("\n[3/6] summarize_fragments（截断）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    facade = GameEngineFacade(s, era_config={})
    long_fragments = [
        {"title": "test1", "content": "a" * 1000, "category": "gossip", "city": "shengze", "score": 1.0},
        {"title": "test2", "content": "b" * 200, "category": "gossip", "city": "shengze", "score": 1.0},
    ]
    summarized = facade.summarize_fragments(long_fragments)
    ok = _step(f"  返回 {len(summarized)} 片段", len(summarized) == 2) and _step(
        f"  长片段被截断（原 1000 → {len(summarized[0]['content'])}）", summarized[0]["_summarized"] is True
    ) and _step(
        f"  短片段未截断（原 200 → {len(summarized[1]['content'])}）", summarized[1].get("_summarized") is None or not summarized[1].get("_summarized")
    )
    return ok


def test_process_narrative_input():
    print("\n[4/6] process_narrative_input（解析 LLM 输出）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    facade = GameEngineFacade(s, era_config={})
    llm_output = """<narrative>你搭船去苏州。阊门码头上岸。</narrative>
<events>
  <event id="discover.item" name="湖绫" type="silk_bolt" owner="shengze" qty="1" description="test"/>
</events>"""
    result = facade.process_narrative_input(llm_output)
    ok = _step(f"  返回 events_applied: {result['events_applied']}", result["events_applied"] >= 1) and _step(
        f"  narrative 提取: '{result['narrative'][:30]}...'", "阊门" in result["narrative"]
    )
    return ok


def test_get_performance_stats():
    print("\n[5/6] get_performance_stats（4 维度监控）")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    facade = GameEngineFacade(s, era_config={})
    stats = facade.get_performance_stats()
    ok = _step("  wiki_cache 维度", "wiki_cache" in stats) and _step(
        "  drama 维度", "drama" in stats
    ) and _step(
        "  event_bus 维度", "event_bus" in stats
    ) and _step(
        "  quest 维度", "quest" in stats
    )
    return ok


def test_game_loop_uses_engine_search_wiki():
    print("\n[6/6] game_loop 用 engine.search_wiki（cache 生效）")
    src = GL.read_text(encoding="utf-8")
    ok = _step(
        "  game_loop 调 self.engine.search_wiki（替代 search_wiki_by_action）",
        "self.engine.search_wiki" in src and "search_wiki_by_action" not in src
    ) and _step(
        "  query/action_verb/target/city 参数",
        "query=player_action.raw_text" in src and "action_verb=player_action.verb" in src,
    )
    return ok


if __name__ == "__main__":
    print("=== v1.7.39 Facade 扩展静态测试 ===\n")
    ok1 = test_search_wiki_signature()
    ok2 = test_wiki_cache_hit()
    ok3 = test_summarize_fragments()
    ok4 = test_process_narrative_input()
    ok5 = test_get_performance_stats()
    ok6 = test_game_loop_uses_engine_search_wiki()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
