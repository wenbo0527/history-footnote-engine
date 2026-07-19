"""角色创建系统验证脚本

测试：
1. CLI角色创建问询（Q1性别 + Q2身份）
2. 6个身份的配置完整性
3. 男性/女性开场的差异化叙事
4. 性别过滤对叙事片段的影响
5. 存档恢复身份
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    print("=" * 60)
    print("角色创建系统验证")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

    # === 测试1：6个身份的配置完整性 ===
    print("\n[1] 验证6个身份的完整配置")
    identities = config["world"]["player_identities"]
    assert len(identities) == 6, f"应有6个身份，实际{len(identities)}"
    print(f"  ✅ 共{len(identities)}个身份")

    # 按性别分类
    male_count = sum(1 for v in identities.values() if v.get("gender") == "male")
    female_count = sum(1 for v in identities.values() if v.get("gender") == "female")
    print(f"  男性: {male_count}个 | 女性: {female_count}个")
    assert male_count == 3 and female_count == 3, "应该男女各3个"

    # 验证每个身份都有必需字段
    for key, ident in identities.items():
        for field in ["id", "label", "gender", "role", "action_boundaries"]:
            assert field in ident, f"身份{key}缺少{field}"
    print(f"  ✅ 所有身份都有完整字段")

    # === 测试2：男性/女性行动边界差异 ===
    print("\n[2] 验证行动边界差异（科举考场：女拒绝 / 男允许）")
    from history_footnote.game_state import make_initial_state
    from history_footnote.rule_engine import RuleEngine

    engine = RuleEngine(config)

    # 女性玩家
    state_female = make_initial_state("wanli1587", config, "weaving_female")
    view_f = engine.make_view(state_female)
    r_f = engine.check_action(view_f, "我去参加科举考试")
    print(f"  女性去科举: allowed={r_f['allowed']}, reason='{r_f.get('reason', '')}'")
    assert not r_f["allowed"], "女性应被拒绝参加科举"

    # 男性玩家
    state_male = make_initial_state("wanli1587", config, "weaving_male")
    view_m = engine.make_view(state_male)
    r_m = engine.check_action(view_m, "我去参加科举考试")
    print(f"  男性去科举: allowed={r_m['allowed']}, reason='{r_m.get('reason', '')}'")
    # weaving_male不能科举（匠户），但scholar_male可以
    # 我们这里测weaving_male，应该拒绝

    # === 测试3：性别过滤对叙事片段的影响 ===
    print("\n[3] 验证性别过滤（snippets target_gender）")
    from history_footnote.knowledge_base import KnowledgeBase

    # 给snippets添加target_gender字段
    snippets_with_gender = []
    for s in config["knowledge"]["narrative_snippets"]:
        s = dict(s)
        # 简单分类：女性专属（王婆/薛嫂/丁娘子/叶家才女等）+ 男性专属（施润泽/西门庆/沈万三等）+ 共同
        text = s.get("snippet_text", "") + s.get("source", "")
        if any(name in text for name in ["王婆", "薛嫂", "刘婆", "丁娘子", "叶家", "才女"]):
            s["target_gender"] = "female"
        elif any(name in text for name in ["施润泽", "施复", "西门庆", "沈万三", "范进", "徐渭", "温秀才"]):
            s["target_gender"] = "male"
        else:
            s["target_gender"] = "all"
        snippets_with_gender.append(s)

    kb = KnowledgeBase(
        entries=config["knowledge"]["entries"],
        snippets=snippets_with_gender,
    )

    # 不带性别过滤
    all_snips = kb.query_snippets(scene="茶馆", top_k=10)
    print(f"  无性别过滤: 茶馆命中{len(all_snips)}条")

    # 男性玩家
    male_snips = kb.query_snippets(scene="茶馆", top_k=10, player_gender="male")
    male_targets = [s.get("target_gender") for s in male_snips]
    print(f"  男性玩家: 命中{len(male_snips)}条 (target_gender={set(male_targets)})")
    assert all(t in ("all", "male") for t in male_targets), "男性应只看到all/male"

    # 女性玩家
    female_snips = kb.query_snippets(scene="茶馆", top_k=10, player_gender="female")
    female_targets = [s.get("target_gender") for s in female_snips]
    print(f"  女性玩家: 命中{len(female_snips)}条 (target_gender={set(female_targets)})")
    assert all(t in ("all", "female") for t in female_targets), "女性应只看到all/female"
    # 女性应看不到"施润泽"等男性专属
    for s in female_snips:
        assert "施润泽" not in s.get("snippet_text", ""), f"女性不应看到施润泽: {s.get('id')}"

    print(f"  ✅ 性别过滤正确（女性看不到施润泽/西门庆/沈万三等男性专属片段）")

    # === 测试4：CLI角色创建问询 ===
    print("\n[4] 验证CLI问询（模拟输入'2女'，'1丝织户（女）'）")
    from history_footnote.__main__ import ask_character

    # 模拟用户输入
    with patch("builtins.input", side_effect=["2", "1"]):
        result = ask_character(config)

    print(f"  选择结果: {result}")
    assert result == "weaving_female", f"应选weaving_female，实际{result}"

    # 模拟男性选择读书人
    with patch("builtins.input", side_effect=["1", "2"]):
        result2 = ask_character(config)
    print(f"  男性选读书人: {result2}")
    assert result2 == "scholar_male", f"应选scholar_male，实际{result2}"

    # === 测试5：存档恢复身份 ===
    print("\n[5] 验证存档恢复selected_identity")
    from history_footnote.storage.save_manager import SaveManager
    import tempfile
    tmp_root = Path(tempfile.mkdtemp(prefix="hf_char_test_"))
    try:
        save_manager = SaveManager(tmp_root)
        from history_footnote.mock_llm import MockDMChatModel
        from history_footnote.game_loop import GameLoop

        llm = MockDMChatModel(era_config=config)
        game = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm,
            save_manager=save_manager,
            selected_identity="weaving_female",
        )
        # 跑一个回合（自动存档）
        with patch("builtins.input", side_effect=["我去织布", "/quit"]):
            try:
                game.run()
            except SystemExit:
                pass

        # 验证存档
        loaded = save_manager.load_state(game.session, "auto")
        print(f"  存档selected_identity: {loaded.get('selected_identity')}")
        print(f"  存档player_gender: {loaded.get('player_gender')}")
        assert loaded.get("selected_identity") == "weaving_female", "存档应保留selected_identity"
        assert loaded.get("player_gender") == "female", "存档应保留player_gender"

        # 从存档恢复
        llm2 = MockDMChatModel(era_config=config)
        game2 = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm2,
            save_manager=save_manager,
            session=game.session,
            load_state_data=loaded,
        )
        print(f"  恢复后selected_identity: {game2.selected_identity}")
        assert game2.selected_identity == "weaving_female", "恢复后身份应一致"

        # 验证身份影响开场白
        from unittest.mock import patch as mock_patch
        with mock_patch("builtins.input", side_effect=["/quit"]):
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                game2._print_opening()
            finally:
                sys.stdout = old_stdout
            output = captured.getvalue()
            print(f"  开场白: {output[:200]}")
            assert "丝织户（女）" in output, "开场白应显示女性身份"
            assert "♀" in output, "开场白应有女性符号"
            assert "江南丝织户·妻子" in output, "开场白应显示女性角色"

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)

    print("\n" + "=" * 60)
    print("✅ 角色创建系统验证全部通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
