"""🆕 v1.6.9 内嵌选项提取测试

用户报告：LLM 把选项写进 narrative（"一、**答应周老板**..."），
但前端没识别为按钮，必须自己输入。

修复：在 narrative_sanitizer 加 extract_inline_options / merge_voice_options
+ game_loop 自动回填 + 前端双保险
"""
import sys
sys.path.insert(0, "src")

from history_footnote.narrative_sanitizer import (
    extract_inline_options,
    merge_voice_options,
)


# === 测试数据：用户实际报告的输出 ===
REAL_USER_REPORT = """你现在面前有几条路：

一、**答应周老板**：三十斤好丝按三两五出手，当场拿十两零五钱银子。但剩下十来斤差货，张顺会不会趁势压价？他说不准。而且你今天还没问张顺"代织"的事——周老板走了，这事还提不提？

二、**全卖给张顺**：省事，三两三拿下走人，不用挑丝不用分货。但周老板开的价比张顺高了二钱银子一整担——这是真金白银的差。

三、**跟周老板另谈**：他是月港来的大客商，走的是南洋的线。你手里没有他要的"三十斤上好"，但你知道**谁有**——丁娘子的丝成色比你还好。要是能搭个桥，往后也许有长远的路子。但丁娘子会怎么想？你又凭什么搭这个桥？

四、**先问张顺"代织"的事**：周老板还在，张顺也在——三个人当面谈，也许能碰出点别的什么来。但你一提"代织"，等于告诉周老板你是想自己攒本钱往上爬，会不会被人看轻？
"""


def test_basic_extraction():
    """基本提取：4 个中文数字选项"""
    options = extract_inline_options(REAL_USER_REPORT)
    assert len(options) == 4, f"应提取 4 个选项，实际 {len(options)}"
    assert options[0]["index"] == "一"
    assert options[0]["label"] == "答应周老板"
    assert options[1]["label"] == "全卖给张顺"
    assert options[2]["label"] == "跟周老板另谈"
    assert options[3]["label"] == "先问张顺\"代织\"的事"
    print(f"✅ test_basic_extraction: {len(options)} 个选项")
    for opt in options:
        print(f"    {opt['index']}、{opt['label']}")


def test_extraction_arabic_numbers():
    """阿拉伯数字选项"""
    text = """
你打算：

1. 直接回家
2. 去茶馆
3. 找李四算账
"""
    options = extract_inline_options(text)
    assert len(options) == 3
    assert options[0]["index"] == "1"
    assert options[0]["label"] == "直接回家"
    print("✅ test_extraction_arabic_numbers: 3 个阿拉伯数字选项")


def test_extraction_mixed_punctuation():
    """混合标点：顿号、点、冒号"""
    text = """
一、答应他
二. 拒绝他
三: 沉默
"""
    options = extract_inline_options(text)
    assert len(options) == 3
    assert options[0]["label"] == "答应他"
    assert options[1]["label"] == "拒绝他"
    assert options[2]["label"] == "沉默"
    print("✅ test_extraction_mixed_punctuation: 顿号/点/冒号 全部识别")


def test_extraction_with_bold():
    """带 ** 加粗的选项"""
    text = """一、**答应周老板**：详细描述...
二、**全卖张顺**：详细描述..."""
    options = extract_inline_options(text)
    assert len(options) == 2
    # ** 应被清理
    assert "**" not in options[0]["label"]
    assert "答应周老板" in options[0]["label"]
    print("✅ test_extraction_with_bold: ** 加粗已清理")


def test_max_options_limit():
    """max_options 限制"""
    text = "\n".join([f"{['一','二','三','四','五','六','七','八','九','十'][i]}、选项{i+1}" for i in range(10)])
    options = extract_inline_options(text, max_options=4)
    assert len(options) == 4, f"应限制为 4 个，实际 {len(options)}"
    print(f"✅ test_max_options_limit: {len(options)} 个（限制 4）")


def test_empty_text():
    """空文本"""
    assert extract_inline_options("") == []
    assert extract_inline_options(None) == []
    print("✅ test_empty_text: 空文本返回 []")


def test_no_options():
    """无选项文本"""
    text = "今天天气不错，万里无云。\n你想着待会要做什么。"
    options = extract_inline_options(text)
    assert options == []
    print("✅ test_no_options: 无选项时返回 []")


def test_short_options_filtered():
    """过短标签被过滤"""
    text = "一、x\n二、正式选项\n三、y"
    options = extract_inline_options(text)
    # 一、x (1字符) 和 三、y (1字符) 应被过滤
    assert len(options) == 1
    assert options[0]["label"] == "正式选项"
    print(f"✅ test_short_options_filtered: 1 字符标签被过滤")


def test_merge_uses_structured():
    """merge 优先用结构化选项"""
    structured = [{"voice_name": "A", "intent_text": "选项A"}]
    merged = merge_voice_options(structured, REAL_USER_REPORT)
    assert len(merged) == 1
    assert merged[0]["voice_name"] == "A"
    assert "source" not in merged[0] or merged[0].get("source") != "inline_extracted"
    print("✅ test_merge_uses_structured: 结构化选项优先")


def test_merge_fallback_to_inline():
    """结构化为空时，fallback 到内嵌提取"""
    merged = merge_voice_options(None, REAL_USER_REPORT)
    assert len(merged) == 4
    assert merged[0]["voice_name"] == "一"
    assert merged[0]["intent_text"] == "答应周老板"
    assert merged[0]["source"] == "inline_extracted"
    print("✅ test_merge_fallback_to_inline: 4 个内嵌选项被回填")


def test_merge_empty_input():
    """空输入"""
    assert merge_voice_options(None, "") == []
    assert merge_voice_options([], "hello world") == []
    print("✅ test_merge_empty_input: 空输入返回 []")


def test_xss_protection_in_label():
    """XSS 防护：label 含 HTML 字符"""
    text = "一、<script>alert(1)</script>"
    options = extract_inline_options(text)
    # 标签里的 HTML 应被保留（前端 escapeHtml 处理）
    assert options[0]["label"].startswith("<script>")
    # 但完整 dict 给前端，前端会 escape
    print("✅ test_xss_protection_in_label: 标签保留（前端 escape）")


if __name__ == "__main__":
    print("=" * 50)
    print("内嵌选项提取 测试（v1.6.9）")
    print("=" * 50)
    test_basic_extraction()
    test_extraction_arabic_numbers()
    test_extraction_mixed_punctuation()
    test_extraction_with_bold()
    test_max_options_limit()
    test_empty_text()
    test_no_options()
    test_short_options_filtered()
    test_merge_uses_structured()
    test_merge_fallback_to_inline()
    test_merge_empty_input()
    test_xss_protection_in_label()
    print("\n✅ 所有 v1.6.9 内嵌选项测试通过")