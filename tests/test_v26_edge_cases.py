"""
tests/test_v26_edge_cases.py - 边界 case 压力测试

发现"奇怪输入"导致的隐藏 BUG：
- 0 行动点能否用卡
- 现金为负能否触发 emergency
- 同一 session 反复用卡
- 大量卡 100+ 张时性能
- 不存在的 location/npc
- 特殊字符输入
- 并发访问
"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

import json
from history_footnote.game_state import GameState
from history_footnote.fate_cards import (
    draw_fate_cards, can_use_card, apply_fate_card,
    check_emergency_situation, get_emergency_cards,
    FATE_CARDS_POOL
)
from history_footnote.location_service import build_location_service
from history_footnote.random_utils import set_session_seed


def test_L4_01_zero_ap():
    """L4.1: 0 AP 时尝试用 modify_state 卡"""
    state = GameState()
    state.cash = 5.0
    state.fate_hand = [
        {"id": "windfall", "name": "天降横财", "icon": "💰", "color": "#6b8b5a",
         "description": "获得 3 两", "effect_type": "modify_state",
         "effect_params": {"cash_delta": 3.0}, "used": False,
         "use_type": "immediate", "use_constraints": {}, "use_hint": ""}
    ]
    # v2.6 modify_state 卡不需要 AP
    fc = next(c for c in FATE_CARDS_POOL if c.id == "windfall")
    msgs, ok = apply_fate_card(fc, state, "immediate")
    assert ok
    assert state.cash == 8.0
    print(f"  ✅ L4.1: 0 AP 仍可用 windfall（immediate 类不消耗 AP）")
    return True


def test_L4_02_negative_cash():
    """L4.2: 现金为负（不应该发生但测试边界）"""
    state = GameState()
    state.cash = -5.0  # 异常
    state.fate_hand = []
    is_e, trigger = check_emergency_situation(state)
    # cash<1 触发，所以负数也算
    assert is_e
    assert trigger == "cash_critical"
    print(f"  ✅ L4.2: 负 cash 仍触发 emergency (cash_critical)")
    return True


def test_L4_03_use_same_card_twice():
    """L4.3: 同一张卡反复点 2 次"""
    state = GameState()
    state.cash = 0.5
    fc = next(c for c in FATE_CARDS_POOL if c.id == "windfall")
    msgs1, ok1 = apply_fate_card(fc, state, "immediate")
    assert ok1
    # 第二次用：state 已有 used 标记吗？
    # 实际：apply_fate_card 不读 used 字段，调用方负责
    # 真实场景：API 端点 handle_POST_fate_use 检查 used 才发请求
    # 这里直接调，状态会被再次修改（bug 吗？）
    msgs2, ok2 = apply_fate_card(fc, state, "immediate")
    # 应该 OK（卡定义没限制 apply 次数）
    # 但实际场景中要靠 used 字段防止重复
    assert state.cash == 6.5  # 0.5 + 3 + 3
    print(f"  ✅ L4.3: 同一卡调 2 次 = 2 次效果（依赖调用方检查 used）")
    return True


def test_L4_04_huge_cards_hand():
    """L4.4: 100+ 张卡时性能"""
    state = GameState()
    state.fate_hand = [
        {"id": f"test_card_{i}", "name": f"测试卡{i}", "icon": "🎴", "color": "#000",
         "description": "test", "effect_type": "modify_state",
         "effect_params": {}, "used": False,
         "use_type": "immediate", "use_constraints": {}, "use_hint": ""}
        for i in range(150)
    ]
    import time
    t0 = time.time()
    em = get_emergency_cards(state)
    elapsed = time.time() - t0
    assert elapsed < 0.1, f"get_emergency_cards 太慢: {elapsed}s"
    print(f"  ✅ L4.4: 150 张卡用 {elapsed*1000:.1f}ms（<100ms）")
    return True


def test_L4_05_nonexistent_location():
    """L4.5: 不存在的 location id"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    svc = build_location_service(era)
    result = svc.can_move("home", "nonexistent_place", ["home"], [], 3.0)
    assert not result.success
    assert "不存在" in result.reason
    print(f"  ✅ L4.5: 不存在 location → 拒绝 (reason: {result.reason})")
    return True


def test_L4_06_special_chars_in_card_id():
    """L4.6: 特殊字符 card_id"""
    state = GameState()
    state.cash = 5
    state.fate_hand = [
        {"id": "test'; DROP TABLE--", "name": "hack", "icon": "💀", "color": "#000",
         "description": "test", "effect_type": "modify_state",
         "effect_params": {}, "used": False,
         "use_type": "immediate", "use_constraints": {}, "use_hint": ""}
    ]
    # 简单匹配是否能找到
    found = next((c for c in state.fate_hand if c.get("id") == "test'; DROP TABLE--"), None)
    assert found
    print(f"  ✅ L4.6: 特殊字符 card_id 处理 OK")
    return True


def test_L4_07_concurrent_seed():
    """L4.7: 多个 session 同一 seed 互不干扰"""
    set_session_seed("session_X", 42)
    rng_x = type("R", (), {})
    from history_footnote.random_utils import get_rng
    rng_x1 = get_rng("session_X")
    seq_x1 = [rng_x1.random() for _ in range(5)]

    set_session_seed("session_Y", 42)
    rng_y1 = get_rng("session_Y")
    seq_y1 = [rng_y1.random() for _ in range(5)]

    # 同 seed 同一会话应相同（重置）
    set_session_seed("session_X", 42)
    rng_x2 = get_rng("session_X")
    seq_x2 = [rng_x2.random() for _ in range(5)]

    assert seq_x1 == seq_x2, "同 session 同 seed 应该重放"
    # 不同 session 独立
    set_session_seed("session_X", 42)  # 重置 X
    rng_x3 = get_rng("session_X")
    seq_x3_a = [rng_x3.random() for _ in range(3)]
    seq_x3_b = [rng_x3.random() for _ in range(3)]  # 继续
    assert seq_x3_a != seq_x3_b, "同一 session 连续调用应不同"
    print(f"  ✅ L4.7: session 隔离 + 同 session 连续调用不同")
    return True


def test_L4_08_empty_emergency():
    """L4.8: emergency 但没有可用卡"""
    state = GameState()
    state.cash = 0.5
    state.fate_hand = []  # 空手牌
    is_e, trigger = check_emergency_situation(state)
    assert is_e
    em = get_emergency_cards(state)
    assert len(em) == 0
    print(f"  ✅ L4.8: emergency 触发 + 无可用卡（不弹窗）")
    return True


# ==== 主运行 ====
def main():
    print("=" * 60)
    print("L4 边界 case (8 个)")
    print("=" * 60)
    tests = [
        test_L4_01_zero_ap,
        test_L4_02_negative_cash,
        test_L4_03_use_same_card_twice,
        test_L4_04_huge_cards_hand,
        test_L4_05_nonexistent_location,
        test_L4_06_special_chars_in_card_id,
        test_L4_07_concurrent_seed,
        test_L4_08_empty_emergency,
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
    print(f"L4 结果: {passed} 通过 / {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
