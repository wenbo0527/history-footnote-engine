"""v2.10.2 综合测试: 性能 + 内存测试

50 回合 mock + 内存监测,确保长时间运行不漏内存
"""
import json
import sys
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch


def main():
    print("=" * 60)
    print("🆕 v2.10.2 性能 + 内存测试")
    print("=" * 60)

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import Runnable

    class MockLLM(Runnable):
        def __init__(self):
            self._state_ref_slot_ref = [{}]
            self.call_count = 0
        def bind_tools(self, tools, **kwargs):
            return self
        def invoke(self, input, **kwargs):
            self.call_count += 1
            return AIMessage(content="<narrative>perf 测试：日常过活。？</narrative>")

    from history_footnote.game_loop import GameLoop
    real_llm = MockLLM()
    era_config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )

    # 启动内存监测
    tracemalloc.start()
    snapshot_start = tracemalloc.take_snapshot()

    loop = GameLoop(
        era_id="wanli1587",
        era_config=era_config,
        llm_model=real_llm,
        selected_identity="weaving_male",
    )

    # 50 回合
    inputs = [f"测试动作{i+1}" for i in range(50)]
    input_iter = iter(inputs)
    times = []

    def mock_get_input():
        try:
            return next(input_iter)
        except StopIteration:
            raise SystemExit("done")

    def mock_is_game_over():
        return loop.state.round_number > 50

    original_run = loop._run_round

    def wrapped_run(player_input):
        t0 = time.perf_counter()
        original_run(player_input)
        times.append((time.perf_counter() - t0) * 1000)

    with patch.object(loop, "_get_player_input", side_effect=mock_get_input), \
         patch.object(loop, "_is_game_over", side_effect=mock_is_game_over), \
         patch.object(loop, "_run_round", side_effect=wrapped_run):
        try:
            loop.run()
        except SystemExit:
            pass

    # 内存快照
    snapshot_end = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # 报告
    print(f"\n📊 性能报告:")
    print(f"  50 回合: 总耗时 {sum(times):.0f}ms (avg {sum(times)/50:.1f}ms/round)")
    print(f"  最快回合: {min(times):.0f}ms")
    print(f"  最慢回合: {max(times):.0f}ms")
    print(f"  LLM 调用: {real_llm.call_count} 次")

    # 内存 top diffs
    diffs = snapshot_end.compare_to(snapshot_start, 'lineno')
    print(f"\n📊 内存报告 (Top 5 增长):")
    for stat in diffs[:5]:
        print(f"  {stat}")

    # 内存总量
    current, peak = tracemalloc.get_traced_memory()
    print(f"\n📊 内存峰值: {peak / 1024 / 1024:.2f} MB")

    # event_log 大小
    print(f"\n📊 状态规模:")
    print(f"  event_log: {len(loop.state.event_log)} 条")
    print(f"  narrative_history: {len(getattr(loop.state, 'narrative_history', []))} 条")
    print(f"  triggered_events: {len(loop.state.triggered_events)} 个")
    print(f"  round_number: {loop.state.round_number}")
    print(f"  current_date: {loop.state.current_date}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
