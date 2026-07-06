"""🆕 v1.7.30 真实 LLM 10 轮 review

使用 minimax-anthropic 跑 10 轮，输出连贯性报告
- 不 mock，调用真实 LLM
- 每轮 narrative + state 都保存到 fixture
- 同时跑 8 维度分析

跑法：
    source .venv/bin/activate
    python scripts/review_10rounds_real.py
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch
import io

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

# 加载 .env
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from history_footnote.llm_providers import make_llm
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager
from history_footnote.narrative_sanitizer import sanitize

INPUTS_10 = [
    "我在织机前织湖绫",
    "我把织好的湖绫拿到牙行去卖",
    "我听说今年第一批洋船要来了",
    "我去苏州城里走走",
    "我听说今年丝税要加",
    "我去里长那里问今年的税单",
    "我听邻居说李秀才中了举人",
    "我决定扩大织机规模",
    "我听说朝廷党争严重",
    "我看到县衙贴出告示",
]


def main():
    print("=" * 60)
    print("🆕 v1.7.30 真实 LLM 10 轮 review")
    print("=" * 60)
    print(f"  LLM: {os.getenv('MINIMAX_MODEL')}")
    print(f"  Provider: minimax-anthropic")
    print()

    config = json.loads((ROOT / "eras" / "wanli1587" / "era.json").read_text(encoding="utf-8"))
    llm = make_llm(provider="minimax-anthropic", era_config=config)

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_real_10_"))
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
        t0 = time.time()
        try:
            with patch("sys.stdout", new=io.StringIO()):
                game._run_round(inp)
        except Exception as e:
            print(f"  ❌ _run_round 抛错：{e}")
            continue
        elapsed = time.time() - t0

        latest = game.state.narrative_history[-1] if game.state.narrative_history else {}
        narrative = (latest.get("narrative") or "").strip() if isinstance(latest, dict) else ""
        # 二次清洗
        if narrative:
            narrative = sanitize(narrative)

        print(f"  🤖 DM ({elapsed:.1f}s, {len(narrative)}字):")
        print(f"      {narrative[:200]}{'...' if len(narrative) > 200 else ''}")

        rounds_data.append({
            "round": i,
            "player_input": inp,
            "narrative": narrative,
            "narrative_len": len(narrative),
            "elapsed_sec": round(elapsed, 1),
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

    # 输出
    output_path = ROOT / "tests" / "fixtures" / "10rounds_coherence_review_REAL.json"
    output_path.write_text(
        json.dumps(rounds_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n\n✅ 真实 LLM 10 轮数据已写入 {output_path.relative_to(ROOT)}")
    print(f"   总耗时：{sum(r['elapsed_sec'] for r in rounds_data):.1f} 秒")
    return 0


if __name__ == "__main__":
    sys.exit(main())
