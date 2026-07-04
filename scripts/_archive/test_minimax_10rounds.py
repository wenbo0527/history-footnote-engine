"""精简版真实LLM测试 - 10回合（快速验证）"""
import json, sys, time
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, "src")
from dotenv import load_dotenv
load_dotenv()

from history_footnote.llm_providers import make_llm
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


INPUTS_10 = [
    "我在织机前织湖绫",
    "我把织好的湖绫拿到牙行去卖",
    "我听说今年第一批洋船要来了",
    "我去苏州城里走走",
    "我听说今年丝税要加",
    "我去里长那里问今年的税单",
    "我听说李秀才中了举人",
    "我决定扩大织机规模",
    "我听说朝廷党争严重",
    "我看到县衙贴出告示",
    "/quit",
]


def main():
    print("=" * 60)
    print("Minimax真实LLM 10回合快速验证")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    llm = make_llm(provider="minimax-anthropic", era_config=config)

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_minimax_10_"))
    try:
        save_manager = SaveManager(tmp_root)
        game = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm,
            save_manager=save_manager,
            selected_identity="weaving_male",
        )

        start = time.time()
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with patch("builtins.input", side_effect=INPUTS_10):
                try: game.run()
                except SystemExit: pass
        finally:
            sys.stdout = old_stdout
            elapsed = time.time() - start

        output = captured.getvalue()
        final_state = game.state

        print(f"\n  回合: {final_state.round_number} ({final_state.current_date})")
        print(f"  用时: {elapsed:.1f}s")
        print(f"  解锁insight: {len(final_state.unlocked_insights)}/14")
        print(f"  触发事件: {len(final_state.triggered_events)}")
        print(f"  输出: {len(output)}字符")
        print(f"  异常: {output.count('异常') + output.count('ERROR')}")

        print(f"\n  Insight: {sorted(final_state.unlocked_insights)}")
        print(f"  Events: {sorted(final_state.triggered_events)}")
        print(f"\n  关键变量:")
        for k, v in sorted(final_state.variables.items()):
            print(f"    {k}: {v}")

        # 输出叙事片段（前2个DM叙事）
        import re
        narratives = re.findall(r"【DM叙事】\s*\n(.+?)(?=\[状态\]|\[INFO\]|$)", output, re.DOTALL)
        print(f"\n=== 真实Minimax生成的叙事（回合1）===")
        if narratives:
            print(narratives[0][:800])
        if len(narratives) > 1:
            print(f"\n=== 真实Minimax生成的叙事（回合5）===")
            print(narratives[min(4, len(narratives)-1)][:800])

        # 存档验证
        loaded = save_manager.load_state(game.session, "auto")
        print(f"\n  存档验证: round={loaded['round_number']} unlocked={loaded['unlocked_insights']}")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()