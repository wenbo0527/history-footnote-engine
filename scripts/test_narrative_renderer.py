"""🆕 v1.7.0 Narrative Renderer 单元测试"""
import sys
sys.path.insert(0, "src")

from history_footnote.narrative_renderer import (
    narrative_to_blocks,
    render_blocks_to_html,
    ensure_blocks,
    DIALOGUE_PATTERN,
    MONOLOGUE_PATTERN,
    TRANSITION_PATTERN,
)


# === 用户实际报告的样本 ===
USER_SAMPLE = """你站在牙行门口，夕阳斜照在青砖上。

张顺说："三两三，不能再多了。"

你心里想：他出价比周老板低，但张顺从不赊账。要是拿到钱，春税的事就不用愁了。但丁娘子的账还没还...

片刻后，张顺敲了敲柜台。"想好了没？"


你现在面前有几条路：

一、**答应周老板**：三十斤好丝按三两五出手，当场拿十两零五钱银子。

二、**全卖给张顺**：省事，三两三拿下走人。

三、**跟周老板另谈**：他是月港来的大客商。

四、**先问张顺"代织"的事**：周老板还在，张顺也在。"""


def test_all_4_block_types():
    """4 种 block 类型都能识别"""
    blocks = narrative_to_blocks(USER_SAMPLE)
    types = set(b["type"] for b in blocks)
    assert "scene" in types, "缺少 scene block"
    assert "dialogue" in types, "缺少 dialogue block"
    assert "monologue" in types, "缺少 monologue block"
    assert "transition" in types, "缺少 transition block"
    print(f"✅ test_all_4_block_types: 4 种类型全部识别 ({len(blocks)} blocks)")
    for b in blocks:
        print(f"    [{b['type']:12s}] {b.get('speaker', '')}{b['text'][:50]}")


def test_dialogue_pattern():
    """对话正则：识别"张顺说：'内容'"""
    text = '张顺说："三两三，不能再多了。"'
    matches = DIALOGUE_PATTERN.findall(text)
    assert len(matches) == 1
    speaker, content = matches[0]
    assert speaker == "张顺"
    assert "三两三" in content
    print(f"✅ test_dialogue_pattern: speaker={speaker}, content={content[:30]}")


def test_dialogue_multiple_verbs():
    """多种对话动词：说/道/答/问/笑/叹/怒"""
    samples = [
        ('张顺说："3两3"', "张顺", "3两3"),
        ('李四道："不行"', "李四", "不行"),
        ('沈氏答道："知道了"', "沈氏", "知道了"),
        ('王二问："去哪？"', "王二", "去哪？"),
        ('张三笑道："好说"', "张三", "好说"),
        ('李四叹道："命苦啊"', "李四", "命苦啊"),
    ]
    for text, expected_speaker, expected_content in samples:
        matches = DIALOGUE_PATTERN.findall(text)
        assert len(matches) >= 1, f"未识别: {text}"
        speaker, content = matches[0]
        assert speaker == expected_speaker
        assert content == expected_content
    print(f"✅ test_dialogue_multiple_verbs: 6 种动词全部识别")


def test_monologue_pattern():
    """内心独白正则"""
    text = "你心里想：他出价比周老板低，但张顺从不赊账。"
    matches = MONOLOGUE_PATTERN.findall(text)
    assert len(matches) >= 1
    content = matches[0]
    assert "出价" in content
    print(f"✅ test_monologue_pattern: '{content[:30]}'")


def test_transition_keywords():
    """场景切换关键词"""
    samples = [
        "片刻后，张顺说：",
        "次日清晨，你醒来。",
        "过了三日，消息传来。",
        "转眼间，夕阳西下。",
        "晨起后，你出门。",
        "黄昏时分，远山如黛。",
    ]
    for text in samples:
        m = TRANSITION_PATTERN.match(text)
        assert m is not None, f"未识别 transition: {text}"
    print(f"✅ test_transition_keywords: 6 个场景切换词")


def test_render_html():
    """HTML 渲染"""
    blocks = narrative_to_blocks(USER_SAMPLE)
    html = render_blocks_to_html(blocks)
    assert "block-scene" in html
    assert "block-dialogue" in html
    assert "block-monologue" in html
    assert "block-transition" in html
    # XSS 防护：标签应被 escape
    assert "&lt;script&gt;" not in html  # 没有原 <script>
    # speaker 应该在 dialogue block 里
    assert ">张顺<" in html
    print(f"✅ test_render_html: {len(html)} 字符，4 种 CSS class")


def test_ensure_blocks_priority():
    """structured_blocks 优先"""
    structured = [{"type": "scene", "text": "structured"}]
    blocks = ensure_blocks(structured, "narrative text here")
    assert len(blocks) == 1
    assert blocks[0]["text"] == "structured"
    # 没有 structured 时，回退到 narrative 解析
    blocks2 = ensure_blocks(None, USER_SAMPLE)
    assert len(blocks2) > 1
    blocks3 = ensure_blocks([], "")
    assert blocks3 == []
    print(f"✅ test_ensure_blocks_priority: structured > narrative > []")


def test_xss_in_html():
    """XSS 防护"""
    text = "你看到 <script>alert('xss')</script> 在闪"
    blocks = narrative_to_blocks(text)
    html = render_blocks_to_html(blocks)
    # < 和 > 应被 escape
    assert "<script>" not in html
    assert "&lt;script&gt;" in html or "&lt;script" in html
    print(f"✅ test_xss_in_html: 标签已 escape")


def test_empty_input():
    """空输入"""
    assert narrative_to_blocks("") == []
    assert narrative_to_blocks(None) == []
    assert narrative_to_blocks("   ") == []
    print("✅ test_empty_input: 空输入返回 []")


def test_short_text():
    """短文本（无对话/独白）"""
    text = "天很蓝，云很白。"
    blocks = narrative_to_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "scene"
    print(f"✅ test_short_text: 1 个 scene block")


def test_real_user_scenario():
    """真实用户场景：周老板 / 张顺选项"""
    text = """你面前有 4 条路：

一、**答应周老板**：三两五出手。
二、**全卖给张顺**：三两三走人。
三、**跟周老板另谈**：搭个桥。
四、**先问张顺代织的事**：三个人当面谈。"""
    blocks = narrative_to_blocks(text)
    # 选项不在 blocks 里（前端通过 extract_inline_options 提取）
    # 但前面的叙述应该被解析
    assert any(b["type"] == "scene" for b in blocks)
    # 测试和 v1.6.9 兼容
    from history_footnote.narrative_sanitizer import extract_inline_options
    options = extract_inline_options(text)
    assert len(options) == 4
    print(f"✅ test_real_user_scenario: {len(blocks)} blocks + {len(options)} options")


if __name__ == "__main__":
    print("=" * 50)
    print("Narrative Renderer 测试（v1.7.0）")
    print("=" * 50)
    test_all_4_block_types()
    test_dialogue_pattern()
    test_dialogue_multiple_verbs()
    test_monologue_pattern()
    test_transition_keywords()
    test_render_html()
    test_ensure_blocks_priority()
    test_xss_in_html()
    test_empty_input()
    test_short_text()
    test_real_user_scenario()
    print("\n✅ 所有 v1.7.0 Narrative Renderer 测试通过")