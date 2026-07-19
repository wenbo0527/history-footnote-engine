"""验证Minimax LLM能跑游戏主循环（3回合冒烟测试）"""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, "src")

# 加载.env
from dotenv import load_dotenv
load_dotenv()

from history_footnote.llm_providers import make_llm
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


def main():
    print("=" * 60)
    print("Minimax真实LLM冒烟测试（3回合）")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

    # 用Minimax真实LLM
    llm = make_llm(provider="minimax-anthropic", era_config=config)
    print(f"\nLLM Provider: Minimax (Anthropic兼容)")
    print(f"Model: {getattr(llm, 'model_name', 'MiniMax-M3')}")

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_minimax_smoke_"))
    try:
        save_manager = SaveManager(tmp_root)
        game = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm,
            save_manager=save_manager,
            selected_identity="weaving_male",
        )

        # 跑3回合
        test_inputs = [
            "我在织机前理经线",
            "我去集市看看丝价",
            "我到茶馆坐坐",
            "/quit",
        ]

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with patch("builtins.input", side_effect=test_inputs):
                try:
                    game.run()
                except SystemExit:
                    pass
        finally:
            sys.stdout = old_stdout
            output = captured.getvalue()

        print(f"\n=== 输出 ===\n{output[-3000:]}")

        # 验证
        if len(output) > 1000:
            print("\n✅ Minimax真实LLM能正常驱动游戏")
        else:
            print("\n⚠️ 输出较短，可能有问题")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()