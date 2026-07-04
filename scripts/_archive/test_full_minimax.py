"""完整60回合真实Minimax LLM长流程测试

设计目标：覆盖全部14个insight解锁路径
- 1-15: 基础织户-市集-税-里甲（ins_silk_trade, ins_city_life, ins_silver_tax, ins_li_jia, ins_bureaucracy）
- 16-25: 科举/南北/党争/上供/扩张（ins_moral_vs_reality, ins_north_south, ins_tribute_trap, ins_expand_ambition）
- 26-35: 衰退信号（ins_decline_signal）
- 36-45: 皇帝缺朝/倭寇/海禁（ins_emperor_absent, ins_jap_invasion, ins_maritime_legitimacy）
- 46-60: 家庭变故 + 终极衰退（ins_family_crisis）
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from history_footnote.llm_providers import make_llm
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


# 60回合剧情种子（覆盖全部14个insight）
INPUTS_FULL = [
    # 1-10: 织户基本盘
    "我在织机前织湖绫",                              # ins_silk_trade
    "我把织好的湖绫拿到牙行去卖",                    # ins_silk_trade
    "我在牙行和牙人谈丝价",
    "我听说今年第一批洋船要来了",
    "我去盛泽镇市集看看",
    "我去苏州城里走走",                              # ins_city_life
    "我听说今年丝税要加",                            # ins_silver_tax
    "我去里长那里问今年的税单",                      # ins_li_jia
    "我算了算今年要交的银",
    "我听邻居说城里热闹",
    # 11-20: 官僚与决策
    "我去县衙看看告示",                              # ins_bureaucracy
    "我听说李秀才中了举人",
    "我去城里的当铺典当了东西",
    "我听说京城出了大事",
    "我听说北边的蛮族在闹",                          # ins_north_south
    "我决定扩大织机规模",                            # ins_expand_ambition
    "我算了算上供的账目",                            # ins_tribute_trap
    "我借了高利贷",
    "我和邻居张三聊怎么逃税",
    "我听说朝廷党争严重",                            # ins_moral_vs_reality
    # 21-30: 衰退
    "我看到县衙贴出告示",
    "我听说京城在闹事",
    "我看到街上行人稀少",
    "我听说北边蛮族扣边",
    "我算了算上供的丝绸已经交不起了",
    "我觉得这生意越做越难",
    "我看到盛泽镇一片衰败",                          # ins_decline_signal
    "我决定把织机都卖了",
    "我听说苏州城里也乱了",
    "我算了算做了几十年还是老样子",
    # 31-40: 皇帝/倭寇/海禁
    "我听老茶客说皇上这十几年都不上朝了",            # ins_emperor_absent
    "我听船夫说月港那边来了倭寇",                    # ins_jap_invasion
    "我听邻居说朝廷下了海禁令",                      # ins_maritime_legitimacy
    "我想去月港做丝卖",
    "我听说戚继光的部队在浙江剿倭",
    "我听老秀才说大明海禁太严了",
    "我听说皇上跟百官斗气不上朝",
    "我听说倭寇从浙江打到福建了",
    "我看到告示说私自出海要杀头",
    "我听说走私的船都被抓了",
    # 41-50: 家庭变故
    "我妻子沈氏生病了",                              # ins_family_crisis
    "我请不起郎中给她看病",
    "我把家传的玉佩典当了给妻子买药",
    "我儿子阿宝的先生催束脩",
    "我听说瘟疫从苏州传过来了",
    "我邻居张寡妇的丈夫也病死了",
    "我听老人说这都是天谴",
    "我把阿宝送到亲戚家避一避",
    "我算了算家里还剩多少粮食",
    "我决定下个月把田也卖了给妻子治病",
]


def run_case(case_name: str, identity: str, label: str, inputs: list, save_root: Path, max_rounds: int) -> dict:
    log = open(f"logs/full_{case_name}.log", "w", encoding="utf-8")
    Path("logs").mkdir(exist_ok=True)
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()

    L(f"\n{'=' * 60}")
    L(f"Case {case_name}: {label}")
    L(f"{'=' * 60}")

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    llm = make_llm(provider="minimax-anthropic", era_config=config)
    L(f"LLM Provider: Minimax | Model: {config.get('llm', {}).get('model', 'MiniMax-M3')}")

    save_manager = SaveManager(save_root / case_name)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save_manager,
        selected_identity=identity,
    )

    start = time.time()
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        # 限制到 max_rounds
        effective_inputs = inputs[:max_rounds] + ["/quit"]
        with patch("builtins.input", side_effect=effective_inputs):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old_stdout
        elapsed = time.time() - start

    output = captured.getvalue()
    full_out_path = Path("logs") / f"full_{case_name}_output.txt"
    full_out_path.write_text(output, encoding="utf-8")

    final_state = game.state
    summary = {
        "case": case_name,
        "label": label,
        "elapsed": elapsed,
        "final_round": final_state.round_number,
        "final_date": final_state.current_date,
        "unlocked_insights": sorted(final_state.unlocked_insights),
        "triggered_events": sorted(final_state.triggered_events),
        "final_variables": dict(final_state.variables),
        "narrative_count": len(game.memory.events),
        "output_length": len(output),
        "errors": output.count("异常") + output.count("ERROR"),
    }

    L(f"\n  回合: {summary['final_round']} ({summary['final_date']})")
    L(f"  用时: {elapsed:.1f}s ({elapsed/max(1, summary['final_round']):.1f}s/回合)")
    L(f"  解锁insight: {len(summary['unlocked_insights'])}/14 → {summary['unlocked_insights']}")
    L(f"  触发事件: {len(summary['triggered_events'])}条 → {summary['triggered_events']}")
    L(f"  输出长度: {summary['output_length']}字符")
    if summary["errors"] > 0:
        L(f"  ⚠️ 异常: {summary['errors']}")
    else:
        L(f"  ✅ 无异常")

    L(f"\n  关键变量:")
    for k in ["livelihood", "silver_pressure", "tax_burden", "workshop_scale", "moral_anxiety", "court_paralysis", "north_threat"]:
        if k in summary["final_variables"]:
            L(f"    {k}: {summary['final_variables'][k]}")

    try:
        loaded = save_manager.load_state(game.session, "auto")
        assert loaded["round_number"] == summary["final_round"]
        L(f"  ✅ 存档验证通过（回合{loaded['round_number']}）")
    except Exception as e:
        L(f"  ❌ 存档验证失败: {e}")
        summary["errors"] += 1

    log.close()
    return summary


def main():
    Path("logs").mkdir(exist_ok=True)
    main_log = open("logs/full_summary.log", "w", encoding="utf-8")
    def M(msg=""):
        print(msg)
        main_log.write(str(msg) + "\n")
        main_log.flush()

    M("=" * 60)
    M("60回合完整Minimax LLM测试（覆盖全部14个insight）")
    M("=" * 60)
    M(f"\n预计总时长: 60回合 × ~12秒 ≈ 12分钟")

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_full_", dir="logs"))

    try:
        # Case A: 男织户 50 回合（游戏总回合数）
        s_a = run_case(
            "A_male_full",
            "weaving_male",
            "织户男·50回合完整",
            INPUTS_FULL,
            tmp_root,
            max_rounds=50,
        )

        # 综合报告
        M("\n\n" + "=" * 60)
        M("60回合完整测试综合报告")
        M("=" * 60)

        M(f"\n{'Case':<25}{'回合':<6}{'insight':<10}{'事件':<6}{'异常':<6}{'用时':<10}{'秒/回合':<8}")
        M("-" * 75)
        for s in [s_a]:
            per = s['elapsed'] / max(1, s['final_round'])
            M(f"{s['case']:<25}{s['final_round']:<6}"
                  f"{len(s['unlocked_insights'])}/14{'':<6}"
                  f"{len(s['triggered_events']):<6}"
                  f"{s['errors']:<6}"
                  f"{s['elapsed']:.1f}s{'':<4}"
                  f"{per:.1f}s")

        # 14个insight解锁状态（按era.json实际ID）
        all_14 = [
            "ins_silk_trade", "ins_silver_tax", "ins_li_jia", "ins_city_life",
            "ins_expand_ambition", "ins_north_south", "ins_bureaucracy",
            "ins_silver_economy", "ins_moral_vs_reality", "ins_tribute_trap",
            "ins_decline_signal", "ins_no_escape", "ins_bigger_not_better",
            "ins_grand_failure",
        ]
        M(f"\n14个insight解锁状态（按era.json）:")
        for ins in all_14:
            mark = "✅" if ins in s_a['unlocked_insights'] else "❌"
            M(f"  {mark} {ins}")
        M(f"\n注: 终极insight (ins_no_escape/ins_bigger_not_better/ins_grand_failure) 需要前期insight全解锁+特定剧情收束")

        if s_a['errors'] == 0:
            M(f"\n✅ 无异常")
        else:
            M(f"\n⚠️ {s_a['errors']}个异常")

    finally:
        M(f"\n存档保留于: {tmp_root}")
        main_log.close()


if __name__ == "__main__":
    main()
