#!/usr/bin/env python
"""🆕 v2.10.25 — NarrativeRenderer 单元测试

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21025_narrative_renderer.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, 'src')

from history_footnote.story_mode.narrative_renderer import NarrativeRenderer
from history_footnote.story_mode.rich import NarrativeSection
from history_footnote.story_mode.types import ScriptedNode


def make_node(node_id, sections, narrative=""):
    return ScriptedNode(
        node_id=node_id,
        round_min=1,
        round_max=999,
        narrative=narrative,
        narrative_sections=sections,
        voice_options=[],
    )


# ============================================================
# Test 1: 单一声部 (旁白)
# ============================================================

def test_narrator_only():
    """只有旁白 (narrator='旁白'), 应该直接输出文本"""
    r = NarrativeRenderer()
    node = make_node("t1", [
        NarrativeSection(narrator="旁白", text="第一句。"),
        NarrativeSection(narrator="旁白", text="第二句。"),
    ])
    out = r.render(node, {})
    assert "第一句" in out
    assert "第二句" in out
    assert "【旁白】" not in out, f"旁白不应加【】前缀: {out}"
    print(f"  test_narrator_only: ✅")


# ============================================================
# Test 2: NPC 对话
# ============================================================

def test_npc_dialogue():
    """NPC 对话 (narrator='张氏'), 应加【张氏】前缀"""
    r = NarrativeRenderer()
    node = make_node("t2", [
        NarrativeSection(narrator="张氏", text="相公，外面有客。"),
    ])
    out = r.render(node, {})
    assert "【张氏】" in out, f"应有【张氏】前缀: {out}"
    assert "相公，外面有客。" in out
    print(f"  test_npc_dialogue: ✅")


# ============================================================
# Test 3: 内心独白 (italic)
# ============================================================

def test_inner_voice_italic():
    """内心独白 (italic=True 或 narrator='内心'), 应加「...」"""
    r = NarrativeRenderer()
    node1 = make_node("t3a", [
        NarrativeSection(narrator="内心", text="我该怎么办？"),
    ])
    out1 = r.render(node1, {})
    assert "「我该怎么办？」" in out1, f"应加「」: {out1}"

    node2 = make_node("t3b", [
        NarrativeSection(narrator="旁白", text="（心想）", italic=True),
    ])
    out2 = r.render(node2, {})
    assert "「（心想）」" in out2, f"italic 也应加「」: {out2}"

    print(f"  test_inner_voice_italic: ✅")


# ============================================================
# Test 4: Emotion (表情)
# ============================================================

def test_emotion_suffix():
    """emotion 应作为后缀 (e.g. 【张氏】（忧）:)"""
    r = NarrativeRenderer()
    node = make_node("t4", [
        NarrativeSection(narrator="张氏", text="...", emotion="忧"),
    ])
    out = r.render(node, {})
    assert "【张氏】（忧）" in out, f"emotion 后缀: {out}"
    print(f"  test_emotion_suffix: ✅")


# ============================================================
# Test 5: Sound (音效)
# ============================================================

def test_sound():
    """sound 单独一行 + 💢 前缀"""
    r = NarrativeRenderer()
    node = make_node("t5", [
        NarrativeSection(narrator="", text="", sound="咚咚咚——"),
    ])
    out = r.render(node, {})
    assert "💢 咚咚咚——" in out, f"音效格式: {out}"
    print(f"  test_sound: ✅")


# ============================================================
# Test 6: Action (动作)
# ============================================================

def test_action():
    """action 应加 *...* 斜体前缀"""
    r = NarrativeRenderer()
    node = make_node("t6", [
        NarrativeSection(narrator="", text="", action="攥紧借据"),
    ])
    out = r.render(node, {})
    assert "*攥紧借据*" in out, f"动作格式: {out}"
    print(f"  test_action: ✅")


# ============================================================
# Test 7: 完整示例 (父亲 + 张氏 + 内心)
# ============================================================

def test_full_scene():
    """完整示例: 旁白 + 音效 + NPC + 内心"""
    r = NarrativeRenderer()
    node = make_node("t7", [
        NarrativeSection(narrator="旁白", text="万历十五年三月十二。"),
        NarrativeSection(narrator="", text="", sound="咳咳咳——"),
        NarrativeSection(
            narrator="父亲",
            text="泽儿...",
            emotion="气弱",
        ),
        NarrativeSection(
            narrator="张氏",
            text="相公...",
            emotion="忧",
            action="眼眶红了",
        ),
        NarrativeSection(
            narrator="内心",
            text="我该怎么办？",
            italic=True,
        ),
    ])
    out = r.render(node, {})
    # 验证所有元素都在
    assert "万历十五年三月十二" in out
    assert "💢 咳咳咳——" in out
    assert "【父亲】（气弱）" in out
    assert "*眼眶红了*" in out
    assert "【张氏】（忧）" in out
    assert "「我该怎么办？」" in out
    print(f"  test_full_scene: ✅")
    print(f"    渲染输出:\n{out}")


# ============================================================
# Test 8: 兜底 narrative 字符串
# ============================================================

def test_narrative_fallback():
    """无 narrative_sections 时, 应兜底使用 narrative 字符串"""
    r = NarrativeRenderer()
    node = ScriptedNode(
        node_id="t8",
        round_min=1,
        round_max=999,
        narrative="这是兜底 narrative。",
        narrative_sections=[],
        voice_options=[],
    )
    out = r.render(node, {})
    assert "这是兜底 narrative。" in out, f"兜底失败: {out}"
    print(f"  test_narrative_fallback: ✅")


# ============================================================
# Test 9: narrative_sections 优先于 narrative
# ============================================================

def test_sections_priority():
    """narrative_sections 应优先于 narrative 字符串"""
    r = NarrativeRenderer()
    node = ScriptedNode(
        node_id="t9",
        round_min=1,
        round_max=999,
        narrative="这是兜底 narrative (不应该出现)。",
        narrative_sections=[
            NarrativeSection(narrator="旁白", text="优先 sections。"),
        ],
        voice_options=[],
    )
    out = r.render(node, {})
    assert "优先 sections" in out
    assert "不应该出现" not in out, f"sections 应覆盖 narrative: {out}"
    print(f"  test_sections_priority: ✅")


# ============================================================
# Test 10: 模板变量替换 {var}
# ============================================================

def test_template_var():
    """TemplateEngine 应替换 {var}"""
    r = NarrativeRenderer()
    node = make_node("t10", [
        NarrativeSection(
            narrator="张氏",
            text="相公，还剩 {cash} 两银子。",
        ),
    ])
    state = {"cash": 5}
    out = r.render(node, state)
    assert "还剩 5 两银子" in out, f"模板替换失败: {out}"
    print(f"  test_template_var: ✅")


# ============================================================
# Test 11: 条件块 {?flag}
# ============================================================

def test_conditional():
    """TemplateEngine 应处理 {?flag}...{/flag} 条件块"""
    r = NarrativeRenderer()
    node = make_node("t11", [
        NarrativeSection(
            narrator="旁白",
            text="{?has_debt}牙行的人追来了。{/has_debt}",
        ),
    ])
    # 有 flag
    out_with = r.render(node, {"scripted_flags": ["has_debt"]})
    assert "牙行的人追来了" in out_with
    # 无 flag
    out_without = r.render(node, {"scripted_flags": []})
    assert "牙行的人追来了" not in out_without
    print(f"  test_conditional: ✅")


# ============================================================
# Test 12: 环境标签注入
# ============================================================

def test_env_injection():
    """环境标签 + 环境短语应作为前缀"""
    r = NarrativeRenderer()
    node = make_node("t12", [
        NarrativeSection(narrator="旁白", text="文本"),
    ])
    out = r.render(
        node,
        {},
        env_label="【春季·晴·盛泽镇·辰时】",
        env_phrase="春阳和煦。",
    )
    assert "【春季·晴·盛泽镇·辰时】" in out
    assert "春阳和煦" in out
    assert "文本" in out
    print(f"  test_env_injection: ✅")


# ============================================================
# Test 13: ch1 demo 节点集成
# ============================================================

def test_ch1_demo_node():
    """ch1_demo_multivocal 节点应能正常渲染"""
    from history_footnote.story_mode.chapter_loader import get_chapter
    ch = get_chapter(1)
    demo = ch.nodes.get("ch1_demo_multivocal")
    assert demo is not None
    assert len(demo.narrative_sections) >= 5

    r = NarrativeRenderer()
    out = r.render(demo, {})
    # 验证关键元素
    assert "万历十五年三月十二" in out
    assert "💢 咳咳咳——" in out
    assert "【父亲】" in out
    assert "【张氏】" in out
    assert "「" in out  # 内心独白
    print(f"  test_ch1_demo_node: ✅")


# ============================================================
# Main
# ============================================================

def run_all():
    print("=== v2.10.25 NarrativeRenderer 单元测试 ===\n")
    print("## Test 1: 单一声部")
    test_narrator_only()

    print("\n## Test 2: NPC 对话")
    test_npc_dialogue()

    print("\n## Test 3: 内心独白")
    test_inner_voice_italic()

    print("\n## Test 4: Emotion")
    test_emotion_suffix()

    print("\n## Test 5: Sound")
    test_sound()

    print("\n## Test 6: Action")
    test_action()

    print("\n## Test 7: 完整示例")
    test_full_scene()

    print("\n## Test 8: narrative 兜底")
    test_narrative_fallback()

    print("\n## Test 9: sections 优先")
    test_sections_priority()

    print("\n## Test 10: 模板变量")
    test_template_var()

    print("\n## Test 11: 条件块")
    test_conditional()

    print("\n## Test 12: 环境注入")
    test_env_injection()

    print("\n## Test 13: ch1 demo 节点")
    test_ch1_demo_node()

    print("\n" + "=" * 60)
    print("✅ 全部 13 个单元测试通过!")
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