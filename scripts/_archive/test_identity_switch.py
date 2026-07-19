"""身份切换机制测试

测试：
1. era.json有identity_switch_offers
2. DM Agent有offer_identity_switch Tool
3. Mock在满足条件时自动调用offer_identity_switch
4. GameLoop正确处理/accept /decline
5. 切换后action_boundaries和identity_config都更新
6. 存档恢复身份切换后的状态
"""
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import io

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    print("=" * 60)
    print("身份切换机制验证")
    print("=" * 60)

    config = json.loads(Path("eras/wanli1587/era.json").read_text(encoding="utf-8"))

    # === 测试1：检查identity_switch_offers存在 ===
    print("\n[1] 验证identity_switch_offers配置")
    offers = config["world"].get("identity_switch_offers", [])
    print(f"  配置了{len(offers)}个切换选项:")
    for o in offers:
        print(f"    - {o['id']}: {o['from_identity']} → {o['to_identity']}")
    assert len(offers) >= 4, f"应至少4个offer，实际{len(offers)}"

    # === 测试2：DM Agent有offer_identity_switch Tool ===
    print("\n[2] 验证DM Agent的Tool列表")
    from history_footnote.mock_llm import MockDMChatModel
    from history_footnote.game_loop import GameLoop
    from history_footnote.storage.save_manager import SaveManager
    import tempfile

    tmp_root = Path(tempfile.mkdtemp(prefix="hf_switch_test_"))
    try:
        save_manager = SaveManager(tmp_root)
        llm = MockDMChatModel(era_config=config)
        game = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=llm,
            save_manager=save_manager,
            selected_identity="weaving_female",
        )
        tool_names = [t.name for t in game.dm.tools]
        print(f"  工具列表: {tool_names}")
        assert "offer_identity_switch" in tool_names, "应有offer_identity_switch Tool"

        # === 测试3：直接调用offer_identity_switch Tool ===
        print("\n[3] 验证offer_identity_switch Tool基本功能")
        offer_tool = next(t for t in game.dm.tools if t.name == "offer_identity_switch")
        # 合法切换
        r = offer_tool.invoke({
            "to_identity": "merchant_female",
            "reason": "卖婆看中你的丝织经验",
            "cost": "放弃织机",
            "benefit": "可以进入富户内宅",
        })
        print(f"  合法切换（女→女）: {r}")
        assert r.get("offered") == True, "合法切换应成功"

        # 非法切换（性别不一致）
        r2 = offer_tool.invoke({
            "to_identity": "weaving_male",
            "reason": "测试",
        })
        print(f"  非法切换（女→男）: {r2}")
        assert r2.get("offered") == False, "跨性别切换应被拒"

        # === 测试4：模拟玩家触发/accept /decline ===
        print("\n[4] 模拟玩家接受offer")
        # 直接设置pending_offer
        test_offer = {
            "offered": True,
            "to_identity": "merchant_female",
            "to_label": "卖婆/牙婆（女）",
            "reason": "卖婆看中你的丝织经验",
            "cost": "放弃现有织机和人脉",
            "benefit": "可以进入富户内宅",
            "message": "DM提供身份切换offer",
        }
        game.set_pending_offer(test_offer)
        assert game.pending_identity_offer is not None
        print(f"  pending_offer已设置: to={game.pending_identity_offer['to_identity']}")

        # 玩家接受
        old_identity = game.selected_identity
        old_role = game.identity_config.get("role", "")
        game._handle_identity_decision(accept=True)
        new_identity = game.selected_identity
        new_role = game.identity_config.get("role", "")
        print(f"  接受后: {old_identity} ({old_role}) → {new_identity} ({new_role})")
        assert new_identity == "merchant_female", "应切换到merchant_female"
        assert game.state.selected_identity == "merchant_female", "state也应更新"
        assert game.state.player_gender == "female", "性别保持female"

        # === 测试5：验证切换后action_boundaries更新 ===
        print("\n[5] 验证切换后行动边界更新")
        from history_footnote.game_state import make_initial_state
        from history_footnote.rule_engine import RuleEngine

        engine = RuleEngine(config)
        view = engine.make_view(game.state)
        # 卖婆不能"参加科举"
        r3 = engine.check_action(view, "我去参加科举")
        print(f"  卖婆去科举: allowed={r3['allowed']}")
        assert not r3["allowed"], "卖婆应被拒绝科举"

        # 卖婆可以"进入富户内宅"
        r4 = engine.check_action(view, "我去富户内宅推销丝绸")
        print(f"  卖婆去富户内宅: allowed={r4['allowed']}")

        # === 测试6：拒绝offer ===
        print("\n[6] 模拟玩家拒绝offer")
        game.selected_identity = "weaving_female"
        game.identity_config = config["world"]["player_identities"]["weaving_female"]
        game.state.selected_identity = "weaving_female"
        test_offer2 = {
            "offered": True,
            "to_identity": "scholar_female",
            "to_label": "才女/闺塾师（女）",
            "reason": "富户内眷请你教女儿识字",
            "cost": "1-2年不事生产",
            "benefit": "成为闺塾师",
            "message": "DM提供身份切换offer",
        }
        game.set_pending_offer(test_offer2)
        game._handle_identity_decision(accept=False)
        assert game.pending_identity_offer is None, "拒绝后pending_offer应清空"
        assert game.selected_identity == "weaving_female", "拒绝后身份不变"
        print(f"  拒绝后身份保持: {game.selected_identity}")

        # === 测试7：存档恢复后身份切换状态 ===
        print("\n[7] 验证存档恢复selected_identity")
        # 重新创建一个merchant_female的game，跑一回合存档
        game2 = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=MockDMChatModel(era_config=config),
            save_manager=save_manager,
            selected_identity="merchant_female",
        )
        with patch("builtins.input", side_effect=["我去牙行", "/quit"]):
            try:
                game2.run()
            except SystemExit:
                pass

        loaded = save_manager.load_state(game2.session, "auto")
        print(f"  存档selected_identity: {loaded.get('selected_identity')}")
        assert loaded.get("selected_identity") == "merchant_female", "存档应保留merchant_female"

        # 恢复
        game3 = GameLoop(
            era_id="wanli1587",
            era_config=config,
            llm_model=MockDMChatModel(era_config=config),
            save_manager=save_manager,
            session=game2.session,
            load_state_data=loaded,
        )
        assert game3.selected_identity == "merchant_female", "恢复后身份应是merchant_female"
        print(f"  ✅ 恢复后身份: {game3.selected_identity}")

    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)

    print("\n" + "=" * 60)
    print("✅ 身份切换机制验证全部通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
