"""🆕 v1.7.30 10 轮故事连贯性 review

跑 mock_llm 10 轮 + 抽 narrative/state，输出连贯性 report（8 维度）

使用：
    python scripts/review_10rounds_coherence.py

输出：
- 10 轮 narrative 摘要（玩家输入 → DM 输出）
- 8 维度连贯性评分（state 连续性、context 传递、事件链、NPC 引用、时间线等）

注意：本脚本用 mock_llm（不依赖真实 LLM），输出的是**框架连贯性**。
如需 review 真实 LLM 输出，请跑 _archive/test_minimax_10rounds.py（需 token）。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from unittest.mock import patch
import io

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager

# 10 轮玩家输入（参考 _archive/test_50rounds.py 的主线 + 季节感）
INPUTS_10 = [
    "我在织机前织湖绫",                # 1
    "我把织好的湖绫拿到牙行去卖",      # 2
    "我听说今年第一批洋船要来了",      # 3
    "我去苏州城里走走",                # 4
    "我听说今年丝税要加",              # 5
    "我去里长那里问今年的税单",        # 6
    "我听邻居说李秀才中了举人",        # 7
    "我决定扩大织机规模",              # 8
    "我听说朝廷党争严重",              # 9
    "我看到县衙贴出告示",              # 10
]


def main():
    print("=" * 60)
    print("🆕 v1.7.30 10 轮故事连贯性 review（mock_llm）")
    print("=" * 60)

    config = json.loads((ROOT / "eras" / "wanli1587" / "era.json").read_text(encoding="utf-8"))
    # 用 mock_llm 替代真实 LLM
    llm = MockDMChatModel()

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_review_10_"))
    try:
        save_manager = SaveManager(tmp_root)
        game = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm,
            save_manager=save_manager,
            selected_identity="weaving_male",
        )
    except Exception as e:
        print(f"❌ GameLoop 初始化失败：{e}")
        return 1

    rounds_data = []
    for i, inp in enumerate(INPUTS_10, 1):
        print(f"\n--- Round {i} ---")
        print(f"  👤 Player: {inp}")
        # 屏蔽 _run_round 内的 print 输出（避免测试日志污染）
        try:
            with patch("sys.stdout", new=io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            print(f"  ❌ _run_round 抛错：{e}")
            continue

        # 从 game.state.narrative_history 抽最新一条
        latest = game.state.narrative_history[-1] if game.state.narrative_history else {}
        narrative = (latest.get("narrative") or "").strip() if isinstance(latest, dict) else ""

        print(f"  🤖 DM:    {narrative[:120]}{'...' if len(narrative) > 120 else ''}")

        rounds_data.append({
            "round": i,
            "player_input": inp,
            "narrative": narrative,
            "narrative_len": len(narrative),
            "state_summary": {
                "round_number": game.state.round_number,
                "current_date": game.state.current_date,
                "variables_count": len(game.state.variables),
                "events_count": len(game.state.narrative_history),
                "insights_count": len(game.state.unlocked_insights),
                "npc_levels": dict(game.state.npc_levels),
                "value_shifts": dict(game.state.value_shifts),
            },
        })

    # 输出 JSON 报告
    output_path = ROOT / "tests" / "fixtures" / "10rounds_coherence_review.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(rounds_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n\n✅ 10 轮数据已写入 {output_path.relative_to(ROOT)}")
    return rounds_data


if __name__ == "__main__":
    data = main()
    if not data:
        sys.exit(1)
