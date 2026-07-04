"""游戏主循环验证脚本

模拟玩家输入，跑3-5回合，验证：
- 历史锚点强制触发
- 小人物身份边界
- 变量变化
- insight解锁
- NPC主动介入（节奏推进）
"""
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_loop import GameLoop
from history_footnote.mock_llm import MockDMChatModel


def simulate_input(inputs: list[str]):
    """构造input()的side_effect"""
    iter_inputs = iter(inputs)
    return lambda _: next(iter_inputs, "/quit")


def run_test():
    print("=" * 60)
    print("游戏主循环验证（Mock LLM）")
    print("=" * 60)

    # 加载时代包
    config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )

    # 准备Mock LLM
    llm = MockDMChatModel(era_config=config)

    # 准备模拟输入：3个普通回合 + 1个测试越界 + 1个测试insight
    test_inputs = [
        "我在织机前理经线，开始新一年的活计",  # round 1: 开年
        "我去茶馆听听有什么消息",  # round 2: 茶馆场景
        "我打听一下今年丝价行情",  # round 3: 丝绸相关
        "我想去皇宫告御状",  # 测试：越界
        "里长来催税怎么办",  # 测试：insight解锁
        "我按时交税",  # round 6: 价值观变化
        "/state",  # 查看状态
        "/quit",  # 退出
    ]

    # 构造GameLoop
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
    )

    # 替换input为模拟输入
    with patch("builtins.input", side_effect=test_inputs):
        try:
            game.run()
        except SystemExit:
            pass

    print("\n" + "=" * 60)
    print("✅ 主循环跑完")
    print("=" * 60)
    print(f"  最终回合: {game.state.round_number}")
    print(f"  当前日期: {game.state.current_date}")
    print(f"  已触发事件: {len(game.state.triggered_events)}个")
    print(f"  已解锁认知: {len(game.state.unlocked_insights)}个 → {game.state.unlocked_insights}")
    print(f"  NPC关系: {dict(game.state.npc_levels)}")
    print(f"  价值观: {dict(game.state.value_shifts)}")
    print(f"  玩家空闲轮数: {game.state.player_idle_rounds}")
    print(f"  事件记忆: {game.memory.count()}条")
    print(f"  叙事历史: {len(game.state.narrative_history)}条")


if __name__ == "__main__":
    run_test()
