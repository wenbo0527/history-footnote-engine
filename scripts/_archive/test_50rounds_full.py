"""50回合终极测试 - 覆盖全部insight的输入"""
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


INPUTS_ULTIMATE = [
    # 1-5: 织丝基础 (ins_silk_trade)
    "我在织机前织湖绫",
    "我继续织丝绸，做妻络夫织的活",
    "我把昨天织的湖绫拿到牙行去卖",
    "我去盛泽镇市集卖丝",
    "我在牙行听人说起湖州的双林镇",
    # 6-10: 城市与税 (ins_city_life, ins_silver_tax)
    "我去苏州城里看看",
    "我在苏州城里走了走",
    "我听说今年丝税要加",
    "我去里长那里问今年的税单",
    "我算了算今年要交的银",
    # 11-15: 读书与上层
    "我去县学看了看",                        # ins_bureaucracy
    "我听说李秀才中了举人",
    "我去城里的当铺典当了东西，用的是白银",   # ins_silver_economy（白银流通）
    "我听说京城出了大事",
    "我听说北边的蛮族在闹",
    # 16-20: 转折
    "我借了高利贷",
    "我决定扩大织机规模",                    # ins_expand_ambition
    "我算了算上供的账目",                    # ins_tribute_trap
    "我看到朝廷又在加税",
    "我听说朝廷党争严重",
    # 21-25: 道德困境
    "我和邻居张三聊怎么逃税",                # ins_moral_vs_reality
    "我去里长家求情",
    "我听说邻居张三发财了",
    "我想做更大的生意",
    "我算了算上供的丝绸要多少",
    # 26-30: 衰退信号
    "我看到县衙贴出告示",                    # ins_decline_signal
    "我听说京城在闹事",
    "我看到街上行人稀少",
    "我听说北边蛮族扣边",
    "我算了算上供的丝绸已经交不起了",
    # 31-35: 无处可逃
    "我觉得这生意越做越难",                  # ins_no_escape
    "我想逃到别处去",
    "我听说月港那边也难",
    "我想想出路在哪里",
    "我听说朝廷在抓逃户",
    # 36-40: 反向思考
    "我接了一笔大单",
    "我雇了三个机工",
    "我看到大机户的下场",                    # ins_bigger_not_better
    "我听说大商人亏了",
    "我算了算扩张的代价",
    # 41-45: 终极
    "我看到盛泽镇一片衰败",                  # ins_grand_failure
    "我听说苏州城里也乱了",
    "我听说月港的商人也亏了",
    "我算了算做了几十年还是老样子",
    "我决定把织机都卖了",
    "/quit",
]


def run_test():
    print("=" * 60)
    print("50回合终极测试（覆盖全部14条insight）")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_50full_"))
    try:
        save_manager = SaveManager(tmp_root)
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
            with patch("builtins.input", side_effect=INPUTS_ULTIMATE):
                try:
                    game.run()
                except SystemExit:
                    pass
        finally:
            sys.stdout = old_stdout
            elapsed = time.time() - start
            output = captured.getvalue()

        final_state = game.state
        all_ids = ['ins_silk_trade', 'ins_silver_tax', 'ins_li_jia', 'ins_city_life',
                   'ins_expand_ambition', 'ins_north_south', 'ins_bureaucracy',
                   'ins_silver_economy', 'ins_moral_vs_reality', 'ins_tribute_trap',
                   'ins_decline_signal', 'ins_no_escape', 'ins_bigger_not_better',
                   'ins_grand_failure']

        print(f"\n  回合: {final_state.round_number} ({final_state.current_date})")
        print(f"  用时: {elapsed:.1f}s")
        print(f"  解锁insight: {len(final_state.unlocked_insights)}/{len(all_ids)} ({len(final_state.unlocked_insights)/len(all_ids)*100:.0f}%)")
        print(f"  触发事件: {len(final_state.triggered_events)}条")
        print(f"  异常: {output.count('异常') + output.count('ERROR')}")

        print(f"\n  解锁详情（按顺序）:")
        unlocked = final_state.unlocked_insights
        for iid in all_ids:
            mark = "✅" if iid in unlocked else "❌"
            print(f"    {mark} {iid}")

        # 叙事独特性
        import re
        narrative_chunks = re.findall(r"DM叙事[^\n]*[\n\s]+(.+?)(?=\[状态\]|$)", output, re.DOTALL)
        unique_chunks = set(narrative_chunks)
        uniqueness = len(unique_chunks) / len(narrative_chunks) if narrative_chunks else 0
        print(f"\n  叙事独特性: {len(unique_chunks)}/{len(narrative_chunks)} ({uniqueness*100:.0f}%)")

        # 变量最终值
        var = final_state.variables
        print(f"\n  最终变量:")
        for k, v in sorted(var.items()):
            print(f"    {k}: {v}")

        # 存档验证
        loaded = save_manager.load_state(game.session, "auto")
        assert loaded["round_number"] == final_state.round_number
        print(f"\n  ✅ 存档验证通过")

        # 输出长度
        print(f"\n  输出总长度: {len(output)} 字符")
        print(f"  平均每回合: {len(output)//final_state.round_number} 字符")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    run_test()