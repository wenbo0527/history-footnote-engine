"""v2.10.1 W52 候选 E: narrative_postprocess 单元测试

从 agent.py:485-547 抽出的后处理逻辑测试。
"""
import pytest

from history_footnote.dm_agent.narrative_postprocess import (
    _narr_ends_with_question,
    _truncate_to_sentence,
    check_narrative_quality,
    postprocess_narrative,
    MAX_CHARS_BY_MODE,
    DEFAULT_CHAR_LIMIT,
)


# ============= 工具函数 =============

def test_narr_ends_with_question_chinese():
    """中文问号 ? 应当识别"""
    assert _narr_ends_with_question("接下来怎么办？") is True
    assert _narr_ends_with_question("你愿意吗？") is True


def test_narr_ends_with_question_english():
    """英文问号 ? 应识别"""
    assert _narr_ends_with_question("What do you do?") is True


def test_narr_ends_with_question_false():
    """无问号应 False"""
    assert _narr_ends_with_question("你继续做你的事。") is False
    assert _narr_ends_with_question("") is False


def test_narr_ends_with_question_within_30():
    """问号在末尾 30 字符内应 True"""
    long_text = "中" * 20 + "怎么办？"  # 问号在末 5 字符
    assert _narr_ends_with_question(long_text) is True
    # 问号在末 30 字符边界内
    long_text2 = "中" * 25 + "？"
    assert _narr_ends_with_question(long_text2) is True
    # 末 30 字符只有句号/逗号
    long_text3 = "中" * 25 + "。"  # 末 30 字符 = 25 中 + 1 句号
    assert _narr_ends_with_question(long_text3) is False


def test_truncate_to_sentence_no_truncation():
    """短文本不截断"""
    text = "这是一个短文本。"
    assert _truncate_to_sentence(text, 800) == text


def test_truncate_to_sentence_at_period():
    """长文本在句号处截断"""
    # 600 字符 limit → cut_at = 480，找 480~530 内的句号
    text = "一二三四五。" * 100  # 每 6 字符一个句号
    truncated = _truncate_to_sentence(text, 600)
    assert len(truncated) <= 600
    assert truncated.endswith("。")  # 在句号处截断


def test_truncate_to_sentence_no_period():
    """无句号时硬截 + 省略号"""
    text = "x" * 1000
    truncated = _truncate_to_sentence(text, 600)
    assert len(truncated) <= 600
    assert truncated.endswith("……")


# ============= check_narrative_quality =============

def test_check_short():
    """过短（<100 字）应 need_retry"""
    short = "短" * 50
    need, reason = check_narrative_quality(short, "now_time")
    assert need is True
    assert "短答" in reason


def test_check_too_long_now_time():
    """now_time 模式 >500 字应 need_retry"""
    long_text = "中" * 600 + "？"  # 601 字
    need, reason = check_narrative_quality(long_text, "now_time")
    assert need is True
    assert "过长" in reason


def test_check_too_long_slow_time():
    """slow_time 模式 >700 字应 need_retry"""
    long_text = "中" * 800 + "？"
    need, reason = check_narrative_quality(long_text, "slow_time")
    assert need is True


def test_check_no_question():
    """末尾无问号应 need_retry"""
    text = "中" * 200 + "。"  # 200 字 + 句号
    need, reason = check_narrative_quality(text, "now_time")
    assert need is True
    assert "问号" in reason


def test_check_ok():
    """合规 narrative 应 False"""
    text = "中" * 200 + "？"
    need, _ = check_narrative_quality(text, "now_time")
    assert need is False


def test_check_all_modes():
    """各模式上限生效"""
    for mode, limit in MAX_CHARS_BY_MODE.items():
        # 上限 +1 字应 fail
        text = "中" * (limit + 1) + "？"
        need, _ = check_narrative_quality(text, mode)
        assert need is True, f"mode={mode} limit={limit} 应 fail"


# ============= postprocess_narrative =============

def test_postprocess_no_retry_needed():
    """合规 narrative 不重试"""
    text = "中" * 200 + "？"
    final, status = postprocess_narrative(text, "now_time", retry_fn=None)
    assert final == text
    assert status == "ok"


def test_postprocess_retry_success():
    """首次短答，重试后合规"""
    short = "短" * 50

    def retry():
        return "中" * 200 + "？"

    final, status = postprocess_narrative(short, "now_time", retry_fn=retry)
    assert status == "retried_success"
    assert len(final) == 201
    assert final.endswith("？")


def test_postprocess_retry_all_fail_truncate():
    """重试仍超长，截断兜底"""
    long_text = "中" * 1000 + "？"

    def retry():
        return "中" * 999 + "？"

    final, status = postprocess_narrative(
        long_text, "now_time", retry_fn=retry, max_retries=2
    )
    assert status == "truncated"
    assert len(final) < 1000  # 应被截断


def test_postprocess_retry_raises():
    """retry_fn 抛异常时不影响兜底"""
    long_text = "中" * 1000 + "？"

    def retry():
        raise RuntimeError("LLM 失败")

    final, status = postprocess_narrative(
        long_text, "now_time", retry_fn=retry
    )
    # 异常被吞，最终 truncate
    assert status == "truncated"


def test_postprocess_unknown_time_mode():
    """未知 time_mode 应用 DEFAULT_CHAR_LIMIT"""
    text = "中" * (DEFAULT_CHAR_LIMIT + 1) + "？"
    need, _ = check_narrative_quality(text, "unknown_mode")
    assert need is True
