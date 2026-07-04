"""50回合长流程测试

测试cases:
- Case A: weaving_male 男性织户（默认）— 主线
- Case B: weaving_female 女性织户 — 对照
- Case C: scholar_male 读书人 — 支线

输出：
- 每回合的state关键指标（回合、日期、变量、insight数、事件数）
- 最终summary
- 存档验证
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


# === 测试cases ===

CASES = {
    "A_weaving_male": {
        "identity": "weaving_male",
        "label": "织户男",
        "inputs": [
            # 1-5: 开局（织机日常）
            "我在织机前理经线",      # 1
            "我继续织了一匹湖绫",    # 2
            "我把昨天织的绸拿到牙行",  # 3
            "今天去盛泽镇集市看看",   # 4
            "我听说今年第一批洋船要来了",  # 5
            # 6-10: 茶馆/牙行
            "我去茶馆坐坐",          # 6
            "今天去牙行问问丝价",     # 7
            "我算了算今年的税单",     # 8
            "我去里长那里打听",       # 9
            "我听说城里可热闹了",     # 10
            # 11-15: 季节事件触发
            "夏天到了我去桑田看看",   # 11
            "我在院子里晾丝",         # 12
            "我听说明年要加税",       # 13
            "我去县城看看官府的告示",  # 14
            "我和邻居聊了聊",          # 15
            # 16-20: 秋季危机
            "我去集市买了些东西",     # 16
            "我在家整理账目",          # 17
            "牙人来压价了",            # 18
            "我想借钱周转",            # 19
            "我决定再撑一阵",          # 20
            # 21-25: 冬天困境
            "今年行情不好",            # 21
            "我去茶馆听说邻县的事",   # 22
            "我和牙行闹翻了",          # 23
            "我在家赶织机",            # 24
            "我算了算欠账",            # 25
            # 26-30: 卖机危机
            "我打算卖掉一台织机",     # 26
            "我去丝市找活",            # 27
            "今天没抢到活",            # 28
            "我听说明年要派税监来",    # 29
            "我和老婆商量怎么办",     # 30
            # 31-35: 机工日常
            "我每天天亮去丝市等活",   # 31
            "牙人介绍我去一家机房",    # 32
            "今天活多",                # 33
            "工钱发了",                # 34
            "回家吃饭",                # 35
            # 36-40: 觉醒期
            "我听说苏州的机工闹事",   # 36
            "我听说葛成在玄妙观聚众", # 37
            "我跟机友们商量怎么办",   # 38
            "我想去看看",              # 39
            "我决定跟着去",            # 40
            # 41-45: 反抗or逃离
            "我跟葛成他们去了",        # 41
            "我在想离乡",              # 42
            "我决定去月港闯闯",        # 43
            "我向老周打听月港的事",   # 44
            "我决定离乡",              # 45
            # 46-50: 离乡准备
            "我开始准备行李",          # 46
            "我向邻居告别",            # 47
            "我去牙行结算",            # 48
            "我算算盘缠够不够",        # 49
            "我去县衙办路引",          # 50
        ],
    },
    "B_weaving_female": {
        "identity": "weaving_female",
        "label": "织户女",
        "inputs": [
            "我在家络丝",               # 1
            "我帮丈夫理经线",            # 2
            "我今天去集市买染料",        # 3
            "我在作坊里干活",            # 4
            "我听邻居说行情",            # 5
            "我去牙行看看",              # 6
            "我和牙行的娘子聊",          # 7
            "我算了算账",                # 8
            "我去里长家里",              # 9
            "我听人说城里热闹",          # 10
            "我去桑田帮忙",              # 11
            "我在家晒丝",                # 12
            "我听说要加税",              # 13
            "我去县衙看看",              # 14
            "我和邻居嫂子聊",            # 15
            "我去镇上看看",              # 16
            "我整理家务",                # 17
            "牙人来压价了",              # 18
            "我劝丈夫别借钱",            # 19
            "我继续撑着",                # 20
            "今年行情不好",              # 21
            "我去茶馆听说",              # 22
            "我和丈夫商量",              # 23
            "我在家赶活",                # 24
            "我算算家里的账",            # 25
            "丈夫要卖织机",              # 26
            "我去丝市看看",              # 27
            "今天没活",                  # 28
            "我听说要派税监",            # 29
            "我和丈夫商量",              # 30
            "我去帮邻居家织布",          # 31
            "我去卖婆家帮忙",            # 32
            "我学会点新技艺",            # 33
            "牙行娘子介绍活",            # 34
            "我回家吃饭",                # 35
            "我听邻居说闹事",            # 36
            "我听说葛成",                # 37
            "我和女伴聊",                # 38
            "我想想未来",                # 39
            "我打算做点什么",            # 40
            "我去帮卖婆跑腿",            # 41
            "我开始学绣花",              # 42
            "我想卖绣品",                # 43
            "我向王婆请教",              # 44
            "我开始给富户送绣",          # 45
            "我接了一笔大单",            # 46
            "我开始独立卖绣",            # 47
            "我攒了点钱",                # 48
            "我打算再学点东西",          # 49
            "我想去苏州看看",            # 50
        ],
    },
}


def run_case(case_name: str, case_data: dict, save_root: Path) -> dict:
    """跑一个case"""
    print(f"\n{'=' * 60}")
    print(f"Case {case_name}: {case_data['label']}")
    print(f"{'=' * 60}")

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    save_manager = SaveManager(save_root / case_name)
    llm = MockDMChatModel(era_config=config)
    game = GameLoop(
        era_id="wanli1587",
        era_config=config,
        llm_model=llm,
        save_manager=save_manager,
        selected_identity=case_data["identity"],
    )

    start = time.time()
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        with patch("builtins.input", side_effect=case_data["inputs"] + ["/quit"]):
            try:
                game.run()
            except SystemExit:
                pass
    finally:
        sys.stdout = old_stdout
        elapsed = time.time() - start

    output = captured.getvalue()

    # 收集结果
    final_state = game.state
    summary = {
        "case": case_name,
        "identity": case_data["identity"],
        "label": case_data["label"],
        "elapsed": elapsed,
        "final_round": final_state.round_number,
        "final_date": final_state.current_date,
        "final_variables": dict(final_state.variables),
        "unlocked_insights": sorted(final_state.unlocked_insights),
        "triggered_events": sorted(final_state.triggered_events),
        "value_shifts": dict(final_state.value_shifts),
        "npc_levels": dict(final_state.npc_levels),
        "narrative_history_count": len(game.memory.events),
        "output_length": len(output),
        "errors": output.count("异常") + output.count("ERROR"),
    }

    # 打印本case的最终状态
    print(f"\n  回合: {summary['final_round']} ({summary['final_date']})")
    print(f"  用时: {elapsed:.1f}s")
    print(f"  解锁insight: {len(summary['unlocked_insights'])}条 → {summary['unlocked_insights']}")
    print(f"  触发事件: {len(summary['triggered_events'])}条 → {summary['triggered_events']}")
    print(f"  价值观: {summary['value_shifts']}")
    print(f"  事件记忆: {summary['narrative_history_count']}条")
    print(f"  输出长度: {summary['output_length']}字符")
    if summary["errors"] > 0:
        print(f"  ⚠️ 异常次数: {summary['errors']}")
    else:
        print(f"  ✅ 无异常")

    # 关键变量
    var = summary["final_variables"]
    print(f"\n  关键变量:")
    for k in ["livelihood", "silver_pressure", "tax_burden", "workshop_scale", "north_threat"]:
        if k in var:
            print(f"    {k}: {var[k]}")

    # 存档验证
    try:
        loaded = save_manager.load_state(game.session, "auto")
        assert loaded is not None
        assert loaded["round_number"] == summary["final_round"]
        print(f"  ✅ 存档/恢复一致（回合{loaded['round_number']}）")
    except Exception as e:
        print(f"  ❌ 存档验证失败: {e}")
        summary["errors"] += 1

    return summary


def main():
    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_50round_"))
    try:
        all_summaries = []
        for case_name, case_data in CASES.items():
            summary = run_case(case_name, case_data, tmp_root)
            all_summaries.append(summary)

        # === 综合报告 ===
        print("\n\n" + "=" * 60)
        print("50回合测试综合报告")
        print("=" * 60)

        print(f"\n{'Case':<25}{'回合':<8}{'insight':<10}{'事件':<8}{'异常':<6}{'用时':<8}")
        print("-" * 65)
        for s in all_summaries:
            print(f"{s['case'] + ' (' + s['label'] + ')':<25}"
                  f"{s['final_round']:<8}"
                  f"{len(s['unlocked_insights']):<10}"
                  f"{len(s['triggered_events']):<8}"
                  f"{s['errors']:<6}"
                  f"{s['elapsed']:.1f}s")

        # 对比
        if len(all_summaries) >= 2:
            print("\n性别对比:")
            male, female = all_summaries[0], all_summaries[1]
            print(f"  男性insight: {male['unlocked_insights']}")
            print(f"  女性insight: {female['unlocked_insights']}")

            male_only = set(male['unlocked_insights']) - set(female['unlocked_insights'])
            female_only = set(female['unlocked_insights']) - set(male['unlocked_insights'])
            common = set(male['unlocked_insights']) & set(female['unlocked_insights'])

            print(f"  仅男解锁: {male_only or '无'}")
            print(f"  仅女解锁: {female_only or '无'}")
            print(f"  共同解锁: {sorted(common) if common else '无'}")

        # 最终决策
        total_errors = sum(s["errors"] for s in all_summaries)
        if total_errors == 0:
            print("\n✅ 全部cases无异常")
        else:
            print(f"\n⚠️ 共{total_errors}个异常")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()