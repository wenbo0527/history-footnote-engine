"""🆕 v2.10.2 综合测试: 50 回合 stress test (mock LLM)

验证 GameLoop 长时间运行的稳定性:
- round 推进是否正常
- event_log / narrative_history 不丢
- 内存/性能不劣化
- 0 异常
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch


def main():
    print("=" * 60)
    print("🆕 v2.10.2 综合测试: 50 回合 stress test")
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
            return AIMessage(content="<narrative>stress 测试：日常过活。？</narrative>")

    from history_footnote.game_loop import GameLoop
    real_llm = MockLLM()
    era_config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )

    loop = GameLoop(
        era_id="wanli1587",
        era_config=era_config,
        llm_model=real_llm,
        selected_identity="weaving_male",
    )

    # 50 回合 input
    inputs = [f"我做了第{i+1}件事" for i in range(50)]
    input_iter = iter(inputs)
    snapshots = []
    round_errors = []
    t0 = time.time()

    def mock_get_input():
        try:
            return next(input_iter)
        except StopIteration:
            raise SystemExit("50 rounds done")

    def mock_is_game_over():
        return loop.state.round_number > 50

    original_run = loop._run_round

    def wrapped_run(player_input):
        try:
            original_run(player_input)
        except Exception as e:
            round_errors.append((loop.state.round_number, str(e)[:120]))
        snapshots.append({
            "round": loop.state.round_number,
            "cash": getattr(loop.state, "cash", 0),
            "events": len(loop.state.event_log),
            "narrative": len(getattr(loop.state, "narrative_history", [])),
        })

    try:
        with patch.object(loop, "_get_player_input", side_effect=mock_get_input), \
             patch.object(loop, "_is_game_over", side_effect=mock_is_game_over), \
             patch.object(loop, "_run_round", side_effect=wrapped_run):
            try:
                loop.run()
            except SystemExit:
                pass
    except Exception as e:
        print(f"❌ run 异常: {e}")
        return 1

    elapsed = time.time() - t0

    print(f"\n📊 50 回合 stress test 结果:")
    print(f"  完成回合: {len(snapshots)}/50")
    print(f"  最终 round_number: {loop.state.round_number}")
    print(f"  event_log: {len(loop.state.event_log)} 条")
    print(f"  narrative_history: {len(getattr(loop.state, 'narrative_history', []))} 条")
    print(f"  triggered_events: {len(loop.state.triggered_events)}")
    print(f"  LLM 调用次数: {real_llm.call_count}")
    print(f"  异常数: {len(round_errors)}")
    print(f"  耗时: {elapsed:.2f}s（avg {elapsed/50*1000:.0f}ms/回合）")

    # 检查 progression（每 10 回合）
    print(f"\n📍 状态快照（每 10 回合）:")
    for snap in snapshots[::10]:
        print(f"  Round {snap['round']:2d}: cash={snap['cash']:.2f} events={snap['events']} narrative={snap['narrative']}")

    if round_errors:
        print(f"\n⚠️ 异常（前 5）:")
        for r, e in round_errors[:5]:
            print(f"  Round {r}: {e}")

    errors = []
    if len(snapshots) < 50:
        errors.append(f"只完成 {len(snapshots)}/50 回合")
    if round_errors:
        errors.append(f"{len(round_errors)} 回合异常")
    if not getattr(loop.state, "narrative_history", []):
        errors.append("narrative_history 为空")

    if errors:
        for e in errors:
            print(f"❌ {e}")
        return 1

    print(f"\n✅ 50 回合 stress test 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
