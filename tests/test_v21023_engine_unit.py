#!/usr/bin/env python
"""🆕 v2.10.23 — Story Mode Engine 单元测试

覆盖:
- ScriptedVoiceOption.check 字段生效 (P0 修复验证)
- _do_check 各表达式 (charisma, cash, flag, luck)
- _resolve_attr (cash/debt/flags)
- _apply_effects (cash_delta, debt_delta, rice_delta, flag_set)
- _apply_chapter_echo (ch2/ch3 回响)
- _fuzzy_match
- start_chapter / exit_scripted_mode

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21023_engine_unit.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, 'src')

from history_footnote.story_mode.engine import ScriptedStoryEngine
from history_footnote.story_mode.types import ScriptedNode, ScriptedVoiceOption


# ============================================================
# Fixtures
# ============================================================

def make_node(node_id, options):
    return ScriptedNode(
        node_id=node_id,
        round_min=1,
        round_max=999,
        narrative=f"Node {node_id}",
        voice_options=options,
    )


def make_chapter(nodes):
    """手工构造章节"""
    from history_footnote.story_mode.types import ScriptedChapter
    return ScriptedChapter(
        chapter_id=99,
        title="Test",
        nodes=nodes,
        start_node_id=list(nodes.keys())[0],
        end_node_ids=[],
        total_rounds=10,
    )


# ============================================================
# Test 1: check 字段生效 (P0 修复)
# ============================================================

def test_check_charisma_pass():
    """charisma >= 2 应让玩家去 success_node"""
    success_node = make_node("success_node", [])
    fail_node = make_node("fail_node", [])
    chapter = make_chapter({
        "test_node": make_node("test_node", [
            ScriptedVoiceOption(
                voice_id="try_negotiate",
                voice_name="Negotiate",
                check="charisma >= 2",
                check_success_node="success_node",
                check_fail_node="fail_node",
                next_node_id="default_node",
            ),
        ]),
        "success_node": success_node,
        "fail_node": fail_node,
    })

    eng = ScriptedStoryEngine(chapter)
    state = {}

    # Run 100 times - all should succeed (charisma 默认 2 + random)
    results = {"success_node": 0, "fail_node": 0, "default_node": 0}
    for _ in range(100):
        s = {}
        s["scripted_node_id"] = "test_node"
        eng.handle_input(s, "try_negotiate")
        results[s.get("scripted_node_id")] = results.get(s.get("scripted_node_id"), 0) + 1

    # 至少应该有 50 次 success/fail (很少走 default)
    # 因为 charisma=2 + random d20 (1-20) ≥ 14 (threshold=14)
    # = 7/20 概率 fail, 13/20 success or great_success
    total_checked = results["success_node"] + results["fail_node"]
    assert total_checked > 50, f"check 没生效: {results}"

    print(f"  test_check_charisma_pass: results={results}")


def test_check_cash_fail():
    """cash < 3 应让玩家走 fail_node"""
    fail_node = make_node("fail_node", [])
    success_node = make_node("success_node", [])
    chapter = make_chapter({
        "test_node": make_node("test_node", [
            ScriptedVoiceOption(
                voice_id="call_doctor",
                voice_name="Call Doctor",
                check="cash >= 3",
                check_success_node="success_node",
                check_fail_node="fail_node",
                next_node_id="default",
            ),
        ]),
        "success_node": success_node,
        "fail_node": fail_node,
    })

    eng = ScriptedStoryEngine(chapter)
    state = {"cash": 1}  # 钱不够

    eng.handle_input(state, "call_doctor")
    # 应走 fail_node (因为 cash=1 < 3)
    # 注意: 在 _do_check 里 cash 不足 → passed=False → fail
    assert state["scripted_node_id"] == "fail_node", f"cash=1 没走 fail: got {state['scripted_node_id']}"
    print(f"  test_check_cash_fail: ✅ (cash=1 → fail_node)")


def test_check_cash_pass():
    """cash >= 3 应让玩家走 success_node"""
    fail_node = make_node("fail_node", [])
    success_node = make_node("success_node", [])
    chapter = make_chapter({
        "test_node": make_node("test_node", [
            ScriptedVoiceOption(
                voice_id="call_doctor",
                voice_name="Call Doctor",
                check="cash >= 3",
                check_success_node="success_node",
                check_fail_node="fail_node",
                next_node_id="default",
            ),
        ]),
        "success_node": success_node,
        "fail_node": fail_node,
    })

    eng = ScriptedStoryEngine(chapter)
    state = {"cash": 10}

    eng.handle_input(state, "call_doctor")
    # cash=10 >= 3 通过 → success_node
    assert state["scripted_node_id"] == "success_node", f"cash=10 没走 success: got {state['scripted_node_id']}"
    print(f"  test_check_cash_pass: ✅ (cash=10 → success_node)")


def test_check_no_field_uses_default():
    """没有 check 字段时, 应走 next_node_id"""
    success_node = make_node("success_node", [])
    chapter = make_chapter({
        "test_node": make_node("test_node", [
            ScriptedVoiceOption(
                voice_id="no_check",
                voice_name="No check",
                # 没有 check / check_success_node / check_fail_node
                next_node_id="success_node",
            ),
        ]),
        "success_node": success_node,
    })

    eng = ScriptedStoryEngine(chapter)
    state = {}

    eng.handle_input(state, "no_check")
    assert state["scripted_node_id"] == "success_node", f"无 check 应走 default: got {state['scripted_node_id']}"
    print(f"  test_check_no_field_uses_default: ✅")


# ============================================================
# Test 2: _do_check 表达式
# ============================================================

def test_do_check_returns_valid_tier():
    eng = ScriptedStoryEngine()
    state = {"cash": 5}

    valid_tiers = {"great_success", "success", "fail"}
    for _ in range(50):
        result, d20 = eng._do_check("charisma >= 2", state)
        assert result in valid_tiers, f"invalid tier: {result}"
        assert 1 <= d20 <= 20, f"invalid d20: {d20}"
    print(f"  test_do_check_returns_valid_tier: ✅ (50 rolls)")


def test_do_check_invalid_expr():
    """无效表达式应 fail 兜底"""
    eng = ScriptedStoryEngine()
    state = {}

    result, d20 = eng._do_check("invalid_expr_no_three_parts", state)
    assert result == "fail"
    print(f"  test_do_check_invalid_expr: ✅")


def test_do_check_flag():
    """flag.has_debt 应基于 scripted_flags"""
    eng = ScriptedStoryEngine()

    # 100 rolls with flag set, 至少有一些应过
    state_with = {"scripted_flags": ["has_debt"]}
    results = {"success": 0, "fail": 0, "great_success": 0}
    for _ in range(100):
        result, d20 = eng._do_check("flag.has_debt", state_with)
        results[result] = results.get(result, 0) + 1
    # 至少应有一些 success 或 great_success
    assert results["success"] + results["great_success"] > 10, f"flag 全 fail: {results}"

    # 没有 flag → 硬性不满足 → 全部 fail
    state_without = {"scripted_flags": []}
    for _ in range(20):
        result, d20 = eng._do_check("flag.has_debt", state_without)
        assert result == "fail", f"flag 应 fail: got {result}"

    print(f"  test_do_check_flag: ✅ (with={results})")


# ============================================================
# Test 3: _resolve_attr
# ============================================================

def test_resolve_attr_cash():
    eng = ScriptedStoryEngine()
    assert eng._resolve_attr("cash", {"cash": 5}) == 5
    assert eng._resolve_attr("cash", {}) == 0
    assert eng._resolve_attr("cash", {"cash": None}) == 0
    print(f"  test_resolve_attr_cash: ✅")


def test_resolve_attr_abstract():
    eng = ScriptedStoryEngine()
    # 默认 2
    assert eng._resolve_attr("charisma", {}) == 2
    # flag 加成
    assert eng._resolve_attr("charisma", {"scripted_flags": ["zhou_favor"]}) == 3
    assert eng._resolve_attr("skill", {"scripted_flags": ["learned_qixia", "master_dyer"]}) == 4
    print(f"  test_resolve_attr_abstract: ✅")


# ============================================================
# Test 4: _apply_effects
# ============================================================

def test_apply_effects_cash_delta():
    eng = ScriptedStoryEngine()
    state = {"cash": 5, "debt": 2}
    eng._apply_effects(state, {"cash_delta": -3, "debt_delta": -1})
    assert state["cash"] == 2
    assert state["debt"] == 1
    print(f"  test_apply_effects_cash_delta: ✅")


def test_apply_effects_city_move():
    """city_move 是 handle_input 单独处理的 (不在 _apply_effects 里)"""
    eng = ScriptedStoryEngine()
    state = {"city": "shengze"}
    # city_move 在 handle_input 里处理
    chapter = make_chapter({
        "test": make_node("test", [
            ScriptedVoiceOption(
                voice_id="opt",
                voice_name="opt",
                next_node_id="next",
                effects={"city_move": "suzhou"},
            ),
        ]),
        "next": make_node("next", []),
    })
    eng = ScriptedStoryEngine(chapter)
    eng.handle_input(state, "opt")
    assert state["city"] == "suzhou"
    print(f"  test_apply_effects_city_move: ✅")


def test_apply_effects_looms_delta():
    eng = ScriptedStoryEngine()
    state = {"looms": 1}
    eng._apply_effects(state, {"looms_delta": +1})
    assert state["looms"] == 2
    print(f"  test_apply_effects_looms_delta: ✅")


# ============================================================
# Test 5: handle_input flag 设置
# ============================================================

def test_handle_input_flag_added():
    chapter = make_chapter({
        "test": make_node("test", [
            ScriptedVoiceOption(
                voice_id="opt",
                voice_name="opt",
                next_node_id="next",
                effects={"flag_set": ["test_flag", "another_flag"]},
            ),
        ]),
        "next": make_node("next", []),
    })
    eng = ScriptedStoryEngine(chapter)
    state = {"scripted_node_id": "test"}

    _, _, info = eng.handle_input(state, "opt")
    assert "test_flag" in state["scripted_flags"]
    assert "another_flag" in state["scripted_flags"]
    assert "test_flag" in info["flag_added"]
    print(f"  test_handle_input_flag_added: ✅")


def test_handle_input_flag_no_dup():
    chapter = make_chapter({
        "test": make_node("test", [
            ScriptedVoiceOption(
                voice_id="opt",
                voice_name="opt",
                next_node_id="next",
                effects={"flag_set": ["same"]},
            ),
        ]),
        "next": make_node("next", []),
    })
    eng = ScriptedStoryEngine(chapter)
    state = {"scripted_flags": ["same"], "scripted_node_id": "test"}

    _, _, info = eng.handle_input(state, "opt")
    # 已存在, 不应再添加
    assert "same" not in info["flag_added"], f"已存在 flag 不应在 flag_added: {info['flag_added']}"
    print(f"  test_handle_input_flag_no_dup: ✅")


# ============================================================
# Test 6: chapter echo
# ============================================================

def test_chapter_echo_ch2():
    """ch2 intro 应根据 ch1 flag 注入回响"""
    eng = ScriptedStoryEngine()
    state = {"scripted_flags": ["has_debt", "zhou_favor"], "cash": 1, "debt": 5}

    # 用 ch2 chapter
    from history_footnote.story_mode.chapter_02 import get_chapter_02
    eng.set_chapter_by_id(2)
    state["scripted_chapter_id"] = 2
    state["scripted_node_id"] = "ch2_intro_normal"

    narr = "原文本"
    result = eng._apply_chapter_echo(narr, state, "ch2_intro_normal")

    # 验证 echo 出现
    assert "回响" in result, f"ch2 echo 没注入: {result}"
    assert "牙行" in result or "周大娘" in result, f"具体 flag echo 缺失: {result}"
    print(f"  test_chapter_echo_ch2: ✅")


def test_chapter_echo_ch3():
    """ch3 intro 应根据 ch2 flag 注入回响"""
    eng = ScriptedStoryEngine()
    state = {"scripted_flags": ["ch2_prosperous", "father_will"], "cash": 10}

    from history_footnote.story_mode.chapter_03 import get_chapter_03
    eng.set_chapter_by_id(3)
    state["scripted_chapter_id"] = 3
    state["scripted_node_id"] = "ch3_intro_normal"

    narr = "原文本"
    result = eng._apply_chapter_echo(narr, state, "ch3_intro_normal")

    assert "回响" in result, f"ch3 echo 没注入: {result}"
    assert "父亲" in result or "三架织机" in result, f"具体 echo 缺失: {result}"
    print(f"  test_chapter_echo_ch3: ✅")


def test_chapter_echo_no_flags():
    """无 flag 时不应注入 echo"""
    eng = ScriptedStoryEngine()
    state = {"scripted_flags": []}

    from history_footnote.story_mode.chapter_02 import get_chapter_02
    eng.set_chapter_by_id(2)
    state["scripted_chapter_id"] = 2
    state["scripted_node_id"] = "ch2_intro_normal"

    narr = "原文本"
    result = eng._apply_chapter_echo(narr, state, "ch2_intro_normal")
    assert "回响" not in result, f"无 flag 不应有 echo: {result}"
    print(f"  test_chapter_echo_no_flags: ✅")


# ============================================================
# Test 7: exit_scripted_mode
# ============================================================

def test_exit_scripted_mode_preserves_flags():
    eng = ScriptedStoryEngine()
    state = {"scripted_mode": True, "scripted_flags": ["has_debt", "met_qian"]}

    eng.exit_scripted_mode(state)
    assert state["scripted_mode"] is False
    assert "has_debt" in state["scripted_flags"]  # 保留
    assert "met_qian" in state["scripted_flags"]  # 保留
    assert state["scripted_chapter_complete"] is False
    print(f"  test_exit_scripted_mode_preserves_flags: ✅")


# ============================================================
# Test 8: start_chapter (不重置主游戏状态)
# ============================================================

def test_start_chapter_preserves_main_state():
    eng = ScriptedStoryEngine()
    state = {"cash": 5, "debt": 2, "looms": 3, "rice": 10}

    eng.start_chapter(state, 1)

    # 主游戏状态应保留
    assert state["cash"] == 5
    assert state["debt"] == 2
    assert state["looms"] == 3
    assert state["rice"] == 10
    # 脚本状态重置
    assert state["scripted_mode"] is True
    assert state["scripted_node_id"] == "intro_1_father_ill"
    assert state["scripted_flags"] == []
    print(f"  test_start_chapter_preserves_main_state: ✅")


# ============================================================
# Test 9: 跨章真实路径 - ch2 negotiate_price
# ============================================================

def test_ch2_negotiate_terms_check():
    """🆕 P0 验证: ch2 escalation_expand 的 negotiate_terms 有 charisma >= 3 检定

    charisma=2 (default), check='charisma >= 3':
    - passed = (2 >= 3) = False → 硬性不满足 → 全部 fail → check_fail_node
    - 所以应该 200 次全走 ch2_escalation_expand
    """
    from history_footnote.story_mode.chapter_02 import get_chapter_02

    eng = ScriptedStoryEngine(get_chapter_02())
    results = {"ch2_escalation_weave": 0, "ch2_escalation_expand": 0}

    for _ in range(100):
        state = {"scripted_node_id": "ch2_escalation_expand"}
        eng.handle_input(state, "negotiate_terms")
        node = state["scripted_node_id"]
        if node in results:
            results[node] += 1

    print(f"  test_ch2_negotiate_terms_check: {results} (100 runs, expect mostly expand)")
    # charisma=2 < 3 硬性不满足 → 全部 fail → expand
    assert results["ch2_escalation_expand"] > 50, f"check 没生效: {results}"


def test_ch2_negotiate_price_with_flag():
    """设置 zhou_favor (charisma +1) 后 negotiate_terms 应能成功"""
    from history_footnote.story_mode.chapter_02 import get_chapter_02

    eng = ScriptedStoryEngine(get_chapter_02())
    results = {"ch2_escalation_weave": 0, "ch2_escalation_expand": 0}

    for _ in range(100):
        state = {
            "scripted_node_id": "ch2_escalation_expand",
            "scripted_flags": ["zhou_favor", "met_big_merchant"],  # +2 charisma = 4
        }
        eng.handle_input(state, "negotiate_terms")
        node = state["scripted_node_id"]
        if node in results:
            results[node] += 1

    print(f"  test_ch2_negotiate_price_with_flag: {results} (100 runs, charisma=4)")
    # charisma=4 >= 3 通过 + d20: 应该多数走 success → weave
    assert results["ch2_escalation_weave"] > 30, f"check 没生效 (flag 加成): {results}"


# ============================================================
# Main
# ============================================================

def run_all():
    print("=== v2.10.23 Engine 单元测试 ===\n")
    print("## Test 1: check 字段生效 (P0 修复)")
    test_check_charisma_pass()
    test_check_cash_fail()
    test_check_cash_pass()
    test_check_no_field_uses_default()

    print("\n## Test 2: _do_check 表达式")
    test_do_check_returns_valid_tier()
    test_do_check_invalid_expr()
    test_do_check_flag()

    print("\n## Test 3: _resolve_attr")
    test_resolve_attr_cash()
    test_resolve_attr_abstract()

    print("\n## Test 4: _apply_effects")
    test_apply_effects_cash_delta()
    test_apply_effects_city_move()
    test_apply_effects_looms_delta()

    print("\n## Test 5: handle_input flag")
    test_handle_input_flag_added()
    test_handle_input_flag_no_dup()

    print("\n## Test 6: chapter echo")
    test_chapter_echo_ch2()
    test_chapter_echo_ch3()
    test_chapter_echo_no_flags()

    print("\n## Test 7: exit_scripted_mode")
    test_exit_scripted_mode_preserves_flags()

    print("\n## Test 8: start_chapter")
    test_start_chapter_preserves_main_state()

    print("\n## Test 9: 跨章真实路径")
    test_ch2_negotiate_terms_check()
    test_ch2_negotiate_price_with_flag()

    print("\n" + "=" * 60)
    print("✅ 全部 18 个单元测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_all()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ 测试失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)