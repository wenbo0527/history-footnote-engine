#!/usr/bin/env python
"""🆕 v2.10.26 — 多声部迁移验证测试

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21026_migrated_nodes.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, 'src')

from history_footnote.story_mode.chapter_loader import get_chapter
from history_footnote.story_mode.narrative_renderer import NarrativeRenderer


def test_ch1_intro_father_ill():
    """ch1 intro_1_father_ill 已迁移 (9 sections)"""
    ch = get_chapter(1)
    n = ch.nodes["intro_1_father_ill"]
    assert len(n.narrative_sections) >= 9, f"sections 不够: {len(n.narrative_sections)}"

    out = NarrativeRenderer().render(n, {})
    # 关键元素都在
    assert "万历十五年三月十二" in out
    assert "【父亲】" in out
    assert "【张氏】（忧）" in out
    assert "「——春日迟迟" in out
    assert "💢 ——吱呀" in out
    print(f"  ch1_intro_father_ill: ✅ ({len(n.narrative_sections)} sections)")


def test_ch1_intro_2_borrow():
    """ch1 intro_2_borrow 已迁移"""
    ch = get_chapter(1)
    n = ch.nodes["intro_2_borrow"]
    assert len(n.narrative_sections) >= 6

    out = NarrativeRenderer().render(n, {})
    assert "【钱老板】" in out
    assert "五两足色纹银" in out
    assert "「——债，就这样背上了。" in out or "债" in out
    assert "算盘响" in out
    print(f"  ch1_intro_2_borrow: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_intro_normal():
    """ch2_intro_normal 已迁移"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_intro_normal"]
    assert len(n.narrative_sections) >= 6

    out = NarrativeRenderer().render(n, {})
    assert "万历十五年六月十八" in out
    assert "【张氏】" in out
    assert "梅雨初歇" in out
    print(f"  ch2_intro_normal: ✅ ({len(n.narrative_sections)} sections)")


def test_ch3_intro_normal():
    """ch3_intro_normal 已迁移"""
    ch = get_chapter(3)
    n = ch.nodes["ch3_intro_normal"]
    assert len(n.narrative_sections) >= 6

    out = NarrativeRenderer().render(n, {})
    assert "万历十五年九月初九" in out
    assert "【张氏】" in out
    assert "织造太监" in out
    assert "💢" in out  # 音效
    print(f"  ch3_intro_normal: ✅ ({len(n.narrative_sections)} sections)")


def test_migration_count():
    """每个章节至少 1 个节点已迁移"""
    for ch_id in (1, 2, 3):
        ch = get_chapter(ch_id)
        migrated = [
            nid for nid, n in ch.nodes.items()
            if n.narrative_sections
        ]
        assert len(migrated) >= 1, f"ch{ch_id} 没迁移任何节点"
        print(f"  ch{ch_id} migrated: {len(migrated)} 节点: {migrated[:3]}")


def test_backward_compatible():
    """未迁移节点 (narrative_sections=[]) 应仍能渲染 (用 narrative 字符串)"""
    ch = get_chapter(1)
    # 找一个未迁移节点
    not_migrated = [
        nid for nid, n in ch.nodes.items()
        if not n.narrative_sections and n.narrative
    ]
    if not not_migrated:
        print(f"  backward_compatible: ⚠️ 没有未迁移节点 (全部已迁移)")
        return

    nid = not_migrated[0]
    n = ch.nodes[nid]
    out = NarrativeRenderer().render(n, {})
    # 仍能渲染 (narrative 字符串兜底)
    assert len(out) > 0
    print(f"  backward_compatible: ✅ ({nid} 仍能渲染)")


def run_all():
    print("=== v2.10.26 多声部迁移验证测试 ===\n")
    print("## Test 1: ch1 intro_1_father_ill")
    test_ch1_intro_father_ill()

    print("\n## Test 2: ch1 intro_2_borrow")
    test_ch1_intro_2_borrow()

    print("\n## Test 3: ch2 intro")
    test_ch2_intro_normal()

    print("\n## Test 4: ch3 intro")
    test_ch3_intro_normal()

    print("\n## Test 5: 迁移计数")
    test_migration_count()

    print("\n## Test 6: 向后兼容 (未迁移节点)")
    test_backward_compatible()

    print("\n" + "=" * 60)
    print("✅ 全部 6 个迁移验证测试通过!")
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