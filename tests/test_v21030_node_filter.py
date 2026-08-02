#!/usr/bin/env python
"""🆕 v2.10.30 — NodeFilter 单元测试

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21030_node_filter.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, 'src')

from history_footnote.story_mode.node_filter import NodeFilter
from history_footnote.story_mode.types import ScriptedNode


def make_node(
    node_id="test",
    required_city=None,
    required_flags=None,
    forbidden_flags=None,
    round_min=1,
    round_max=999,
):
    return ScriptedNode(
        node_id=node_id,
        round_min=round_min,
        round_max=round_max,
        required_city=required_city,
        required_flags=required_flags or [],
        forbidden_flags=forbidden_flags or [],
        narrative_sections=[],
        voice_options=[],
    )


# ============================================================
# Test 1: city 过滤
# ============================================================

def test_required_city_pass():
    """city 匹配 → 可访问"""
    node = make_node(required_city="suzhou")
    state = {"city": "suzhou"}
    assert NodeFilter.is_accessible(node, state)
    print(f"  test_required_city_pass: ✅")


def test_required_city_fail():
    """city 不匹配 → 不可访问"""
    node = make_node(required_city="suzhou")
    state = {"city": "shengze"}
    assert not NodeFilter.is_accessible(node, state)
    reasons = NodeFilter.get_unmet_requirements(node, state)
    assert "city:mismatch" in reasons[0]
    print(f"  test_required_city_fail: ✅ ({reasons})")


def test_required_city_default():
    """缺省 city=shengze"""
    node = make_node(required_city="shengze")
    state = {}  # 没设置 city
    assert NodeFilter.is_accessible(node, state)
    print(f"  test_required_city_default: ✅")


# ============================================================
# Test 2: required_flags 过滤
# ============================================================

def test_required_flags_pass():
    """所有 required_flags 都有 → 可访问"""
    node = make_node(required_flags=["has_debt", "zhou_favor"])
    state = {"scripted_flags": ["has_debt", "zhou_favor", "extra"]}
    assert NodeFilter.is_accessible(node, state)
    print(f"  test_required_flags_pass: ✅")


def test_required_flags_partial():
    """只满足部分 → 不可访问"""
    node = make_node(required_flags=["has_debt", "zhou_favor"])
    state = {"scripted_flags": ["has_debt"]}  # 缺 zhou_favor
    assert not NodeFilter.is_accessible(node, state)
    reasons = NodeFilter.get_unmet_requirements(node, state)
    assert any("zhou_favor" in r for r in reasons)
    print(f"  test_required_flags_partial: ✅ ({reasons})")


# ============================================================
# Test 3: forbidden_flags 过滤
# ============================================================

def test_forbidden_flags_clean():
    """没有 forbidden flag → 可访问"""
    node = make_node(forbidden_flags=["sold_loom"])
    state = {"scripted_flags": ["has_debt"]}
    assert NodeFilter.is_accessible(node, state)
    print(f"  test_forbidden_flags_clean: ✅")


def test_forbidden_flags_hit():
    """有 forbidden flag → 不可访问"""
    node = make_node(forbidden_flags=["sold_loom"])
    state = {"scripted_flags": ["sold_loom", "has_debt"]}
    assert not NodeFilter.is_accessible(node, state)
    reasons = NodeFilter.get_unmet_requirements(node, state)
    assert any("sold_loom" in r and "forbidden" in r for r in reasons)
    print(f"  test_forbidden_flags_hit: ✅ ({reasons})")


# ============================================================
# Test 4: round 范围
# ============================================================

def test_round_in_range():
    """round 在范围内"""
    node = make_node(round_min=3, round_max=8)
    assert NodeFilter.is_accessible(node, {"round": 5})
    print(f"  test_round_in_range: ✅")


def test_round_too_low():
    """round < round_min"""
    node = make_node(round_min=3, round_max=8)
    assert not NodeFilter.is_accessible(node, {"round": 1})
    reasons = NodeFilter.get_unmet_requirements(node, {"round": 1})
    assert any("round:too_low" in r for r in reasons)
    print(f"  test_round_too_low: ✅ ({reasons})")


def test_round_too_high():
    """round > round_max"""
    node = make_node(round_min=3, round_max=8)
    assert not NodeFilter.is_accessible(node, {"round": 10})
    print(f"  test_round_too_high: ✅")


# ============================================================
# Test 5: 多条件组合
# ============================================================

def test_all_pass():
    """所有条件都满足"""
    node = make_node(
        required_city="suzhou",
        required_flags=["a", "b"],
        forbidden_flags=["c"],
        round_min=2,
        round_max=10,
    )
    state = {
        "city": "suzhou",
        "scripted_flags": ["a", "b", "d"],
        "round": 5,
    }
    assert NodeFilter.is_accessible(node, state)
    print(f"  test_all_pass: ✅")


def test_all_fail():
    """所有条件都不满足"""
    node = make_node(
        required_city="suzhou",
        required_flags=["a", "b"],
        forbidden_flags=["c"],
        round_min=5,
        round_max=10,
    )
    state = {
        "city": "shengze",  # 不匹配
        "scripted_flags": ["a", "c"],  # 缺 b + 有 forbidden c
        "round": 1,  # 太低
    }
    assert not NodeFilter.is_accessible(node, state)
    reasons = NodeFilter.get_unmet_requirements(node, state)
    assert len(reasons) >= 4  # 4 个 unmet
    print(f"  test_all_fail: ✅ ({len(reasons)} reasons: {reasons[:2]}...)")


# ============================================================
# Test 6: 集成 — engine 集成
# ============================================================

def test_engine_integration():
    """ch1_demo_filter 节点测试:
    - 不满足条件 → 警告 narrative + 空 options
    - 满足条件 → 正常 narrative
    """
    from history_footnote.story_mode.chapter_loader import get_chapter
    from history_footnote.story_mode.narrative_renderer import NarrativeRenderer
    from history_footnote.story_mode.engine import ScriptedStoryEngine

    ch = get_chapter(1)
    demo = ch.nodes["ch1_demo_filter"]
    assert demo.required_city == "suzhou"
    assert demo.required_flags == ["has_debt", "zhou_favor"]
    assert demo.forbidden_flags == ["sold_loom"]

    eng = ScriptedStoryEngine(ch)

    # Case 1: 不满足 → 警告
    state = {"scripted_node_id": "ch1_demo_filter"}
    narr, opts = eng._get_current_view(state)
    assert "暂不可访问" in narr
    assert len(opts) == 0
    print(f"  test_engine_integration (blocked): ✅")

    # Case 2: 满足 → 正常
    state = {
        "scripted_node_id": "ch1_demo_filter",
        "city": "suzhou",
        "scripted_flags": ["has_debt", "zhou_favor"],
        "round": 1,
    }
    narr, opts = eng._get_current_view(state)
    assert "NodeFilter 示例" in narr
    assert len(opts) == 1
    assert opts[0].voice_id == "back_to_shengze"
    print(f"  test_engine_integration (pass): ✅")


def run_all():
    print("=== v2.10.30 NodeFilter 单元测试 ===\n")
    print("## Test 1: city 过滤")
    test_required_city_pass()
    test_required_city_fail()
    test_required_city_default()

    print("\n## Test 2: required_flags")
    test_required_flags_pass()
    test_required_flags_partial()

    print("\n## Test 3: forbidden_flags")
    test_forbidden_flags_clean()
    test_forbidden_flags_hit()

    print("\n## Test 4: round 范围")
    test_round_in_range()
    test_round_too_low()
    test_round_too_high()

    print("\n## Test 5: 多条件组合")
    test_all_pass()
    test_all_fail()

    print("\n## Test 6: engine 集成")
    test_engine_integration()

    print("\n" + "=" * 60)
    print("✅ 全部 12 个 NodeFilter 单元测试通过!")
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