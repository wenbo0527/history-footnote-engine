"""50回合真实Minimax LLM长流程测试

测试cases：
- Case A: weaving_male 男性织户（30回合，缩短以控制时间）
- Case B: weaving_female 女性织户（30回合）

输出：
- 每回合的关键指标（LLM真实生成的叙事片段）
- 最终summary
- insight解锁率
- 存档验证
"""
import json
import sys
import time
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


# 30回合关键场景测试（缩短版以控制时间）
INPUTS_REAL_LLM = [
    # 1-5: 织丝基础 (ins_silk_trade)
    "我在织机前织湖绫",
    "我把织好的湖绫拿到牙行去卖",
    "我去盛泽镇市集看看",
    "我在牙行和牙人谈丝价",
    "我听说今年第一批洋船要来了",
    # 6-10: 城市与税 (ins_city_life, ins_silver_tax, ins_li_jia)
    "我去苏州城里走走",
    "我听说今年丝税要加",
    "我去里长那里问今年的税单",
    "我算了算今年要交的银",
    "我听说城里可热闹",
    # 11-15: 官僚与南北
    "我去县衙看看告示",
    "我听说李秀才中了举人",
    "我去城里的当铺典当了东西",
    "我听说京城出了大事",
    "我听说北边的蛮族在闹",
    # 16-20: 扩张与上供
    "我决定扩大织机规模",
    "我算了算上供的账目",
    "我借了高利贷",
    "我和邻居张三聊怎么逃税",
    "我听说朝廷党争严重",
    # 21-25: 衰退信号
    "我看到县衙贴出告示",
    "我听说京城在闹事",
    "我看到街上行人稀少",
    "我听说北边蛮族扣边",
    "我算了算上供的丝绸已经交不起了",
    # 26-30: 终极
    "我觉得这生意越做越难",
    "我看到盛泽镇一片衰败",
    "我决定把织机都卖了",
    "我听说苏州城里也乱了",
    "我算了算做了几十年还是老样子",
]


def run_case(case_name: str, identity: str, label: str, inputs: list, save_root: Path) -> dict:
    log = open(f"logs/minimax_{case_name}.log", "w", encoding="utf-8")
    Path("logs").mkdir(exist_ok=True)
    def L(msg=""):
        print(msg)
        log.write(str(msg) + "\n")
        log.flush()
    L(f"\n{'=' * 60}")
    L(f"Case {case_name}: {label}")
    L(f"{'=' * 60}")

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    L(f"LLM Provider: Minimax (Anthropic兼容) | Model: MiniMax-M3")

    # 用Minimax真实LLM
    llm = make_llm(provider="minimax-anthropic", era_config=config)

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
        with patch("builtins.input", side_effect=inputs + ["/quit"]):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old_stdout
        elapsed = time.time() - start

    output = captured.getvalue()

    # 写入完整 LLM 输出供分析
    full_out_path = Path("logs") / f"minimax_{case_name}_full_output.txt"
    full_out_path.write_text(output, encoding="utf-8")

    # 抽取 LLM 真实生成的 narrative 片段
    import re
    narratives = re.findall(r"\[叙事\]\s*\n(.*?)(?=\n\[|$)", output, re.DOTALL)
    L(f"\n  叙事抽样（前3条）:")
    for i, n in enumerate(narratives[:3]):
        snippet = n.strip()[:200]
        L(f"    [{i+1}] {snippet}…")

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
    L(f"  用时: {elapsed:.1f}s")
    L(f"  解锁insight: {len(summary['unlocked_insights'])}/14 → {summary['unlocked_insights']}")
    L(f"  触发事件: {len(summary['triggered_events'])}条 → {summary['triggered_events']}")
    L(f"  输出长度: {summary['output_length']}字符")
    if summary["errors"] > 0:
        L(f"  ⚠️ 异常: {summary['errors']}")
    else:
        L(f"  ✅ 无异常")

    # 关键变量
    L(f"\n  关键变量:")
    for k in ["livelihood", "silver_pressure", "tax_burden", "workshop_scale", "moral_anxiety"]:
        if k in summary["final_variables"]:
            L(f"    {k}: {summary['final_variables'][k]}")

    # 存档验证
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
    main_log = open("logs/minimax_summary.log", "w", encoding="utf-8")
    def M(msg=""):
        print(msg)
        main_log.write(str(msg) + "\n")
        main_log.flush()
    M("=" * 60)
    M("50回合真实Minimax LLM测试")
    M("=" * 60)
    M("\n⚠️  注意：本测试会调用真实Minimax API，耗时较长（30回合约3-5分钟）")

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_50minimax_", dir="logs"))
    try:
        # Case A: 男性织户
        s_a = run_case(
            "A_weaving_male_minimax",
            "weaving_male",
            "织户男（Minimax真实LLM）",
            INPUTS_REAL_LLM,
            tmp_root,
        )

        # Case B: 女性织户（输入稍不同）
        inputs_female = [
            "我在家络丝",
            "我帮丈夫理经线",
            "我今天去集市买染料",
            "我和牙行娘子聊丝价",
            "我听邻居说行情",
            "我去牙行看看",
            "我听说今年丝税要加",
            "我去里长那里问",
            "我算了算账",
            "我听人说城里热闹",
            "我去桑田帮忙",
            "我听邻居说李秀才中了举",
            "我听说京城出了大事",
            "我听说北边的蛮族在闹",
            "我决定扩大作坊",
            "我算了算上供的账目",
            "我借了高利贷",
            "我和邻居嫂子聊怎么逃税",
            "我听说朝廷党争严重",
            "我去县衙看看",
            "我听说京城在闹事",
            "我看到街上行人稀少",
            "我听说北边蛮族扣边",
            "我算了算上供的丝绸",
            "我觉得这生意越做越难",
            "我看到盛泽镇一片衰败",
            "我决定把织机都卖了",
            "我听邻居说苏州城里也乱了",
            "我想想未来",
            "我开始学绣花",
        ]
        s_b = run_case(
            "B_weaving_female_minimax",
            "weaving_female",
            "织户女（Minimax真实LLM）",
            inputs_female,
            tmp_root,
        )

        # 综合报告
        M("\n\n" + "=" * 60)
        M("50回合真实LLM综合报告")
        M("=" * 60)

        M(f"\n{'Case':<35}{'回合':<6}{'insight':<10}{'事件':<6}{'异常':<6}{'用时':<8}")
        M("-" * 70)
        for s in [s_a, s_b]:
            M(f"{s['case']:<35}{s['final_round']:<6}"
                  f"{len(s['unlocked_insights']):<10}"
                  f"{len(s['triggered_events']):<6}"
                  f"{s['errors']:<6}"
                  f"{s['elapsed']:.1f}s")

        # 性别对比
        M(f"\n性别对比:")
        M(f"  男解锁insight: {s_a['unlocked_insights']}")
        M(f"  女解锁insight: {s_b['unlocked_insights']}")

        common = set(s_a['unlocked_insights']) & set(s_b['unlocked_insights'])
        male_only = set(s_a['unlocked_insights']) - set(s_b['unlocked_insights'])
        female_only = set(s_b['unlocked_insights']) - set(s_a['unlocked_insights'])

        M(f"  共同: {sorted(common) if common else '无'}")
        M(f"  仅男: {sorted(male_only) if male_only else '无'}")
        M(f"  仅女: {sorted(female_only) if female_only else '无'}")

        total_errors = s_a['errors'] + s_b['errors']
        if total_errors == 0:
            M(f"\n✅ 全部cases无异常")
        else:
            M(f"\n⚠️ 共{total_errors}个异常")

    finally:
        import shutil
        # 保留存档供分析，不删除 tmp_root
        # shutil.rmtree(tmp_root, ignore_errors=True)
        main_log.close()
        L(f"\n  存档保留于: {tmp_root}")


if __name__ == "__main__":
    main()