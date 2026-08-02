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


def test_ch1_climax_silk():
    """🆕 v2.10.27: ch1 climax_silk 已迁移"""
    ch = get_chapter(1)
    n = ch.nodes["climax_silk"]
    assert len(n.narrative_sections) >= 8

    out = NarrativeRenderer().render(n, {})
    assert "一连十日" in out
    assert "【钱老板】" in out
    assert "五两银子" in out
    assert "💢 ——叮" in out  # 银子音效
    assert "「" in out  # 内心独白
    print(f"  ch1_climax_silk: ✅ ({len(n.narrative_sections)} sections)")


def test_ch1_climax_father_dies():
    """🆕 v2.10.27: ch1 climax_father_dies (关键悲剧)"""
    ch = get_chapter(1)
    n = ch.nodes["climax_father_dies"]
    assert len(n.narrative_sections) >= 5

    out = NarrativeRenderer().render(n, {})
    assert "张氏" in out
    assert "【张氏】（惊恐）" in out
    assert "【父亲】" in out
    assert "「父亲想说什么" in out
    assert "💢 ——沙沙沙" in out  # 雨声
    print(f"  ch1_climax_father_dies: ✅ ({len(n.narrative_sections)} sections)")


def test_ch1_resolution_prosperous():
    """🆕 v2.10.27: ch1 resolution_prosperous (完美结局)"""
    ch = get_chapter(1)
    n = ch.nodes["resolution_prosperous"]
    assert len(n.narrative_sections) >= 6

    out = NarrativeRenderer().render(n, {})
    assert "十二两银子" in out
    assert "【牙行掌柜】" in out
    assert "【张氏】" in out
    assert "【第一章完" in out
    print(f"  ch1_resolution_prosperous: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_climax_dye():
    """🆕 v2.10.27: ch2 ch2_climax_dye (关键转折)"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_climax_dye"]
    assert len(n.narrative_sections) >= 5

    out = NarrativeRenderer().render(n, {})
    assert "赵师傅" in out
    assert "张氏" in out
    assert "染色" in out
    print(f"  ch2_climax_dye: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_climax_father_secret():
    """🆕 v2.10.27: ch2 father_secret (关键 - 复仇火种)"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_climax_father_secret"]
    assert len(n.narrative_sections) >= 7

    out = NarrativeRenderer().render(n, {})
    assert "织造太监李保" in out
    assert "父亲沈茂" in out
    assert "证据确凿" in out
    assert "「——万历十五年，李保仍在任" in out
    print(f"  ch2_climax_father_secret: ✅ ({len(n.narrative_sections)} sections)")


def test_ch3_climax_zhouqi():
    """🆕 v2.10.27: ch3 周七上门"""
    ch = get_chapter(3)
    n = ch.nodes["ch3_climax_zhouqi"]
    assert len(n.narrative_sections) >= 4

    out = NarrativeRenderer().render(n, {})
    assert "周七" in out
    assert "【周七】" in out
    assert "李公公" in out
    print(f"  ch3_climax_zhouqi: ✅ ({len(n.narrative_sections)} sections)")


def test_ch3_climax_resistance():
    """🆕 v2.10.27: ch3 抗税起义"""
    ch = get_chapter(3)
    n = ch.nodes["ch3_climax_resistance"]
    assert len(n.narrative_sections) >= 6

    out = NarrativeRenderer().render(n, {})
    assert "号角" in out
    assert "刘二" in out
    assert "抗税" in out
    assert "💢 ——呜" in out  # 号角声
    print(f"  ch3_climax_resistance: ✅ ({len(n.narrative_sections)} sections)")


# 🆕 v2.10.28 新增测试

def test_ch1_climax_silk_better():
    """v2.10.28: ch1 climax_silk_better (舌战掌柜, 绮霞罗成功)"""
    ch = get_chapter(1)
    n = ch.nodes["climax_silk_better"]
    assert len(n.narrative_sections) >= 5

    out = NarrativeRenderer().render(n, {})
    assert "舌战" in out
    assert "【你】" in out
    assert "【掌柜】" in out
    assert "💢 ——啪" in out  # 拍桌
    assert "💢 ——踢踏踢踏" in out  # 马蹄
    print(f"  ch1_climax_silk_better: ✅ ({len(n.narrative_sections)} sections)")


def test_ch1_escalation_zhou():
    """v2.10.28: ch1 escalation_zhou (周大娘教绮霞罗)"""
    ch = get_chapter(1)
    n = ch.nodes["escalation_zhou"]
    assert len(n.narrative_sections) >= 5

    out = NarrativeRenderer().render(n, {})
    assert "周大娘" in out
    assert "【周大娘】" in out
    assert "绮霞罗" in out
    assert "「" in out  # 内心独白
    print(f"  ch1_escalation_zhou: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_climax_dye_success():
    """v2.10.28: ch2 染色成功 (学会玄黄染色法)"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_climax_dye_success"]
    assert len(n.narrative_sections) >= 5

    out = NarrativeRenderer().render(n, {})
    assert "赵师傅" in out
    assert "玄黄染色法" in out
    assert "💢 ——咕嘟咕嘟" in out  # 染料翻滚
    print(f"  ch2_climax_dye_success: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_climax_dye_fail():
    """v2.10.28: ch2 染色失败"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_climax_dye_fail"]
    assert len(n.narrative_sections) >= 3

    out = NarrativeRenderer().render(n, {})
    assert "赵师傅" in out
    assert "【赵师傅】（愧疚）" in out
    print(f"  ch2_climax_dye_fail: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_climax_quality():
    """v2.10.28: ch2 染色大成功 (订单大成功)"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_climax_quality"]
    assert len(n.narrative_sections) >= 4

    out = NarrativeRenderer().render(n, {})
    assert "孙掌柜" in out
    assert "绛紫、月白、鸦青、藕荷" in out
    assert "【孙掌柜】（惊叹）" in out
    print(f"  ch2_climax_quality: ✅ ({len(n.narrative_sections)} sections)")


def test_ch2_climax_quality_partial():
    """v2.10.28: ch2 部分完成 (八折)"""
    ch = get_chapter(2)
    n = ch.nodes["ch2_climax_quality_partial"]
    assert len(n.narrative_sections) >= 3

    out = NarrativeRenderer().render(n, {})
    assert "孙掌柜" in out
    assert "八折" in out
    print(f"  ch2_climax_quality_partial: ✅ ({len(n.narrative_sections)} sections)")


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
    print("=== v2.10.28 多声部迁移验证测试 ===\n")
    print("## ch1 节点")
    test_ch1_intro_father_ill()
    test_ch1_intro_2_borrow()
    test_ch1_climax_silk()
    test_ch1_climax_silk_better()
    test_ch1_climax_father_dies()
    test_ch1_resolution_prosperous()
    test_ch1_escalation_zhou()

    print("\n## ch2 节点")
    test_ch2_intro_normal()
    test_ch2_climax_dye()
    test_ch2_climax_dye_success()
    test_ch2_climax_dye_fail()
    test_ch2_climax_quality()
    test_ch2_climax_quality_partial()
    test_ch2_climax_father_secret()

    print("\n## ch3 节点")
    test_ch3_intro_normal()
    test_ch3_climax_zhouqi()
    test_ch3_climax_resistance()

    print("\n## 整体")
    test_migration_count()
    test_backward_compatible()

    print("\n" + "=" * 60)
    print("✅ 全部 18 个迁移验证测试通过!")
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