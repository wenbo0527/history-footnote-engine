"""行动点机制烟雾测试（Mock LLM）"""
import sys, json, threading
sys.path.insert(0, "src")
from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop
from history_footnote.game_state import GameState

config = json.loads(open("eras/wanli1587/era.json").read())
llm = MockDMChatModel(era_config=config)
game = GameLoop(era_id="wanli1587", era_config=config, llm_model=llm, selected_identity="weaving_male")

print(f"=== 初始状态 ===")
print(f"回合: {game.state.round_number} | 日期: {game.state.current_date}")
print(f"行动点: {game.state.action_points_current}/{game.state.action_points_max}")

# 模拟输入3次行动（每次消耗1点）
inputs = [
    "我去集市上看看",  # 行动点 -1
    "我问问邻居张三今年行情",  # 行动点 -1
    "我织一匹湖绫",  # 行动点 -1 → 行动点耗尽 → 跳月
]
for i, inp in enumerate(inputs, 1):
    print(f"\n=== 玩家输入 #{i}: {inp} ===")
    date_before = game.state.current_date
    ap_before = game.state.action_points_current
    game._run_round(inp)
    ap_after = game.state.action_points_current
    date_after = game.state.current_date
    print(f"\n>> 状态: 回合{game.state.round_number} | 日期{date_after} | 行动点 {ap_after}/{game.state.action_points_max}")
    if date_before != date_after:
        print(f">> ⏭️  跳月：从 {date_before} → {date_after}")

# 再做1次问询（不消耗行动点）
print(f"\n=== 玩家输入 #4: 我问下李秀才今年丝价 ===")
date_before = game.state.current_date
ap_before = game.state.action_points_current
game._run_round("我问下李秀才今年丝价")
ap_after = game.state.action_points_current
print(f"\n>> 状态: 回合{game.state.round_number} | 行动点 {ap_after}/{game.state.action_points_max} (应保持不变)")
print(f">> 月推进: {date_before != game.state.current_date} (应为False)")

# 验证 narrative_history
print(f"\n=== narrative_history ===")
for nh in game.state.narrative_history:
    print(f"  回合{nh['round']}: {nh['summary']} | {nh['narrative'][:60]}...")

# 验证 行动点数学
print(f"\n=== 行动点数学验证 ===")
print(f"最终行动点: {game.state.action_points_current}")
print(f"最终回合: {game.state.round_number}")
print(f"最终日期: {game.state.current_date}")
