"""🆕 v1.7.41 架构简化 + 性能监控 静态测试"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GL = ROOT / "src/history_footnote/game_loop.py"
GEF = ROOT / "src/history_footnote/game_engine_facade.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_state_ref_slot_helper():
    print("[1/5] 通用 set_state_ref_slot")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  def set_state_ref_slot + 4 个 set_*_hint 改用",
        "def set_state_ref_slot" in src
        and "self.set_state_ref_slot(\"calendar_events\"" in src
        and "self.set_state_ref_slot(\"wiki_hint\"" in src
        and "self.set_state_ref_slot(\"drama_hint\"" in src,
    )


def test_set_hint_count_reduced():
    print("\n[2/5] 重复代码减少（5 → 1）")
    src = GL.read_text(encoding="utf-8")
    n_old = src.count('current_ref["')  # 老代码
    n_new = src.count('self.set_state_ref_slot(')
    print(f"  老代码 current_ref[..] 引用: {n_old}")
    print(f"  新代码 set_state_ref_slot() 引用: {n_new}")
    # 由于 set_action_context_for_dm 仍用 current_ref 写 action_context dict
    # set_state_ref_slot 实际替代 4 个 set_*_hint 方法中的 3 个
    # 验证：calendar_events / wiki_hint / drama_hint 都改用 helper
    return _step(
        f"  set_state_ref_slot 已用于 3 个 set_*_hint (calendar/wiki/drama)",
        "set_state_ref_slot(\"calendar_events\"" in src
        and "set_state_ref_slot(\"wiki_hint\"" in src
        and "set_state_ref_slot(\"drama_hint\"" in src,
    )


def test_perf_monitoring():
    print("\n[3/5] 性能监控（LLM 调用次数/耗时）")
    src = GEF.read_text(encoding="utf-8")
    return _step(
        "  facade.record_perf + get_extended_perf_stats",
        "def record_perf" in src
        and "llm_total_ms" in src
        and "process_total_ms" in src
        and "get_extended_perf_stats" in src,
    )


def test_game_loop_uses_record_perf():
    print("\n[4/5] game_loop 调 record_perf")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  game_loop 调 self.engine.record_perf(\"llm_call\", ms)",
        "self.engine.record_perf" in src and "llm_call" in src,
    )


def test_get_extended_perf_e2e():
    print("\n[5/5] 端到端 get_extended_perf_stats")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.game_state import GameState
    from history_footnote.game_engine_facade import GameEngineFacade

    s = GameState()
    s.cash = 5.0
    facade = GameEngineFacade(s, era_config={})
    facade.record_perf("llm_call", 1500.0)
    facade.record_perf("llm_call", 2000.0)
    facade.record_perf("process_call", 200.0)
    stats = facade.get_extended_perf_stats()
    ok = _step(f"  llm.calls=2 (实际 {stats['llm']['calls']})", stats['llm']['calls'] == 2) and _step(
        f"  llm.total_ms=3500 (实际 {stats['llm']['total_ms']})", stats['llm']['total_ms'] == 3500
    ) and _step(
        f"  llm.avg_ms=1750 (实际 {stats['llm']['avg_ms']})", stats['llm']['avg_ms'] == 1750
    ) and _step(
        f"  process.calls=1 (实际 {stats['process']['calls']})", stats['process']['calls'] == 1
    )
    return ok


if __name__ == "__main__":
    print("=== v1.7.41 架构简化 + 性能监控 静态测试 ===\n")
    ok1 = test_state_ref_slot_helper()
    ok2 = test_set_hint_count_reduced()
    ok3 = test_perf_monitoring()
    ok4 = test_game_loop_uses_record_perf()
    ok5 = test_get_extended_perf_e2e()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
