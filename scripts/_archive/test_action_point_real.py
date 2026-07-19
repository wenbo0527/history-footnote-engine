"""5回合真实Minimax LLM测试 - 验证行动点机制

测试场景：
- 输入1: "我去织机前理经线" → 行动 -1点
- 输入2: "我去牙行和牙人谈丝价" → 行动 -1点
- 输入3: "我织一匹湖绫" → 行动 -2点（耗尽→跳月）
- 输入4: "我问问邻居张三今年行情" → 问询 0点
- 输入5: "我去县衙看看告示" → 行动 -1点

预期：回合2-3中触发跳月
"""
import json, sys, time, io
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "src")
from dotenv import load_dotenv
load_dotenv()

from history_footnote.llm_providers import make_llm
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


SAMPLE_INPUTS = [
    "我去织机前理经线",            # 行动 -1点
    "我去牙行和牙人谈丝价",        # 行动 -1点
    "我织一匹湖绫",                # 行动 -2点 → 跳月
    "我问问邻居张三今年行情",      # 问询 0点（不消耗）
    "我去县衙看看告示",            # 行动 -1点
]


def main():
    Path("logs").mkdir(exist_ok=True)
    log = open("logs/action_point_real.log", "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("5回合真实Minimax LLM行动点测试")
    L("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    llm = make_llm(provider="minimax-anthropic", era_config=config)
    L(f"Provider: Minimax | Model: MiniMax-M3")

    save_root = Path("logs/action_point_save")
    save_root.mkdir(exist_ok=True, parents=True)
    save_manager = SaveManager(save_root)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save_manager,
        selected_identity="weaving_male",
    )

    L(f"\n初始: 回合{game.state.round_number} | {game.state.current_date} | 行动点 {game.state.action_points_current}/{game.state.action_points_max}")

    captured = io.StringIO()
    old = sys.stdout
    sys.stdout = captured
    try:
        with patch("builtins.input", side_effect=SAMPLE_INPUTS + ["/quit"]):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old

    output = captured.getvalue()
    Path("logs/action_point_real_full.txt").write_text(output, encoding="utf-8")

    L(f"\n=== DM输出 ===\n{output}")

    L(f"\n=== 最终状态 ===")
    L(f"回合: {game.state.round_number}")
    L(f"日期: {game.state.current_date}")
    L(f"行动点: {game.state.action_points_current}/{game.state.action_points_max}")
    L(f"已解锁 insight: {sorted(game.state.unlocked_insights)}")
    L(f"已触发事件: {sorted(game.state.triggered_events)}")

    # 统计跳月次数
    month_advances = output.count("行动点耗尽，进入")
    L(f"\n=== 跳月次数: {month_advances} ===")

    # 统计行动点消耗统计
    import re
    consumes = re.findall(r"本次行动消耗\s*(\d+)\s*点", output)
    L(f"行动点消耗记录: {consumes}")
    inquires = output.count("问询] 本次不消耗行动点")
    L(f"问询次数（不消耗）: {inquires}")

    # narrative 长度分析
    L(f"\n=== 叙事长度分析 ===")
    for i, nh in enumerate(game.state.narrative_history):
        length = len(nh["narrative"])
        L(f"  回合{nh['round']} #{i+1}: {length}字符 | {nh['narrative'][:80]}...")

    log.close()


if __name__ == "__main__":
    main()
