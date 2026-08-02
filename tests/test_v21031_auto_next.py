#!/usr/bin/env python
"""🆕 v2.10.31 — AutoNextNode 单元测试

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21031_auto_next.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, 'src')

from history_footnote.story_mode.chapter_loader import get_chapter
from history_footnote.story_mode.engine import ScriptedStoryEngine
from history_footnote.story_mode.types import ScriptedNode, ScriptedVoiceOption


def make_autonext_node(node_id, target_id, with_options=False):
    """创建一个 auto_next_node 节点"""
    opts = []
    if with_options:
        opts = [
            ScriptedVoiceOption(
                voice_id="opt",
                voice_name="选项",
                next_node_id="anywhere",
            )
        ]
    return ScriptedNode(
        node_id=node_id,
        round_min=1,
        round_max=999,
        narrative_sections=[],
        voice_options=opts,
        auto_next_node_id=target_id,
    )


# ============================================================
# Test 1: 单跳 auto-next
# ============================================================

def test_single_jump():
    """单个 auto_next_node_id 跳转"""
    ch = get_chapter(1)
    # 在 chapter 上注入临时节点 (覆盖 + restore)
    ch.nodes["temp_src"] = make_autonext_node("temp_src", "temp_dst")
    ch.nodes["temp_dst"] = make_autonext_node("temp_dst", None, with_options=True)

    try:
        eng = ScriptedStoryEngine(ch)
        state = {"scripted_node_id": "temp_src"}
        narr, opts = eng._get_current_view(state)

        # 应该已跳到 temp_dst
        assert state["scripted_node_id"] == "temp_dst"
        assert len(opts) == 1
        assert opts[0].voice_id == "opt"
        print(f"  test_single_jump: ✅ (state.scripted_node_id = temp_dst)")
    finally:
        del ch.nodes["temp_src"]
        del ch.nodes["temp_dst"]


# ============================================================
# Test 2: 多跳 chain
# ============================================================

def test_chain_jump():
    """链式跳转: a → b → c"""
    ch = get_chapter(1)
    ch.nodes["temp_a"] = make_autonext_node("temp_a", "temp_b")
    ch.nodes["temp_b"] = make_autonext_node("temp_b", "temp_c")
    ch.nodes["temp_c"] = make_autonext_node("temp_c", None, with_options=True)

    try:
        eng = ScriptedStoryEngine(ch)
        state = {"scripted_node_id": "temp_a"}
        narr, opts = eng._get_current_view(state)

        assert state["scripted_node_id"] == "temp_c"
        assert len(opts) == 1
        print(f"  test_chain_jump: ✅ (a→b→c)")
    finally:
        for k in ("temp_a", "temp_b", "temp_c"):
            del ch.nodes[k]


# ============================================================
# Test 3: 循环检测
# ============================================================

def test_cycle_detection():
    """循环: a → b → a → ... 应被检测"""
    ch = get_chapter(1)
    ch.nodes["temp_a"] = make_autonext_node("temp_a", "temp_b")
    ch.nodes["temp_b"] = make_autonext_node("temp_b", "temp_a")

    try:
        eng = ScriptedStoryEngine(ch)
        state = {"scripted_node_id": "temp_a"}
        narr, opts = eng._get_current_view(state)

        # 不应无限循环 - 应停在某个位置 (或警告)
        # 防循环机制: 最多 50 次
        assert state["scripted_node_id"] in ("temp_a", "temp_b")
        print(f"  test_cycle_detection: ✅ (停止于 {state['scripted_node_id']})")
    finally:
        for k in ("temp_a", "temp_b"):
            del ch.nodes[k]


# ============================================================
# Test 4: 有 voice_options 时不触发
# ============================================================

def test_options_no_jump():
    """节点有 voice_options 时不应触发 auto-next"""
    ch = get_chapter(1)
    ch.nodes["temp_with_opt"] = make_autonext_node("temp_with_opt", "temp_dst", with_options=True)
    ch.nodes["temp_dst"] = make_autonext_node("temp_dst", None, with_options=True)

    try:
        eng = ScriptedStoryEngine(ch)
        state = {"scripted_node_id": "temp_with_opt"}
        narr, opts = eng._get_current_view(state)

        # 因有 options, 不应跳转
        assert state["scripted_node_id"] == "temp_with_opt"
        assert len(opts) == 1
        assert opts[0].voice_id == "opt"
        print(f"  test_options_no_jump: ✅ (停在 temp_with_opt)")
    finally:
        for k in ("temp_with_opt", "temp_dst"):
            del ch.nodes[k]


# ============================================================
# Test 5: auto_next_node_id 指向不存在的节点
# ============================================================

def test_invalid_target():
    """auto_next_node_id 指向不存在的节点 → 错误信息"""
    ch = get_chapter(1)
    ch.nodes["temp_bad"] = make_autonext_node("temp_bad", "nonexistent_node")

    try:
        eng = ScriptedStoryEngine(ch)
        state = {"scripted_node_id": "temp_bad"}
        narr, opts = eng._get_current_view(state)

        assert "auto_next 目标节点不存在" in narr
        assert len(opts) == 0
        print(f"  test_invalid_target: ✅ ({narr[:30]}...)")
    finally:
        del ch.nodes["temp_bad"]


# ============================================================
# Test 6: ch1_demo_autonext 集成测试
# ============================================================

def test_ch1_demo():
    """ch1_demo_autonext 节点集成"""
    ch = get_chapter(1)
    assert "ch1_demo_autonext" in ch.nodes
    assert "ch1_demo_autonext_target" in ch.nodes

    eng = ScriptedStoryEngine(ch)
    state = {"scripted_node_id": "ch1_demo_autonext"}
    narr, opts = eng._get_current_view(state)

    # 自动跳到 target
    assert state["scripted_node_id"] == "ch1_demo_autonext_target"
    assert "AutoNextNode 示例 2/2" in narr
    assert len(opts) == 1
    print(f"  test_ch1_demo: ✅")


def run_all():
    print("=== v2.10.31 AutoNextNode 单元测试 ===\n")
    print("## Test 1: 单跳")
    test_single_jump()

    print("\n## Test 2: 链式跳转")
    test_chain_jump()

    print("\n## Test 3: 循环检测")
    test_cycle_detection()

    print("\n## Test 4: 有 options 不触发")
    test_options_no_jump()

    print("\n## Test 5: 无效目标")
    test_invalid_target()

    print("\n## Test 6: 集成")
    test_ch1_demo()

    print("\n" + "=" * 60)
    print("✅ 全部 6 个 AutoNextNode 单元测试通过!")
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