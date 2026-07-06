"""🆕 v1.7.43 体验优化 静态测试"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
LC = ROOT / "src/history_footnote/llm_cache.py"
SRH = ROOT / "src/history_footnote/state_ref_helpers.py"
DAN = ROOT / "src/history_footnote/dm_agent/nodes/nodes.py"
GEF = ROOT / "src/history_footnote/game_engine_facade.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_llm_cache():
    print("[1/5] LLM Cache 命中")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.llm_cache import LLMCache

    cache = LLMCache(max_size=10)
    state_sig = {"round": 1, "city": "shengze"}
    hints = {"wiki_hint": "苏州"}
    ok = True
    ok = _step("  1. miss", cache.get("x", state_sig, hints) is None) and ok
    cache.put("x", state_sig, hints, {"narrative": "test"})
    r = cache.get("x", state_sig, hints)
    ok = _step(f"  2. hit: from_cache={r.get('_from_cache')}", r and r.get("_from_cache") is True) and ok
    # 改 state → miss
    state_sig2 = {"round": 2}
    ok = _step("  3. 改 state → miss", cache.get("x", state_sig2, hints) is None) and ok
    # stats
    stats = cache.get_stats()
    ok = _step(f"  4. stats: hit_rate={stats['hit_rate']:.0%}", stats["hits"] == 1 and stats["misses"] == 2) and ok
    return ok


def test_unified_context():
    print("\n[2/5] build_unified_context 合并 4 hint")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.state_ref_helpers import DMStateRefHelpers
    from history_footnote.action_resolver import PlayerAction, ActionResult

    class MockLLM:
        def __init__(self):
            self._state_ref_slot_ref = [{}]

    helpers = DMStateRefHelpers(MockLLM())
    pa = PlayerAction(raw_text="x", verb="V")
    ar = ActionResult(state_changes={}, events=[], success=True)
    helpers.set_action_context(pa, ar)
    helpers.set_wiki_hint([{"title": "苏州", "content": "阊门..."}])
    helpers.set_drama_hint("放松")
    helpers.set_calendar_events("evt.little_ice_age")

    unified = helpers.build_unified_context()
    ok = _step(f"  包含【玩家动作】", "【玩家动作】" in unified) and _step(
        f"  包含【历史参考】", "【历史参考】" in unified
    ) and _step(
        f"  包含【节奏干预】", "【节奏干预】" in unified
    ) and _step(
        f"  包含【时代背景】", "【时代背景】" in unified
    ) and _step(
        f"  长度: {len(unified)} 字符", len(unified) > 50
    )
    return ok


def test_smart_node_skip():
    print("\n[3/5] DM 节点智能跳过")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.dm_agent.nodes import (
        should_skip_narrative_fusion, smart_narrative_fusion_node
    )

    ok = True
    # 已存在 narrative → skip
    state1 = {"narrative": "你已经织好了一匹湖绫，丝光莹润。" * 5, "player_input": "我又织了"}
    ok = _step("  narrative 已存在 → skip", should_skip_narrative_fusion(state1)) and ok
    # IDLE → skip
    state2 = {"narrative": "", "player_input": "闲坐"}
    ok = _step("  player_input=闲坐 → skip", should_skip_narrative_fusion(state2)) and ok
    # 新输入 → not skip
    state3 = {"narrative": "", "player_input": "我搭船去苏州"}
    ok = _step("  新输入 → not skip", not should_skip_narrative_fusion(state3)) and ok
    # smart node
    smart = smart_narrative_fusion_node(None, None)
    r1 = smart(state1)
    r3 = smart(state3)
    ok = _step(f"  smart skip 后 _llm_skipped=True", r1.get("_llm_skipped") is True) and _step(
        f"  smart 不 skip _llm_skipped=False", r3.get("_llm_skipped") is False
    )
    return ok


def test_recent_events_for_display():
    print("\n[4/5] get_recent_events_for_display")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.round_number = 5
    s.cash = 5.0
    s.triggered_events = ["evt.guoben_dispute"]
    facade = GameEngineFacade(s, era_config={})
    events = facade.get_recent_events_for_display(limit=10)
    ok = _step(f"  返回 {len(events)} 事件", isinstance(events, list))
    types = [e.get("type") for e in events]
    ok = _step(f"  包含 major_event: {('major_event' in types)}", "major_event" in types) and ok
    # 完成一个任务（接受已有任务，然后改 status）
    facade.quest_system.accept_quest("quest.first_silk")
    facade.quest_system.quests["quest.first_silk"].status = "completed"
    events2 = facade.get_recent_events_for_display(limit=10)
    types2 = [e.get("type") for e in events2]
    ok = _step(f"  任务完成 → quest_completed", "quest_completed" in types2) and ok
    return ok


def test_files_separated():
    print("\n[5/5] 文件拆分（llm_cache + smart_node）")
    return _step(
        "  llm_cache.py 存在", LC.exists()
    ) and _step(
        "  state_ref_helpers.build_unified_context 存在", "def build_unified_context" in SRH.read_text()
    ) and _step(
        "  DM nodes 智能跳过", "should_skip_narrative_fusion" in DAN.read_text()
    ) and _step(
        "  facade get_recent_events_for_display", "get_recent_events_for_display" in GEF.read_text()
    )


if __name__ == "__main__":
    print("=== v1.7.43 体验优化 静态测试 ===\n")
    ok1 = test_llm_cache()
    ok2 = test_unified_context()
    ok3 = test_smart_node_skip()
    ok4 = test_recent_events_for_display()
    ok5 = test_files_separated()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
