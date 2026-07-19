"""正式Insight测试

测试维度：
1. 覆盖率：14条insight中合理游戏流程能解锁多少
2. 依赖链：insight树的多级前置条件是否正确
3. 双路机制：player_explore vs narrative_guided
4. 持久化：存档恢复保留unlocked_insights
5. 触发词：玩家特定输入触发对应insight
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.mock_llm import MockDMChatModel
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import SaveManager


def test_insight_coverage():
    """测试1：覆盖率——跑20回合看解锁多少insight"""
    print("\n" + "=" * 60)
    print("[测试1] Insight覆盖率")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    total_insights = len(config.get("growth", {}).get("insight_tree", []))
    print(f"  时代包共定义{total_insights}条insight")

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_insight_test_"))
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

        # 跑20回合，每回合不同输入
        inputs = [
            "我在织机前理经线",          # 织丝相关 → ins_silk_trade
            "我听说今年税单重了",        # 税 → ins_silver_tax
            "我去里长那里问问",          # 里甲 → ins_li_jia
            "我听说城里可热闹",          # 城市 → ins_city_life
            "我去集市看看行情",          # 扩展贸易 → ins_expand_ambition
            "我和牙人谈了谈丝价",        # 牙行
            "听说京城出了大事",          # 南北 → ins_north_south
            "我想写封信给在北方的亲戚",  # 南北
            "我看到县衙贴出告示",        # 官僚 → ins_bureaucracy
            "我想去苏州看看",            # 城市
            "我今年多织了两匹绸",        # 银经济 → ins_silver_economy
            "我听说隔壁张三卖绸发了财",  # 道德/现实
            "我算了算上供的账",          # 上供陷阱 → ins_tribute_trap
            "我想再买一台织机",          # 扩展
            "我看到朝廷又在加税",        # 衰败信号 → ins_decline_signal
            "我听说北边蛮族在闹",        # 衰败
            "我觉得这生意越做越难",      # 无处可逃 → ins_no_escape
            "我做了个梦，梦里丝绸堆成山",  # 道德
            "我接了一笔大单",            # 扩展
            "我决定把织机都卖了",        # /quit
        ]

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
            output = captured.getvalue()

        unlocked = game.state.unlocked_insights
        coverage = len(unlocked) / total_insights if total_insights else 0
        print(f"\n  20回合后解锁: {len(unlocked)}/{total_insights} ({coverage*100:.0f}%)")
        print(f"  列表: {sorted(unlocked)}")

        # 期望：至少解锁3-5条基础insight（无前置或简单前置）
        assert len(unlocked) >= 3, f"应至少3条，实际{len(unlocked)}"
        print(f"  ✅ 基础insight覆盖率达标")

        # 关键insight检查
        expected_basic = ["ins_silk_trade", "ins_silver_tax", "ins_li_jia", "ins_city_life"]
        for iid in expected_basic:
            assert iid in unlocked, f"基础insight {iid} 应被解锁"
        print(f"  ✅ 4条基础insight全部解锁: {expected_basic}")

        # 期望：依赖链触发1-2条二级insight
        # ins_expand_ambition依赖ins_silk_trade
        # ins_north_south依赖ins_silver_tax + ins_li_jia
        # ins_bureaucracy依赖ins_li_jia
        # ins_silver_economy依赖ins_silk_trade + ins_silver_tax
        secondary_candidates = ["ins_expand_ambition", "ins_bureaucracy", "ins_north_south", "ins_silver_economy"]
        secondary_unlocked = [iid for iid in secondary_candidates if iid in unlocked]
        print(f"  二级insight解锁: {secondary_unlocked}")
        if secondary_unlocked:
            print(f"  ✅ 依赖链机制工作")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_insight_persistence():
    """测试2：持久化——存档恢复保留unlocked_insights"""
    print("\n" + "=" * 60)
    print("[测试2] Insight持久化")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_insight_persist_"))
    try:
        save_manager = SaveManager(tmp_root)

        # 第1次：跑2回合解锁insight
        llm1 = MockDMChatModel(era_config=config)
        game1 = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm1,
            save_manager=save_manager,
            selected_identity="weaving_male",
        )
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with patch("builtins.input", side_effect=["我听说城里可热闹", "我算了算今年的税", "/quit"]):
                try:
                    game1.run()
                except SystemExit:
                    pass
        finally:
            sys.stdout = old_stdout

        initial_unlocked = list(game1.state.unlocked_insights)
        print(f"  第1次跑2回合: unlocked={initial_unlocked}")

        # 存档
        loaded = save_manager.load_state(game1.session, "auto")
        assert loaded is not None
        print(f"  存档unlocked_insights: {loaded.get('unlocked_insights')}")
        assert loaded.get("unlocked_insights") == initial_unlocked

        # 第2次：从存档恢复
        llm2 = MockDMChatModel(era_config=config)
        game2 = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm2,
            save_manager=save_manager,
            session=game1.session,
            load_state_data=loaded,
        )
        restored_unlocked = game2.state.unlocked_insights
        print(f"  恢复后unlocked: {restored_unlocked}")
        assert restored_unlocked == initial_unlocked
        print(f"  ✅ 存档/恢复保留unlocked_insights")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_insight_trigger_keywords():
    """测试3：触发词——玩家特定输入触发对应insight"""
    print("\n" + "=" * 60)
    print("[测试3] Insight触发词")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    from history_footnote.rule_engine import RuleEngine

    engine = RuleEngine(config)

    # 创建初始state
    from history_footnote.game_state import make_initial_state
    state = make_initial_state("wanli1587", config, "weaving_male")

    # 测试cases: (input, expected_insight_substring)
    test_cases = [
        ("我在织机前织了一匹湖绫", "ins_silk_trade"),       # 织丝
        ("我听说今年税单重了", "ins_silver_tax"),           # 税
        ("我去里长那里问问", "ins_li_jia"),                # 里长
        ("我听说城里可真热闹", "ins_city_life"),           # 城
    ]

    for player_input, expected_id in test_cases:
        view = engine.make_view(state)
        candidates = engine.check_insights(view, player_input)
        ids = [c.id for c in candidates]
        print(f"  输入: {player_input[:20]} → {ids}")
        assert expected_id in ids, f"应触发{expected_id}，实际{ids}"
    print(f"  ✅ 触发词全部生效")


def test_insight_prerequisites():
    """测试4：依赖链——前置未满足则不返回候选"""
    print("\n" + "=" * 60)
    print("[测试4] Insight依赖链")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))
    from history_footnote.rule_engine import RuleEngine
    from history_footnote.game_state import make_initial_state

    engine = RuleEngine(config)

    # 创建state：模拟已解锁ins_silk_trade
    state = make_initial_state("wanli1587", config, "weaving_male")
    state.unlocked_insights.append("ins_silk_trade")
    state.unlocked_insights.append("ins_silver_tax")

    view = engine.make_view(state)

    # 测试1：依赖未满足（ins_bureaucracy需要ins_li_jia）
    candidates = engine.check_insights(view, "我在县衙告状")
    print(f"  只有ins_silk_trade + ins_silver_tax时输入'告状':")
    for c in candidates:
        print(f"    {c.id}")
    # ins_bureaucracy需要ins_li_jia作为前置 → 不应出现
    assert "ins_bureaucracy" not in [c.id for c in candidates], "前置未满足不应出现"
    print(f"  ✅ 前置依赖正确")

    # 测试2：解锁ins_li_jia后
    state.unlocked_insights.append("ins_li_jia")
    view = engine.make_view(state)
    candidates = engine.check_insights(view, "我在县衙告状")
    print(f"\n  解锁ins_li_jia后输入'告状':")
    for c in candidates:
        print(f"    {c.id}")
    assert "ins_bureaucracy" in [c.id for c in candidates], "前置满足应触发"
    print(f"  ✅ 依赖链解锁后生效")


def main():
    print("=" * 60)
    print("Insight 系统正式测试")
    print("=" * 60)

    test_insight_coverage()
    test_insight_persistence()
    test_insight_trigger_keywords()
    test_insight_prerequisites()

    print("\n" + "=" * 60)
    print("✅ Insight 测试全部通过")
    print("=" * 60)


if __name__ == "__main__":
    main()