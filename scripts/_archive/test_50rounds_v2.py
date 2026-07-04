"""50回合长流程测试 v2 - 更密集的关键词覆盖

改进：
1. 输入关键词更密集（每回合都针对一个insight的trigger_keywords）
2. 添加第三次断点（更细粒度）
3. 输出每回合的关键指标
4. 重点关注变量趋势、insight解锁曲线
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


# 50回合密集关键词测试
INPUTS_INTENSIVE = [
    # 1-5: 开局 + 织丝基础
    "我在织机前织湖绫",                   # ins_silk_trade
    "我继续织丝绸，做妻络夫织的活",       # ins_silk_trade
    "我把昨天织的湖绫拿到牙行去卖",        # ins_silk_trade
    "我去盛泽镇市集卖丝",                  # ins_silk_trade
    "我在牙行听人说起湖州的双林镇",        # ins_silk_trade
    # 6-10: 城市与税
    "我去苏州城里看看",                    # ins_city_life
    "我在苏州城里走了走",                  # ins_city_life
    "我听说今年丝税要加",                  # ins_silver_tax
    "我去里长那里问今年的税单",            # ins_li_jia
    "我算了算今年要交的银",                # ins_silver_tax
    # 11-15: 读书与上层
    "我去县学看了看",                      # ins_bureaucracy
    "我听说李秀才中了举人",                # ins_expand_ambition
    "我去城里的当铺典当了东西",            # ins_silver_economy
    "我听说京城出了大事",                  # ins_north_south
    "我听说北边的蛮族在闹",                # ins_north_south
    # 16-20: 转折
    "我借了高利贷",                        # ins_moral_vs_reality
    "我决定扩大织机规模",                  # ins_expand_ambition
    "我算了算上供的账目",                  # ins_tribute_trap
    "我看到朝廷又在加税",                  # ins_decline_signal
    "我听说朝廷党争严重",                  # ins_bureaucracy
    # 21-25: 道德困境
    "我和邻居张三聊怎么逃税",              # ins_moral_vs_reality
    "我去里长家求情",                      # ins_li_jia
    "我听说邻居张三发财了",                # ins_moral_vs_reality
    "我想做更大的生意",                    # ins_expand_ambition
    "我算了算上供的丝绸要多少",            # ins_tribute_trap
    # 26-30: 衰退信号
    "我看到县衙贴出告示",                  # ins_decline_signal
    "我听说京城在闹事",                    # ins_decline_signal
    "我看到街上行人稀少",                  # ins_decline_signal
    "我听说北边蛮族扣边",                  # ins_decline_signal
    "我算了算上供的丝绸已经交不起了",      # ins_tribute_trap
    # 31-35: 无处可逃
    "我觉得这生意越做越难",                # ins_no_escape
    "我想逃到别处去",                      # ins_no_escape
    "我听说月港那边也难",                  # ins_no_escape
    "我想想出路在哪里",                    # ins_no_escape
    "我听说朝廷在抓逃户",                  # ins_no_escape
    # 36-40: 反向思考
    "我接了一笔大单",                      # ins_bigger_not_better
    "我雇了三个机工",                      # ins_bigger_not_better
    "我看到大机户的下场",                  # ins_bigger_not_better
    "我听说大商人亏了",                    # ins_bigger_not_better
    "我算了算扩张的代价",                  # ins_bigger_not_better
    # 41-45: 终极
    "我看到盛泽镇一片衰败",                # ins_grand_failure
    "我听说苏州城里也乱了",                # ins_grand_failure
    "我听说月港的商人也亏了",              # ins_grand_failure
    "我算了算做了几十年还是老样子",        # ins_grand_failure
    "我决定把织机都卖了",                  # /quit
    "/quit",
]


def run_test(label: str, inputs: list, save_root: Path) -> dict:
    print(f"\n{'=' * 60}")
    print(f"{label}: {len(inputs)} 回合")
    print(f"{'=' * 60}")

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    save_manager = SaveManager(save_root)
    llm = MockDMChatModel(era_config=config)
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
        with patch("builtins.input", side_effect=inputs):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old_stdout
        elapsed = time.time() - start

    output = captured.getvalue()

    final_state = game.state

    # 输出每5回合的snapshot
    print(f"\n  时间线（每5回合）:")
    print(f"  {'回合':<6}{'日期':<12}{'livelihood':<12}{'tax':<8}{'silv_p':<8}{'ins':<5}{'events':<6}")

    # 解析output里的[状态]行
    import re
    state_lines = re.findall(
        r"回合(\d+)\s*\|\s*(\S+)\s*\|\s*已解锁认知(\d+)个",
        output
    )

    # 每5回合采样
    state_history = []
    for line in state_lines:
        round_num = int(line[0])
        date = line[1]
        insight_count = int(line[2])
        # 从state里查变量
        if round_num in [s["round"] for s in state_history]:
            continue
        # 简化：从output查变量
        var_match = re.search(
            rf"回合{round_num}.*?livelihood:\s*([\d.]+).*?tax_burden:\s*([\d.]+).*?silver_pressure:\s*([\d.]+)",
            output,
            re.DOTALL,
        )
        if var_match:
            li, tax, sp = float(var_match.group(1)), float(var_match.group(2)), float(var_match.group(3))
        else:
            li = tax = sp = -1
        state_history.append({
            "round": round_num,
            "date": date,
            "livelihood": li,
            "tax": tax,
            "sp": sp,
            "insights": insight_count,
        })

    # 输出
    for s in state_history[::5]:  # 每5条
        print(f"  {s['round']:<6}{s['date']:<12}{s['livelihood']:<12}{s['tax']:<8}{s['sp']:<8}{s['insights']:<5}")

    # 最终状态
    print(f"\n  最终状态:")
    print(f"    回合: {final_state.round_number} ({final_state.current_date})")
    print(f"    用时: {elapsed:.1f}s")
    print(f"    解锁insight: {len(final_state.unlocked_insights)}条")
    print(f"    触发事件: {len(final_state.triggered_events)}条")
    print(f"    事件记忆: {len(game.memory.events)}条")
    print(f"    异常: {output.count('异常') + output.count('ERROR')}")

    # 关键变量
    var = final_state.variables
    print(f"\n  最终变量:")
    for k, v in sorted(var.items()):
        print(f"    {k}: {v}")

    # insight解锁曲线
    print(f"\n  Insight解锁过程（按回合）:")
    all_insights = final_state.unlocked_insights
    print(f"    最终: {sorted(all_insights)}")

    # 输出长度
    print(f"\n  总输出: {len(output)} 字符")

    # 检查叙事重复度
    narrative_chunks = re.findall(r"DM叙事[^\\n]*[\\n\\s]+(.+?)(?=\[状态\]|$)", output, re.DOTALL)
    unique_chunks = set(narrative_chunks)
    if narrative_chunks:
        uniqueness = len(unique_chunks) / len(narrative_chunks)
        print(f"  叙事块: {len(narrative_chunks)}, 唯一: {len(unique_chunks)}, 独特性: {uniqueness*100:.1f}%")

    return {
        "label": label,
        "elapsed": elapsed,
        "final_round": final_state.round_number,
        "insight_count": len(all_insights),
        "insights": sorted(all_insights),
        "events": sorted(final_state.triggered_events),
        "variables": var,
        "narrative_history_count": len(game.memory.events),
        "output_length": len(output),
        "errors": output.count("异常") + output.count("ERROR"),
        "state_history": state_history,
    }


def main():
    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_50v2_"))
    try:
        summary = run_test("密集关键词测试", INPUTS_INTENSIVE, tmp_root)

        # 报告
        print("\n\n" + "=" * 60)
        print("50回合密集测试报告")
        print("=" * 60)
        print(f"\n  最终回合: {summary['final_round']}")
        print(f"  解锁insight: {summary['insight_count']}/14 ({summary['insight_count']/14*100:.0f}%)")
        print(f"  触发事件: {len(summary['events'])}条")
        print(f"  异常: {summary['errors']}")

        # 未解锁的insight
        all_ids = ['ins_silk_trade', 'ins_silver_tax', 'ins_li_jia', 'ins_city_life',
                   'ins_expand_ambition', 'ins_north_south', 'ins_bureaucracy',
                   'ins_silver_economy', 'ins_moral_vs_reality', 'ins_tribute_trap',
                   'ins_decline_signal', 'ins_no_escape', 'ins_bigger_not_better',
                   'ins_grand_failure']
        unlocked = set(summary['insights'])
        missing = [iid for iid in all_ids if iid not in unlocked]
        print(f"  未解锁: {missing if missing else '无'}")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()