"""5回合真实Minimax LLM测试 - 验证8个SKILL

测试场景：
- 回合1: 玩家问询（触发慢时间 + 揭示型线索）
- 回合2: 玩家做正事（现在时间）
- 回合3: 玩家主动探索（慢时间 + 价值观发声）
- 回合4: 玩家说"科举"（认知框架锁定）
- 回合5: 玩家说"去京城见皇帝"（铁律拒绝）
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
from history_footnote.dm_skills import run_all_skills

SAMPLE_INPUTS = [
    "我去看看窗外的盛泽镇今天什么样",     # 1: 问询 → 慢时间 + 揭示型
    "我在织机前理经线",                  # 2: 正事 → 现在时间
    "我听说科举要提前了，我想问问李秀才",  # 3: 探索 → 慢时间 + 内心独白
    "我想去打听今年的乡试",              # 4: 科举 → 认知框架锁定
    "我要去京城见皇帝",                  # 5: 铁律 → 拒绝
]


def main():
    Path("logs").mkdir(exist_ok=True)
    log = open("logs/test_8skills_real.log", "w", encoding="utf-8")
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L("=" * 60)
    L("5回合真实LLM 8SKILL验证")
    L("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    llm = make_llm(provider="minimax-anthropic", era_config=config)
    L(f"Provider: Minimax | Model: MiniMax-M3")

    save_root = Path("logs/test_8skills_save")
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
    Path("logs/test_8skills_full.txt").write_text(output, encoding="utf-8")

    L(f"\n=== DM输出 ===\n{output}")
    L(f"\n=== 最终状态 ===")
    L(f"回合: {game.state.round_number}")
    L(f"日期: {game.state.current_date}")
    L(f"行动点: {game.state.action_points_current}/{game.state.action_points_max}")
    L(f"已解锁 insight: {sorted(game.state.unlocked_insights)}")
    L(f"已触发事件: {sorted(game.state.triggered_events)}")

    # SKILL 触发统计
    L(f"\n=== 8 SKILL 触发统计 ===")
    L(f"  SKILL-2 节奏控制:")
    for mode in ["slow_time", "now_time", "abstract_time", "sharp_cut"]:
        count = output.count(f"→ {mode}") + output.count(f"→ {mode}")
        L(f"    {mode}: {count} 次")
    L(f"  SKILL-3 线索投放:")
    for lt in ["推动型", "引导型", "揭示型", "压力型"]:
        count = output.count(lt)
        L(f"    {lt}: {count} 次")
    L(f"  SKILL-4 史实锚定:")
    L(f"    春税提示: {output.count('春税') + output.count('预单')}")
    L(f"  SKILL-5 价值观发声:")
    L(f"    内心独白/声音: {output.count('声音') + output.count('想起')}")
    L(f"  SKILL-6 失败叙事化:")
    L(f"    失败/但: {output.count('失败') + output.count('但是')}")
    L(f"  SKILL-7 三层裁判:")
    L(f"    拒绝/拦: {output.count('拒') + output.count('拦') + output.count('不见')}")
    L(f"  SKILL-8 认知框架:")
    L(f"    科举相关: {output.count('科举') + output.count('乡试')}")

    # 叙事长度分析
    L(f"\n=== 叙事长度分析 ===")
    for i, nh in enumerate(game.state.narrative_history):
        length = len(nh["narrative"])
        L(f"  回合{nh['round']} #{i+1}: {length}字符 | {nh['narrative'][:80]}...")

    log.close()


if __name__ == "__main__":
    main()
