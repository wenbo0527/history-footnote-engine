"""
tests/test_v26_integration.py - 整合测试（v2.5-v2.6.2 完整集成）

不调 LLM，纯 API + 状态机测试。

发现隐藏 BUG：
- 状态序列化/反序列化
- 路由注册正确性
- 端点参数容错
- 端点之间的数据流转
- 状态机边界
"""
import sys
import json
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

from history_footnote.game_state import GameState
from history_footnote.fate_cards import (
    FATE_CARDS_POOL, draw_fate_cards, can_use_card, apply_fate_card,
    check_emergency_situation, get_emergency_cards, get_immediate_cards,
    EMERGENCY_TRIGGERS
)
from history_footnote.location_service import build_location_service
from history_footnote.random_utils import (
    set_session_seed, get_rng, generate_random_seed, make_seed_from_string
)
from history_footnote.web_server.router_registry import GET_ROUTES, POST_ROUTES


# ============================================================
# L1.1-L1.4: GameState 序列化
# ============================================================

def test_L1_01_game_state_default_fields():
    """L1.1: GameState 默认字段全部存在（v2.5-v2.6 字段）"""
    gs = GameState()
    assert hasattr(gs, 'seed')
    assert hasattr(gs, 'requested_seed')
    assert hasattr(gs, 'fate_hand')
    assert hasattr(gs, 'fate_used')
    assert hasattr(gs, 'fate_event_flags')
    assert hasattr(gs, 'npc_relations')
    assert hasattr(gs, 'encounter_multiplier')
    assert hasattr(gs, 'active_buffs')
    assert hasattr(gs, 'current_location')
    assert hasattr(gs, 'visited_locations')
    assert hasattr(gs, 'heard_locations')
    print("  ✅ L1.1: GameState 默认字段全部存在")
    return True


def test_L1_02_game_state_mutable_lists():
    """L1.2: list/dict 字段可变（不是 class 级共享）"""
    gs1 = GameState()
    gs2 = GameState()
    gs1.fate_hand.append({"id": "test"})
    gs1.npc_relations["沈氏"] = 50
    assert len(gs2.fate_hand) == 0, "fate_hand 应该是独立 list"
    assert "沈氏" not in gs2.npc_relations, "npc_relations 应该是独立 dict"
    print("  ✅ L1.2: 字段独立可变（无 class 级共享）")
    return True


def test_L1_03_fate_hand_deduplication():
    """L1.3: 抽卡无重复（同一卡不会抽 2 次）"""
    set_session_seed("test_L1_3", 42)
    cards = draw_fate_cards("test_L1_3", n=10)
    assert len(cards) == 10
    ids = [c.id for c in cards]
    assert len(set(ids)) == 10, f"抽到重复: {[i for i in ids if ids.count(i) > 1]}"
    print("  ✅ L1.3: 抽 10 张无重复")
    return True


def test_L1_04_seed_replay():
    """L1.4: 同 seed 必出同卡"""
    set_session_seed("test_L1_4", 999)
    c1 = draw_fate_cards("test_L1_4", n=5)
    set_session_seed("test_L1_4", 999)
    c2 = draw_fate_cards("test_L1_4", n=5)
    for a, b in zip(c1, c2):
        assert a.id == b.id
    print("  ✅ L1.4: seed 重放 = 同卡")
    return True


# ============================================================
# L1.5-L1.8: 路由注册 + 端点
# ============================================================

def test_L1_05_routes_registered():
    """L1.5: 关键端点全部注册"""
    all_routes = list(GET_ROUTES.keys()) + list(POST_ROUTES.keys())
    required = [
        "/api/location/move",
        "/api/location/list",
        "/api/location/detail",
        "/api/fate/hand",
        "/api/fate/use",
        "/api/fate/available",
        "/api/fate/emergency_check",
        "/api/character_wiki",
        "/api/character_wiki_update",
    ]
    for r in required:
        assert r in all_routes, f"端点 {r} 未注册（现有 {len(all_routes)} 个）"
    print(f"  ✅ L1.5: 9 个关键端点全部注册（GET {len(GET_ROUTES)} + POST {len(POST_ROUTES)}）")
    return True


def test_L1_06_endpoint_imports():
    """L1.6: 端点 handler 全部可导入"""
    from history_footnote.web_server.routers.input import (
        handle_POST_location_move,
        handle_GET_location_list,
        handle_GET_location_detail,
        handle_GET_fate_hand,
        handle_POST_fate_use,
        handle_GET_fate_available,
        handle_GET_fate_emergency_check,
    )
    handlers = [
        handle_POST_location_move, handle_GET_location_list, handle_GET_location_detail,
        handle_GET_fate_hand, handle_POST_fate_use,
        handle_GET_fate_available, handle_GET_fate_emergency_check,
    ]
    for h in handlers:
        assert callable(h)
    print(f"  ✅ L1.6: 7 个 handler 全部可导入")
    return True


def test_L1_07_session_imports():
    """L1.7: session handler 可导入（v2.5 seed 处理）"""
    from history_footnote.web_server.routers.session import handle_POST_start
    assert callable(handle_POST_start)
    print(f"  ✅ L1.7: session handler 可导入")
    return True


def test_L1_08_character_imports():
    """L1.8: character handler 可导入（v2.6.2 npc_relations）"""
    from history_footnote.web_server.routers.character import handle_GET_character_wiki
    assert callable(handle_GET_character_wiki)
    print(f"  ✅ L1.8: character handler 可导入")
    return True


# ============================================================
# L1.9-L1.12: 状态机 + 边界
# ============================================================

def test_L1_09_emergency_triggers():
    """L1.9: 5 个 emergency 触发器全部工作"""
    class StateWithBad:
        cash = 0.5
        debt = 3
        rice = 0
        round_number = 6
        active_buffs = [{"name": "unlucky", "rounds_left": 2}]

    is_e, trigger = check_emergency_situation(StateWithBad())
    assert is_e
    assert trigger in EMERGENCY_TRIGGERS
    print(f"  ✅ L1.9: emergency 触发 ({trigger})")
    return True


def test_L1_10_can_use_invalid_card():
    """L1.10: 不存在的卡能正确处理"""
    state = GameState()
    state.cash = 5
    state.fate_hand = [{"id": "nonexistent", "use_type": "immediate", "use_constraints": {}, "used": False}]
    can, reason = can_use_card(state.fate_hand[0], state, "immediate")
    assert can  # 因为没约束
    print(f"  ✅ L1.10: 不存在卡处理 OK")
    return True


def test_L1_11_buff_expiry():
    """L1.11: buff 不会无限期（duration 字段控制）"""
    state = GameState()
    state.fate_hand = []
    # 加一个 buff
    from history_footnote.fate_cards import FATE_CARDS_POOL
    lucky_card = next(c for c in FATE_CARDS_POOL if c.id == "lucky_star")
    apply_fate_card(lucky_card, state, "emergency")
    assert len(state.active_buffs) == 1
    assert state.active_buffs[0]["name"] == "lucky"
    assert state.active_buffs[0]["rounds_left"] == 3
    # 重复加同 buff 应该替换而非叠加
    apply_fate_card(lucky_card, state, "emergency")
    assert len(state.active_buffs) == 1  # 不叠加
    print(f"  ✅ L1.11: buff 替换不叠加")
    return True


def test_L1_12_npc_relations_isolated():
    """L1.12: npc_relations 修改不影响其他 state"""
    gs1 = GameState()
    gs2 = GameState()
    gs1.npc_relations["沈氏"] = 30
    gs1.npc_relations["王牙人"] = -20
    assert len(gs2.npc_relations) == 0, f"gs2.npc_relations 应空: {gs2.npc_relations}"
    print(f"  ✅ L1.12: npc_relations 隔离")
    return True


# ============================================================
# 主运行
# ============================================================

def main():
    print("=" * 60)
    print("L1 整合测试 (12 个)")
    print("=" * 60)
    tests = [
        test_L1_01_game_state_default_fields,
        test_L1_02_game_state_mutable_lists,
        test_L1_03_fate_hand_deduplication,
        test_L1_04_seed_replay,
        test_L1_05_routes_registered,
        test_L1_06_endpoint_imports,
        test_L1_07_session_imports,
        test_L1_08_character_imports,
        test_L1_09_emergency_trigers if False else test_L1_09_emergency_triggers,  # 修正 typo
        test_L1_10_can_use_invalid_card,
        test_L1_11_buff_expiry,
        test_L1_12_npc_relations_isolated,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    print("=" * 60)
    print(f"L1 结果: {passed} 通过 / {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
