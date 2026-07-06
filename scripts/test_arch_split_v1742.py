"""🆕 v1.7.42 架构拆分（state_ref_helpers + DM nodes + save/load）"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SRH = ROOT / "src/history_footnote/state_ref_helpers.py"
DAN = ROOT / "src/history_footnote/dm_agent/nodes/__init__.py"
GEF = ROOT / "src/history_footnote/game_engine_facade.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_state_ref_helpers():
    print("[1/6] state_ref_helpers 5 hint + 通用 set_slot")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.state_ref_helpers import DMStateRefHelpers

    class MockLLM:
        def __init__(self):
            self._state_ref_slot_ref = [{}]

    helpers = DMStateRefHelpers(MockLLM())
    ok = True
    # 5 hint
    ok = _step("  set_slot 通用", "def set_slot" in (SRH.read_text())) and ok
    helpers.set_calendar_events("- evt")
    helpers.set_wiki_hint([{"title": "X", "content": "Y"}])
    helpers.set_drama_hint("hint")
    from history_footnote.action_resolver import PlayerAction, ActionResult
    pa = PlayerAction(raw_text="x", verb="V")
    ar = ActionResult(state_changes={}, events=[], success=True)
    helpers.set_action_context(pa, ar)
    helpers.set_random_events([{"outcome": {"description": "test"}}])
    state_ref = helpers.get_all_slots()
    expected_keys = {"calendar_events", "wiki_hint", "drama_hint", "action_context", "random_events"}
    actual_keys = set(state_ref.keys())
    ok = _step(f"  5 hint 全部注入（{len(actual_keys)}）", expected_keys.issubset(actual_keys)) and ok
    helpers.clear_all_slots()
    ok = _step(f"  clear_all_slots 后空", helpers.get_all_slots() == {}) and ok
    return ok


def test_dm_nodes_split():
    print("\n[2/6] DM Agent 5 nodes 拆分")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.dm_agent.nodes import (
        make_all_dm_nodes, extract_narrative_node, state_confirmation_node, DMState,
    )
    nodes = make_all_dm_nodes(llm_with_tools=None, state_ref={})
    expected = {"skill_orchestration", "situation_assessment", "narrative_fusion", "extract_narrative", "state_confirmation"}
    actual = set(nodes.keys())
    ok = _step(f"  5 nodes: {sorted(actual)}", actual == expected) and _step(
        f"  DMState TypedDict 字段", "narrative" in DMState.__annotations__ and "wiki_hint" in DMState.__annotations__
    )
    # extract_narrative_node
    state = {"narrative": "<narrative>你搭船去苏州。</narrative>"}
    result = extract_narrative_node(state)
    ok = _step(f"  extract_narrative 提取 {result['narrative'][:10]}", result["narrative"] == "你搭船去苏州。") and ok
    return ok


def test_save_load_to_disk():
    print("\n[3/6] facade save_to_disk / load_from_disk")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.cash = 5.0
    s.current_city = "suzhou"
    s.round_number = 10
    facade = GameEngineFacade(s, era_config={})
    facade.record_perf("llm_call", 1500)
    facade.record_perf("process_call", 100)

    tmp_path = Path(tempfile.mkdtemp(prefix="hf_save_")) / "engine.json"
    ok = _step(f"  save_to_disk: {tmp_path.name}", facade.save_to_disk(str(tmp_path))) and _step(
        f"  文件存在", tmp_path.exists()
    )

    # 修改状态
    s.cash = 0.0
    s.current_city = "hangzhou"
    s.round_number = 1

    ok = _step(f"  load_from_disk 还原", facade.load_from_disk(str(tmp_path))) and _step(
        f"  cash 恢复: 5.00 (实际 {s.cash:.2f})", abs(s.cash - 5.0) < 0.01
    ) and _step(
        f"  city 恢复: suzhou (实际 {s.current_city})", s.current_city == "suzhou"
    ) and _step(
        f"  round 恢复: 10 (实际 {s.round_number})", s.round_number == 10
    ) and _step(
        f"  perf 恢复: 2 calls (实际 {facade._perf['llm_calls']})", facade._perf["llm_calls"] == 1
    )
    return ok


def test_process_perf_tracked():
    print("\n[4/6] process_player_input 性能记录")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.cash = 5.0
    facade = GameEngineFacade(s, era_config={})
    facade.process_player_input("我织了一匹湖绫")
    facade.process_player_input("我搭船去苏州")
    perf = facade.get_extended_perf_stats()
    ok = _step(f"  process.calls=2 (实际 {perf['process']['calls']})", perf['process']['calls'] == 2) and _step(
        f"  process.avg_ms > 0 (实际 {perf['process']['avg_ms']:.2f})", perf['process']['avg_ms'] > 0
    )
    return ok


def test_files_separated():
    print("\n[5/6] 文件拆分（game_loop / dm_agent / facade）")
    ok = _step(
        "  state_ref_helpers.py 存在",
        SRH.exists(),
    ) and _step(
        "  dm_agent/nodes/ 目录存在",
        DAN.exists() and (DAN.parent / "nodes.py").exists(),
    ) and _step(
        "  game_engine_facade.py 含 save_to_disk + load_from_disk",
        "def save_to_disk" in GEF.read_text() and "def load_from_disk" in GEF.read_text(),
    )
    return ok


def test_e2e_full_workflow():
    print("\n[6/6] 端到端：state_ref helpers + DM nodes + facade")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade
    from history_footnote.state_ref_helpers import DMStateRefHelpers
    from history_footnote.dm_agent.nodes import extract_narrative_node

    # 1. 创建 facade
    s = GameState()
    s.cash = 5.0
    facade = GameEngineFacade(s, era_config={})

    # 2. 模拟 LLM
    class MockLLM:
        def __init__(self):
            self._state_ref_slot_ref = [{}]
    mock_llm = MockLLM()

    # 3. 用 state_ref_helpers 注入
    helpers = DMStateRefHelpers(mock_llm)
    helpers.set_wiki_hint([{"title": "苏州", "content": "阊门码头..."}])
    helpers.set_drama_hint("玩家放松")
    ok = _step(f"  state_ref 有 wiki_hint", "wiki_hint" in helpers.get_all_slots()) and _step(
        f"  state_ref 有 drama_hint", "drama_hint" in helpers.get_all_slots()
    )

    # 4. 用 DM node 提取
    state = {"narrative": "<narrative>你搭船去苏州。</narrative>"}
    result = extract_narrative_node(state)
    ok = _step(f"  DM node 提取: {result['narrative'][:10]}", result["narrative"] == "你搭船去苏州。") and ok

    # 5. facade 跑 + 监控
    facade.process_player_input("我搭船去苏州")
    perf = facade.get_extended_perf_stats()
    ok = _step(f"  facade.process.calls > 0", perf['process']['calls'] > 0) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.42 架构拆分 静态测试 ===\n")
    ok1 = test_state_ref_helpers()
    ok2 = test_dm_nodes_split()
    ok3 = test_save_load_to_disk()
    ok4 = test_process_perf_tracked()
    ok5 = test_files_separated()
    ok6 = test_e2e_full_workflow()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
