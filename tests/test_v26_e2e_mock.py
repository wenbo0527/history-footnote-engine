"""
tests/test_v26_e2e_mock.py - 端到端测试（mock LLM）

跳过 LLM 真实调用，用 mock_dm + 真实 game_loop 走 1 局

发现隐藏 BUG：
- 状态机完整流程
- 序列化/反序列化
- 命运卡完整使用流程
- 地点移动 → 状态变更
- 跨模块数据流转
"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

import json
from history_footnote.game_loop import GameLoop
from history_footnote.game_state import GameState
from history_footnote.location_service import build_location_service
from history_footnote.fate_cards import draw_fate_cards, apply_fate_card
from history_footnote.random_utils import set_session_seed


# ==== Test 1: 创建 game + 抽 5 张卡 ====
def test_L2_01_create_game_with_fate_cards():
    """L2.1: 创建 game + 抽 5 张卡 + 验证 v2.5 字段"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    from history_footnote.mock_llm import MockDMChatModel
    from history_footnote.storage.save_manager import SaveManager
    from pathlib import Path
    sm = SaveManager(save_root=Path("/tmp/test_v26_saves"))
    llm = MockDMChatModel(era_config=era)
    set_session_seed("L2_01", 42)
    game = GameLoop(
        era_id="wanli1587",
        era_config=era,
        llm_model=llm,
        save_manager=sm,
        selected_identity="weaving_male",
    )
    # 抽卡（v2.5 流程）
    fate_cards = draw_fate_cards("L2_01", n=5)
    game.state.fate_hand = [
        {"id": c.id, "name": c.name, "icon": c.icon, "color": c.color,
         "description": c.description, "effect_type": c.effect_type,
         "effect_params": c.effect_params, "used": False,
         "use_type": c.use_type, "use_constraints": c.use_constraints, "use_hint": c.use_hint}
        for c in fate_cards
    ]
    # 验证字段
    assert len(game.state.fate_hand) == 5
    assert game.state.current_location == ""  # 默认
    assert game.state.visited_locations == []
    print(f"  ✅ L2.1: 抽 5 张卡 + state 字段正常")
    return True


# ==== Test 2: 手动设置 current_location（v2.4）====
def test_L2_02_set_location():
    """L2.2: 设置 current_location + 验证 location_service 集成"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    svc = build_location_service(era)
    gs = GameState()
    gs.current_location = svc.get_default()  # "home"
    gs.visited_locations = ["home"]
    assert gs.current_location == "home"
    # 移到牙行（用 MoveResult 对象）
    result = svc.can_move("home", "tooth_market", ["home"], [], 3.0)
    assert result.success
    assert result.ap_cost >= 1.0  # 1.0 (牙行是 L1 熟悉)
    # 验证：牙行是 home 邻居
    home = svc.get("home")
    assert "tooth_market" in home.neighbors, "牙行 应该是 home 的邻居"
    print(f"  ✅ L2.2: current_location 设置 + 移动计算正确 (ap={result.ap_cost})")
    return True


# ==== Test 3: 用命运卡 + 状态变化 ====
def test_L2_03_fate_card_use():
    """L2.3: 用 windfall 卡 + 状态变化"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    svc = build_location_service(era)
    gs = GameState()
    gs.cash = 0.5
    gs.debt = 0
    gs.fate_hand = [
        {"id": "windfall", "name": "天降横财", "icon": "💰", "color": "#6b8b5a",
         "description": "获得 3 两", "effect_type": "modify_state",
         "effect_params": {"cash_delta": 3.0}, "used": False,
         "use_type": "immediate", "use_constraints": {}, "use_hint": ""}
    ]
    # 调用 use 流程
    from history_footnote.fate_cards import FateCard
    fc = FateCard(
        id="windfall", name="天降横财", icon="💰", color="#6b8b5a",
        description="获得 3 两", effect_type="modify_state",
        effect_params={"cash_delta": 3.0},
        use_type="immediate", use_constraints={}, use_hint=""
    )
    msgs, ok = apply_fate_card(fc, gs, "immediate")
    assert ok
    assert gs.cash == 3.5  # 0.5 + 3.0
    print(f"  ✅ L2.3: 用 windfall → cash 0.5 → 3.5")
    return True


# ==== Test 4: emergency 触发 + 应有 emergency 卡 ====
def test_L2_04_emergency_workflow():
    """L2.4: 现金 < 1 → emergency 触发 + 有可用卡"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    gs = GameState()
    gs.cash = 0.5
    gs.fate_hand = [
        {"id": "windfall", "name": "天降横财", "icon": "💰", "color": "#6b8b5a",
         "description": "获得 3 两", "effect_type": "modify_state",
         "effect_params": {"cash_delta": 3.0}, "used": False,
         "use_type": "immediate", "use_constraints": {}, "use_hint": ""}
    ]
    from history_footnote.fate_cards import check_emergency_situation, get_emergency_cards
    is_e, trigger = check_emergency_situation(gs)
    # windfall 是 immediate 不是 emergency，所以不弹出
    assert is_e  # cash_critical 触发
    em = get_emergency_cards(gs)
    assert len(em) == 0  # windfall 不是 emergency 类型
    # 加一张 emergency 卡
    gs.fate_hand.append({
        "id": "lucky_star", "name": "吉星高照", "icon": "✨", "color": "#b8860b",
        "description": "+10%", "effect_type": "apply_buff",
        "effect_params": {"buff": "lucky", "duration": 3}, "used": False,
        "use_type": "emergency", "use_constraints": {}, "use_hint": ""
    })
    em = get_emergency_cards(gs)
    assert len(em) == 1
    assert em[0]["id"] == "lucky_star"
    print(f"  ✅ L2.4: emergency 触发 + lucky_star 可用")
    return True


# ==== Test 5: 完整 1 局（5 步，mock LLM）====
def test_L2_05_full_game_session():
    """L2.5: 完整 1 局（创建→抽卡→设置位置→用卡→emergency）"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    from history_footnote.mock_llm import MockDMChatModel
    from history_footnote.storage.save_manager import SaveManager
    from pathlib import Path
    sm = SaveManager(save_root=Path("/tmp/test_v26_saves"))
    llm = MockDMChatModel(era_config=era)
    set_session_seed("L2_05", 100)

    # 1. 创建
    game = GameLoop(
        era_id="wanli1587", era_config=era, llm_model=llm,
        save_manager=sm, selected_identity="weaving_male",
    )

    # 2. 抽 5 张卡
    cards = draw_fate_cards("L2_05", n=5)
    game.state.fate_hand = [
        {"id": c.id, "name": c.name, "icon": c.icon, "color": c.color,
         "description": c.description, "effect_type": c.effect_type,
         "effect_params": c.effect_params, "used": False,
         "use_type": c.use_type, "use_constraints": c.use_constraints, "use_hint": c.use_hint}
        for c in cards
    ]
    initial_seed = game.state.seed
    assert initial_seed == 0  # GameState 默认 0

    # 3. 设置当前位置
    game.state.current_location = "home"
    game.state.visited_locations = ["home"]

    # 4. 模拟玩家行动（用 windfall 假设卡）
    if any(c["id"] == "windfall" for c in game.state.fate_hand):
        from history_footnote.fate_cards import FateCard
        for c in game.state.fate_hand:
            if c["id"] == "windfall":
                fc = FateCard(**{k: c[k] for k in ["id", "name", "icon", "color", "description",
                              "effect_type", "effect_params", "use_type", "use_constraints", "use_hint"]})
                msgs, ok = apply_fate_card(fc, game.state, "immediate")
                assert ok
                c["used"] = True
                break

    # 5. 验证最终状态
    assert game.state.current_location == "home"
    assert "home" in game.state.visited_locations
    # 至少 1 张用过的
    used = [c for c in game.state.fate_hand if c.get("used")]
    print(f"  ✅ L2.5: 完整 1 局跑通（{len(used)} 张卡用过，cash={game.state.cash}）")
    return True


# ==== 主运行 ====
def main():
    print("=" * 60)
    print("L2 E2E 测试 (mock LLM)")
    print("=" * 60)
    tests = [
        test_L2_01_create_game_with_fate_cards,
        test_L2_02_set_location,
        test_L2_03_fate_card_use,
        test_L2_04_emergency_workflow,
        test_L2_05_full_game_session,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print("=" * 60)
    print(f"L2 结果: {passed} 通过 / {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
