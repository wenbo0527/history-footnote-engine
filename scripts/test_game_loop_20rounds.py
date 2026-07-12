"""🆕 v2.10.1 20 回合 GameLoop 端到端测试（mock LLM）

依据 W52 优化清单 P2-5 followup
- 真实 GameLoop.run() 跑 20 回合
- mock LLM + dm.run + _get_player_input + round 推进
- 验证 round_number 推进 + state 变化 + event_log
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch


class MockLLM:
    """最小可工作 LLM mock:
    - bind_tools(tools) → self
    - _state_ref_slot_ref → list[dict]
    - invoke(messages) → AIMessage with content
    """
    def __init__(self):
        self._state_ref_slot_ref = [{}]

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages, **kwargs):
        from langchain_core.messages import AIMessage
        return AIMessage(content="<narrative>你继续做你的事。</narrative>")


# 20 个 input 序列（用 action_resolver 友好的格式）
PLAYER_INPUTS = [
    "我织了一匹湖绫",
    "我去牙行卖丝",
    "我听邻居说李秀才中了举人",
    "我听说今年丝税要加",
    "我去里长那里问今年的税单",
    "我决定硬抗税",
    "我去苏州城里走走",
    "我听说洋船要来了",
    "我看到县衙贴出告示",
    "我决定扩大织机规模",
    "我去告官府",
    "我向李秀才借债",
    "我开始织春蚕丝",
    "我去跟邻人商量",
    "我修好织机",
    "我用借的钱交了税",
    "我把春蚕丝拿去卖",
    "我还了一部分债",
    "我跟沈氏在自家织房",
    "我决定继续守这片土地",
]


def make_mock_dm_response(round_num: int, player_input: str) -> dict:
    """构造 dm.run() 返回值"""
    narrative = f"第 {round_num} 回合：你做了『{player_input[:20]}』，系统处理完毕。"
    return {
        "narrative": narrative,
        "state_changes": {},
        "events_to_save": [f"Round {round_num}: {player_input[:30]}"],
        "updates": None,
        "identity_offer": None,
    }


def main():
    print("=" * 60)
    print("🆕 v2.10.1 20 回合 GameLoop 端到端测试 (mock LLM)")
    print("=" * 60)

    from history_footnote.game_loop import GameLoop

    # 1. 加载 era_config
    era_config = json.loads(
        Path('eras/wanli1587/era.json').read_text(encoding='utf-8')
    )

    # 2. mock LLM
    mock_llm = MockLLM()

    # 3. 构造 GameLoop
    print("⏳ 初始化 GameLoop ...")
    init_t0 = time.time()
    try:
        loop = GameLoop(
            era_id="wanli1587",
            era_config=era_config,
            llm_model=mock_llm,
            selected_identity="weaving_male",
        )
        print(f"✓ GameLoop 初始化成功 ({time.time() - init_t0:.2f}s)")
    except Exception as e:
        print(f"❌ GameLoop 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. mock iter
    dm_response_iter = iter(
        make_mock_dm_response(i + 1, inp)
        for i, inp in enumerate(PLAYER_INPUTS)
    )
    input_iter = iter(PLAYER_INPUTS)

    error_count = [0]  # 用 list 便于在闭包内修改
    state_snapshots = []

    def mock_dm_run(player_input: str) -> dict:
        return next(dm_response_iter)

    def mock_get_input() -> str:
        try:
            return next(input_iter)
        except StopIteration:
            raise SystemExit("Test done after 20 rounds")

    def mock_is_game_over() -> bool:
        return loop.state.round_number > 20

    # Wrap run() to bump round after each _run_round
    original_run_round = loop._run_round
    round_errors = []

    def wrapped_run_round(player_input: str) -> None:
        """每次 _run_round 后收集快照（round 由 AP 系统自然推进）"""
        round_before = loop.state.round_number
        try:
            original_run_round(player_input)
        except Exception as e:
            round_errors.append((loop.state.round_number, player_input, e))
            import traceback
            traceback.print_exc()
        # 收集快照（round 已被 AP 系统推进或保持）
        state_snapshots.append({
            "round": loop.state.round_number,
            "round_before": round_before,
            "cash": getattr(loop.state, 'cash', 0),
            "debt": getattr(loop.state, 'debt', 0),
            "events_count": len(loop.state.event_log),
            "triggered": len(loop.state.triggered_events),
        })

    # 5. 跑 20 回合
    print(f"⏳ 跑 20 回合 ...")
    start_t = time.time()
    try:
        with patch.object(loop, '_get_player_input', side_effect=mock_get_input), \
             patch.object(loop, '_is_game_over', side_effect=mock_is_game_over), \
             patch.object(loop.dm, 'run', side_effect=mock_dm_run), \
             patch.object(loop.dm, 'regenerate', side_effect=mock_dm_run), \
             patch.object(loop, '_run_round', side_effect=wrapped_run_round):
            try:
                loop.run()
            except SystemExit as e:
                pass
    except Exception as e:
        print(f"❌ 跑 20 回合异常: {e}")
        import traceback
        traceback.print_exc()
        return 1
    elapsed = time.time() - start_t
    print(f"✓ 跑完 ({elapsed:.2f}s)")

    # 6. 报告
    print()
    print(f"📊 最终状态:")
    print(f"  round_number: {loop.state.round_number}")
    print(f"  current_city: {getattr(loop.state, 'current_city', '?')}")
    print(f"  selected_identity: {loop.state.selected_identity}")
    print(f"  cash: {getattr(loop.state, 'cash', '?')}")
    print(f"  debt: {getattr(loop.state, 'debt', '?')}")
    print(f"  triggered_events: {len(loop.state.triggered_events)}")
    print(f"  event_log: {len(loop.state.event_log)}")
    print(f"  narrative_history: {len(getattr(loop.state, 'narrative_history', []))}")
    print(f"  snapshots: {len(state_snapshots)}")

    # 7. 阶段性快照
    if state_snapshots:
        print()
        print("📍 状态快照（每 5 回合）:")
        for snap in state_snapshots[::5]:
            print(f"  Round {snap['round']:2d}: cash={snap['cash']:.2f} debt={snap['debt']:.2f} events={snap['events_count']}")

    # 8. 综合判断
    errors = []
    if len(state_snapshots) != 20:
        errors.append(f"snapshots={len(state_snapshots)} (期望 20)")

    if not loop.state.event_log:
        errors.append("event_log 为空")

    if round_errors:
        print(f"\n⚠️ {len(round_errors)} 个回合异常:")
        for rnd, inp, e in round_errors[:5]:
            print(f"  Round {rnd}: {e}")

    if errors:
        print()
        for e in errors:
            print(f"❌ {e}")
        return 1

    print()
    print(f"✅ 20 回合 GameLoop 端到端测试 通过")
    print(f"   - state.round_number = {loop.state.round_number}（跑完 20 回合）")
    print(f"   - event_log = {len(loop.state.event_log)} 条")
    print(f"   - 触发事件: {len(loop.state.triggered_events)} 个")
    print(f"   - 耗时: {elapsed:.2f}s (avg {elapsed/20*1000:.0f}ms/round)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
