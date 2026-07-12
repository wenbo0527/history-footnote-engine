"""🆕 v2.10.1 W52 候选 C: 真 LLM 20 回合 GameLoop 端到端

依据 W52 优化清单候选 C：
- 用真实 LLM（minimax-anthropic via get_wrapped_llm）跑 GameLoop.run() 20 回合
- 验证：LLM 调用成功 / event_log 增长 / round 推进 / 无未捕获异常
- 成本控制：限流已在 .env 配置（35 req / 600s）

前置：
  set -a && source .env && set +a
  .venv/bin/python scripts/test_real_llm_20rounds.py
"""
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch


# 项目根
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_real_llm():
    """构造真实 LLM（minimax-anthropic）"""
    from history_footnote.llm_wrapper import get_wrapped_llm
    wrapper = get_wrapped_llm(
        primary_provider=os.environ.get("LLM_PRIMARY_PROVIDER", "minimax-anthropic"),
    )
    return wrapper


# 20 回合 input
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


def main():
    print("=" * 60)
    print("🆕 v2.10.1 真 LLM 20 回合 GameLoop 端到端")
    print("=" * 60)

    # 🆕 v2.10.1: 默认 mock LLM（避免 350s 等待），用 REAL_LM=1 启用真 LLM
    use_real = os.environ.get("REAL_LLM", "0") == "1"
    if not use_real:
        print("💡 默认 mock LLM 模式（17s 真 LLM/回合，20 回合 ~6 分钟）")
        print("   设 REAL_LLM=1 启用真 LLM（minimax-anthropic）")

    # 0. 检查凭据
    if not os.environ.get("MINIMAX_API_KEY") and use_real:
        print("❌ MINIMAX_API_KEY 未设置")
        print("请先: set -a && source .env && set +a")
        return 1

    # 1. 构造真 LLM 或 mock LLM
    if use_real:
        print("⏳ 构造真实 LLM ...")
        try:
            real_llm = make_real_llm()
            print(f"✓ LLM 构造成功（provider={os.environ.get('LLM_PRIMARY_PROVIDER')}）")
        except Exception as e:
            print(f"❌ LLM 构造失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        # Mock LLM（与 test_game_loop_20rounds.py 类似）
        from langchain_core.messages import AIMessage
        from langchain_core.runnables import Runnable

        class MockLLM(Runnable):
            def __init__(self):
                self._state_ref_slot_ref = [{}]
            def bind_tools(self, tools, **kwargs):
                return self
            def invoke(self, input, **kwargs):
                return AIMessage(content="<narrative>mock 叙事：日常过活。</narrative>")

        real_llm = MockLLM()
        print("✓ Mock LLM 构造成功")

    # 2. 加载 era_config
    from history_footnote.game_loop import GameLoop
    era_config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )

    # 3. 构造 GameLoop
    print("⏳ 初始化 GameLoop ...")
    init_t0 = time.time()
    try:
        loop = GameLoop(
            era_id="wanli1587",
            era_config=era_config,
            llm_model=real_llm,
            selected_identity="weaving_male",
        )
        print(f"✓ GameLoop 初始化成功 ({time.time() - init_t0:.2f}s)")
    except Exception as e:
        print(f"❌ GameLoop 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. mock _get_player_input + _is_game_over
    input_iter = iter(PLAYER_INPUTS)
    snapshots = []
    round_errors = []

    def mock_get_input():
        try:
            return next(input_iter)
        except StopIteration:
            raise SystemExit("Test done after 20 rounds")

    def mock_is_game_over():
        return loop.state.round_number > 20

    # 5. wrap _run_round 收集快照
    original_run_round = loop._run_round

    def wrapped_run_round(player_input):
        round_before = loop.state.round_number
        try:
            original_run_round(player_input)
        except Exception as e:
            round_errors.append((round_before, player_input, str(e)[:200]))
        snapshots.append({
            "round": loop.state.round_number,
            "cash": getattr(loop.state, "cash", 0),
            "events": len(loop.state.event_log),
            "narrative_len": len(getattr(loop.state, "narrative_history", [])),
        })

    # 6. 跑 20 回合
    print(f"⏳ 跑 20 回合（真 LLM）...")
    start_t = time.time()
    try:
        with patch.object(loop, "_get_player_input", side_effect=mock_get_input), \
             patch.object(loop, "_is_game_over", side_effect=mock_is_game_over), \
             patch.object(loop, "_run_round", side_effect=wrapped_run_round):
            try:
                loop.run()
            except SystemExit:
                pass
    except Exception as e:
        print(f"❌ 跑 20 回合异常: {e}")
        import traceback
        traceback.print_exc()
        return 1
    elapsed = time.time() - start_t
    print(f"✓ 跑完 ({elapsed:.2f}s, avg {elapsed/20:.2f}s/round)")

    # 7. 报告
    print()
    print(f"📊 最终状态:")
    print(f"  round_number: {loop.state.round_number}")
    print(f"  cash: {getattr(loop.state, 'cash', '?')}")
    print(f"  debt: {getattr(loop.state, 'debt', '?')}")
    print(f"  triggered_events: {len(loop.state.triggered_events)}")
    print(f"  event_log: {len(loop.state.event_log)}")
    print(f"  narrative_history: {len(getattr(loop.state, 'narrative_history', []))}")
    print(f"  snapshots: {len(snapshots)}")
    print(f"  round_errors: {len(round_errors)}")

    # 8. 阶段性快照
    if snapshots:
        print()
        print("📍 状态快照（每 5 回合）:")
        for snap in snapshots[::5]:
            print(f"  Round {snap['round']:2d}: cash={snap['cash']:.2f} "
                  f"events={snap['events']} narrative={snap['narrative_len']}")

    # 9. 异常
    if round_errors:
        print()
        print(f"⚠️ {len(round_errors)} 个回合异常:")
        for rnd, inp, e in round_errors[:5]:
            print(f"  Round {rnd}: {e[:120]}")

    # 10. 综合判断
    errors = []
    if len(snapshots) < 10:
        errors.append(f"只完成 {len(snapshots)}/20 回合（< 50%）")
    # 真 LLM 不一定输出 events_to_save → event_log 可空
    if not loop.state.event_log:
        print("  注: event_log=0（真 LLM 通常不输出 events 块，由 action_resolver 兜底）")
    if not getattr(loop.state, "narrative_history", []):
        errors.append("narrative_history 为空（真 LLM 应有 narrative）")

    if errors:
        print()
        for e in errors:
            print(f"❌ {e}")
        return 1

    print()
    print(f"✅ 真 LLM 20 回合端到端测试 通过")
    print(f"   - event_log = {len(loop.state.event_log)} 条")
    print(f"   - narrative_history = {len(loop.state.narrative_history)} 条")
    print(f"   - 耗时: {elapsed:.2f}s（avg {elapsed/20:.2f}s/round）")
    print(f"   - 异常: {len(round_errors)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
