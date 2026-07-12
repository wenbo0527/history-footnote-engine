"""v2.10.2 W52 followup: currency 单元测试

验证银钱单位的统一：
- parse_amount: 字符串 → float
- to_liang: float → "X 两 Y 钱"
- to_compact_liang: 紧凑显示
"""
import pytest

from history_footnote.currency import (
    parse_amount,
    to_liang,
    to_compact_liang,
    to_liang_or_yuan,
    UNIT_TO_LIANG,
    CN_DIGITS,
)


# ============= parse_amount =============

def test_parse_arabic_integer():
    """纯阿拉伯数字 → 默认两"""
    assert parse_amount("5") == 5.0
    assert parse_amount("0") == 0.0
    assert parse_amount("100") == 100.0


def test_parse_arabic_float():
    """阿拉伯小数"""
    assert parse_amount("5.7") == 5.7
    assert parse_amount("0.5") == 0.5


def test_parse_arabic_with_unit_liang():
    """阿拉伯 + 两"""
    assert parse_amount("5两") == 5.0
    assert parse_amount("5.7两") == 5.7
    assert parse_amount("5两银子") == 5.0


def test_parse_arabic_with_unit_qian():
    """阿拉伯 + 钱"""
    assert parse_amount("5钱") == pytest.approx(0.5)
    assert parse_amount("7钱") == pytest.approx(0.7)
    assert parse_amount("35钱") == pytest.approx(3.5)


def test_parse_arabic_with_unit_fen_li_wen():
    """阿拉伯 + 分/厘/文"""
    assert parse_amount("5分") == 0.05
    assert parse_amount("5厘") == 0.005
    assert parse_amount("100文") == 0.1  # 100 文 = 0.1 两


def test_parse_chinese_integer():
    """中文整数"""
    assert parse_amount("五两") == 5.0
    assert parse_amount("十两") == 10.0
    assert parse_amount("二十两") == 20.0
    assert parse_amount("三十五两") == 35.0
    assert parse_amount("一百两") == 100.0
    assert parse_amount("一千两") == 1000.0


def test_parse_chinese_with_unit_qian():
    """中文 + 钱"""
    assert parse_amount("五钱") == 0.5
    assert parse_amount("三十五钱") == 3.5
    assert parse_amount("十钱") == 1.0


def test_parse_empty_or_invalid():
    """空字符串 / 无效输入 → None"""
    assert parse_amount("") is None
    assert parse_amount("   ") is None
    assert parse_amount("abc") is None
    assert parse_amount(None) is None


# ============= to_liang =============

def test_to_liang_zero():
    """0 → 0 两"""
    assert to_liang(0) == "0 两"


def test_to_liang_integer():
    """整数两 → X 两"""
    assert to_liang(5) == "5 两"
    assert to_liang(100) == "100 两"


def test_to_liang_with_qian():
    """含钱 → X 两 Y 钱"""
    assert to_liang(5.7) == "5 两 7 钱"
    assert to_liang(5.0) == "5 两"


def test_to_liang_qian_only():
    """< 1 两 → X 钱"""
    assert to_liang(0.5) == "5 钱"
    assert to_liang(0.7) == "7 钱"


def test_to_liang_fen_only():
    """< 0.1 两 → X 分"""
    assert to_liang(0.05) == "5 分"
    assert to_liang(0.07) == "7 分"


def test_to_liang_li_only():
    """< 0.01 两 → X 厘"""
    assert to_liang(0.005) == "5 厘"
    assert to_liang(0.003) == "3 厘"


def test_to_liang_complex():
    """复杂小数 → X 两 Y 钱 Z 分 W 厘"""
    assert to_liang(5.789) == "5 两 7 钱 8 分 9 厘"
    assert to_liang(0.123) == "1 钱 2 分 3 厘"


# ============= to_compact_liang =============

def test_to_compact_liang_zero():
    """0 → 0 两"""
    assert to_compact_liang(0) == "0 两"


def test_to_compact_liang_integer():
    """整数两"""
    assert to_compact_liang(5) == "5 两"
    assert to_compact_liang(100) == "100 两"


def test_to_compact_liang_with_qian():
    """含钱"""
    assert to_compact_liang(5.7) == "5 两 7 钱"
    assert to_compact_liang(5.0) == "5 两"


def test_to_compact_liang_small():
    """< 1 两"""
    assert to_compact_liang(0.5) == "5 钱"
    assert to_compact_liang(0.05) == "5 分"
    assert to_compact_liang(0.005) == "5 厘"


def test_to_compact_liang_negative():
    """负数"""
    assert to_compact_liang(-5) == "-5 两"
    assert to_compact_liang(-0.5) == "-5 钱"


# ============= to_liang_or_yuan =============

def test_to_liang_or_yuan_basic():
    """to_liang_or_yuan 保留 2 位小数"""
    assert to_liang_or_yuan(5) == "5.00 两"
    assert to_liang_or_yuan(5.7) == "5.70 两"
    assert to_liang_or_yuan(0.5) == "0.50 两"


# ============= 单位常量 =============

def test_unit_constants():
    """单位常量值正确"""
    assert UNIT_TO_LIANG["两"] == 1.0
    assert UNIT_TO_LIANG["钱"] == 0.1
    assert UNIT_TO_LIANG["分"] == 0.01
    assert UNIT_TO_LIANG["厘"] == 0.001
    assert UNIT_TO_LIANG["文"] == 0.001


def test_cn_digits():
    """中文数字映射正确"""
    assert CN_DIGITS["零"] == 0
    assert CN_DIGITS["一"] == 1
    assert CN_DIGITS["两"] == 2
    assert CN_DIGITS["十"] == 10
    assert CN_DIGITS["百"] == 100
    assert CN_DIGITS["千"] == 1000
    assert CN_DIGITS["万"] == 10000
    assert CN_DIGITS["半"] == 0.5
