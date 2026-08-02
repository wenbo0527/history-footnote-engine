#!/usr/bin/env python
"""🆕 v2.10.32 — 手动输入关键词模糊匹配 单元测试

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21032_fuzzy_match.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, 'src')

from history_footnote.story_mode.engine import _extract_keywords, ScriptedStoryEngine
from history_footnote.story_mode.types import ScriptedVoiceOption


def make_opts():
    """构造测试用 voice_options"""
    return [
        ScriptedVoiceOption(
            voice_id='borrow_money',
            voice_name='💰 向牙行借银子',
            description='咬牙借五两，月息三分',
            inner_voice='月息太重...',
            next_node_id='intro_2_borrow',
        ),
        ScriptedVoiceOption(
            voice_id='sell_loom',
            voice_name='🧵 卖一架织机',
            description='可换三两',
            inner_voice='败家啊...',
            next_node_id='intro_2_sell',
        ),
        ScriptedVoiceOption(
            voice_id='go_suzhou',
            voice_name='🚣 去苏州府',
            description='苏州大单',
            inner_voice='听说能赚大钱',
            next_node_id='intro_2_suzhou',
        ),
        ScriptedVoiceOption(
            voice_id='stay',
            voice_name='🛏️ 留在家中',
            description='哪都不去',
            next_node_id='stay',
        ),
    ]


def test_extract_keywords_chinese():
    """中文关键词提取"""
    kws = _extract_keywords("借钱")
    assert "借" in kws
    assert "钱" in kws
    assert "借钱" in kws
    print(f"  test_extract_keywords_chinese: ✅ (kws={kws[:3]}...)")


def test_extract_keywords_filters_stopwords():
    """停用词被过滤"""
    kws = _extract_keywords("我想去苏州")
    # "我" 是停用词, 应被过滤
    assert "我" not in kws
    assert "苏州" in kws
    assert "去" in kws
    print(f"  test_extract_keywords_filters_stopwords: ✅")


def test_extract_keywords_3grams():
    """3 字词组提取"""
    kws = _extract_keywords("卖织机")
    assert "卖织机" in kws
    assert "卖" in kws
    print(f"  test_extract_keywords_3grams: ✅")


# ============================================================
# Fuzzy match tests
# ============================================================

def _make_engine():
    return ScriptedStoryEngine(None)


def test_fuzzy_voice_id_exact():
    """精确 voice_id 匹配"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("borrow_money", opts)
    assert r is not None
    assert r.voice_id == "borrow_money"
    print(f"  test_fuzzy_voice_id_exact: ✅")


def test_fuzzy_voice_id_substring():
    """voice_id 子串匹配"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("borrow", opts)
    assert r is not None
    assert r.voice_id == "borrow_money"
    print(f"  test_fuzzy_voice_id_substring: ✅")


def test_fuzzy_chinese_keyword():
    """中文关键词匹配"""
    eng = _make_engine()
    opts = make_opts()
    # 借钱
    r = eng._fuzzy_match("借钱", opts)
    assert r is not None
    assert r.voice_id == "borrow_money", f"expected borrow_money, got {r.voice_id if r else None}"
    print(f"  test_fuzzy_chinese_keyword: ✅ ('借钱' → borrow_money)")


def test_fuzzy_long_chinese():
    """长中文输入"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("我想借银子", opts)
    assert r is not None
    assert r.voice_id == "borrow_money"
    print(f"  test_fuzzy_long_chinese: ✅")


def test_fuzzy_sell():
    """卖织机"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("卖织机", opts)
    assert r is not None
    assert r.voice_id == "sell_loom"
    print(f"  test_fuzzy_sell: ✅")


def test_fuzzy_go_suzhou():
    """去苏州"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("去苏州", opts)
    assert r is not None
    assert r.voice_id == "go_suzhou"
    print(f"  test_fuzzy_go_suzhou: ✅")


def test_fuzzy_no_match():
    """完全无关输入 → 无匹配"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("乱码随机输入xyz", opts)
    assert r is None
    print(f"  test_fuzzy_no_match: ✅")


def test_fuzzy_emoji_ignored():
    """emoji 不影响匹配"""
    eng = _make_engine()
    opts = make_opts()
    r = eng._fuzzy_match("💰 借银子 💰", opts)
    assert r is not None
    assert r.voice_id == "borrow_money"
    print(f"  test_fuzzy_emoji_ignored: ✅")


def test_fuzzy_picks_best():
    """多个候选项时选最相似的"""
    eng = _make_engine()
    opts = make_opts()
    # "借银子应急" 应选 borrow_money (有"借银子")
    r = eng._fuzzy_match("借银子应急", opts)
    assert r is not None
    assert r.voice_id == "borrow_money"
    print(f"  test_fuzzy_picks_best: ✅")


def test_fuzzy_case_insensitive():
    """大小写不敏感"""
    eng = _make_engine()
    opts = make_opts()
    r1 = eng._fuzzy_match("Borrow_Money", opts)
    r2 = eng._fuzzy_match("borrow_money", opts)
    r3 = eng._fuzzy_match("BORROW_MONEY", opts)
    assert r1 is not None and r2 is not None and r3 is not None
    assert r1.voice_id == r2.voice_id == r3.voice_id == "borrow_money"
    print(f"  test_fuzzy_case_insensitive: ✅")


# ============================================================
# Integration: handle_input with free text
# ============================================================

def test_handle_input_with_chinese_text():
    """handle_input 接收中文自由输入"""
    from history_footnote.story_mode.chapter_loader import get_chapter
    ch = get_chapter(1)
    eng = ScriptedStoryEngine(ch)

    # 设置 state 到 intro_2_xxx 节点
    state = {"scripted_node_id": "intro_1_father_ill", "scripted_flags": [], "scripted_visits": []}

    # 玩家输入"借钱"
    narr, opts, info = eng.handle_input(state, "借钱")

    # 应该匹配到 borrow_money → 跳到 intro_2_borrow
    assert info.get("new_node_id") == "intro_2_borrow", f"got {info.get('new_node_id')}"
    assert "cash_delta" in info.get("effects_applied", {})
    print(f"  test_handle_input_with_chinese_text: ✅ (借钱 → intro_2_borrow)")


def test_handle_input_no_match_returns_error():
    """完全无关输入 → 错误 (不破坏剧本)"""
    from history_footnote.story_mode.chapter_loader import get_chapter
    ch = get_chapter(1)
    eng = ScriptedStoryEngine(ch)

    state = {"scripted_node_id": "intro_1_father_ill", "scripted_flags": [], "scripted_visits": []}

    narr, opts, info = eng.handle_input(state, "外星人攻击地球")

    # 应该错误
    assert "error" in info or "剧本错误" in narr
    print(f"  test_handle_input_no_match_returns_error: ✅")


def run_all():
    print("=== v2.10.32 手动输入关键词模糊匹配 单元测试 ===\n")
    print("## 关键词提取")
    test_extract_keywords_chinese()
    test_extract_keywords_filters_stopwords()
    test_extract_keywords_3grams()

    print("\n## 模糊匹配")
    test_fuzzy_voice_id_exact()
    test_fuzzy_voice_id_substring()
    test_fuzzy_chinese_keyword()
    test_fuzzy_long_chinese()
    test_fuzzy_sell()
    test_fuzzy_go_suzhou()
    test_fuzzy_no_match()
    test_fuzzy_emoji_ignored()
    test_fuzzy_picks_best()
    test_fuzzy_case_insensitive()

    print("\n## handle_input 集成")
    test_handle_input_with_chinese_text()
    test_handle_input_no_match_returns_error()

    print("\n" + "=" * 60)
    print("✅ 全部 13 个模糊匹配单元测试通过!")
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