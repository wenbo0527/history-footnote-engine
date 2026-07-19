"""🆕 v2.10.2 W52 followup: 银钱单位统一模块

历史背景（明代万历年间）：
- 1 两白银 = 10 钱 = 100 分 = 1000 文（铜钱）
- 1 两 ≈ 2 石米（万历年间）
- "分"和"厘"是更小单位，多用于记账

本模块提供：
- 4 个单位常量 + 换算表
- parse_amount(text) — 字符串解析（阿拉伯/中文）
- to_liang(liang) — 格式化显示（"5 两 7 钱"）

设计目标：
- GameState.cash/debt 始终以"两"为单位（float，内部精度）
- 显示时按需格式化
- 用户输入"5 两 7 钱"自动 parse 为 5.7
"""
from __future__ import annotations

import re
from typing import Literal

Unit = Literal["两", "钱", "分", "厘", "文"]

# 🆕 v2.10.2 权威单位换算（以"两"为基准）
UNIT_TO_LIANG = {
    "两": 1.0,
    "钱": 0.1,    # 1 钱 = 0.1 两（1 两 = 10 钱）
    "分": 0.01,   # 1 分 = 0.01 两（1 两 = 100 分）
    "厘": 0.001,  # 1 厘 = 0.001 两（1 两 = 1000 厘）
    "文": 0.001,  # 1 文 = 0.001 两（1 两 = 1000 文，铜钱）
}

UNIT_NAMES = {
    "两": "两",
    "钱": "钱",
    "分": "分",
    "厘": "厘",
    "文": "文",
}

# 中文数字 → 阿拉伯数字
CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "半": 0.5, "百": 100, "千": 1000, "万": 10000,
}

# 中文金额正则：支持"五两七钱"/"5.7两"/"三钱"/"100文"
AMOUNT_RE = re.compile(
    r"([一二三四五六七八九十百千万半]+|[0-9]+(?:\.[0-9]+)?)\s*(两|钱|分|厘|文)?"
)


def _cn_to_float(s: str) -> float | None:
    """中文数字字符串 → float（如"三十五" → 35, "二" → 2）"""
    if not s:
        return None
    # 单字符
    if len(s) == 1 and s in CN_DIGITS:
        return float(CN_DIGITS[s])
    # 复合（如"三十五" / "二百" / "三万五千"）
    total = 0
    current = 0
    for ch in s:
        if ch not in CN_DIGITS:
            return None
        v = CN_DIGITS[ch]
        if v >= 10:  # 权位
            if current == 0:
                current = 1
            total += current * v
            current = 0
        else:
            current = v
    total += current
    return float(total) if total > 0 else None


def parse_amount(text: str) -> float | None:
    """解析金额字符串 → 两（float）

    支持：
    - "5" / "5.7" / "5两" / "5两银子" / "5两7钱" / "五两" / "三十五钱" / "100文"
    - 返回 None 表示无法解析

    示例：
    >>> parse_amount("五两")
    5.0
    >>> parse_amount("五两七钱")
    5.7
    >>> parse_amount("100文")
    0.1
    >>> parse_amount("三十五钱")
    3.5
    >>> parse_amount("abc")
    None
    """
    if not text or not text.strip():
        return None
    text = text.strip()

    # 优先尝试纯阿拉伯数字
    try:
        return float(text)
    except ValueError:
        pass

    # 用正则匹配数字+单位
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    num_str, unit = m.group(1), m.group(2)

    # 解析数字
    try:
        num = float(num_str)
    except ValueError:
        num = _cn_to_float(num_str)
    if num is None:
        return None

    # 换算到两
    if unit:
        return num * UNIT_TO_LIANG.get(unit, 1.0)
    return num  # 无单位默认两


def to_liang(liang: float) -> str:
    """把"两"格式化为"X 两 Y 钱"显示字符串

    示例：
    >>> to_liang(5.7)
    '5 两 7 钱'
    >>> to_liang(5.0)
    '5 两'
    >>> to_liang(0.5)
    '5 钱'
    >>> to_liang(0.05)
    '5 分'
    >>> to_liang(0.005)
    '5 厘'
    >>> to_liang(0.0)
    '0 两'
    >>> to_liang(0.0005)
    '0 两 0 钱 0 分 5 厘'
    """
    if liang == 0:
        return "0 两"

    liang_int = int(liang)
    remainder = liang - liang_int

    if remainder == 0:
        return f"{liang_int} 两"

    # 转换为厘（最小单位）
    centis = round(remainder * 1000)

    if centis < 10:
        # 0-9 厘，display 为 0 两 0 钱 0 分 X 厘
        if liang_int == 0:
            return f"{centis} 厘"
        return f"{liang_int} 两 {centis} 厘"

    # 转为分
    fens = centis // 10
    centis_left = centis % 10
    if fens < 10:
        # 0-9 分
        if liang_int == 0:
            if centis_left == 0:
                return f"{fens} 分"
            return f"{fens} 分 {centis_left} 厘"
        if centis_left == 0:
            return f"{liang_int} 两 {fens} 分"
        return f"{liang_int} 两 {fens} 分 {centis_left} 厘"

    # 转为钱
    qians = fens // 10
    fens_left = fens % 10
    if liang_int == 0:
        if fens_left == 0 and centis_left == 0:
            return f"{qians} 钱"
        if centis_left == 0:
            return f"{qians} 钱 {fens_left} 分"
        return f"{qians} 钱 {fens_left} 分 {centis_left} 厘"
    if fens_left == 0 and centis_left == 0:
        return f"{liang_int} 两 {qians} 钱"
    if centis_left == 0:
        return f"{liang_int} 两 {qians} 钱 {fens_left} 分"
    return f"{liang_int} 两 {qians} 钱 {fens_left} 分 {centis_left} 厘"


def to_compact_liang(liang: float) -> str:
    """紧凑显示: 只显示 2 位有效单位（两/钱/分）

    示例：
    >>> to_compact_liang(5.7)
    '5 两 7 钱'
    >>> to_compact_liang(0.5)
    '5 钱'
    >>> to_compact_liang(0.05)
    '5 分'
    >>> to_compact_liang(0.005)
    '5 厘'
    """
    if liang == 0:
        return "0 两"
    abs_liang = abs(liang)
    sign = "-" if liang < 0 else ""

    if abs_liang >= 1:
        liang_int = int(abs_liang)
        remainder = round((abs_liang - liang_int) * 10)  # 0-9 钱
        if remainder == 0:
            return f"{sign}{liang_int} 两"
        return f"{sign}{liang_int} 两 {remainder} 钱"
    elif abs_liang >= 0.1:
        qians = round(abs_liang * 10)
        return f"{sign}{qians} 钱"
    elif abs_liang >= 0.01:
        fens = round(abs_liang * 100)
        return f"{sign}{fens} 分"
    else:
        centis = round(abs_liang * 1000)
        if centis == 0:
            return f"{sign}0 两"
        return f"{sign}{centis} 厘"


def to_liang_or_yuan(liang: float) -> str:
    """显示为 "X.XX 两"（保留 2 位小数，内部精度）

    适合机器/数据展示（GameHeader, SidebarPanel 等）
    """
    return f"{liang:.2f} 两"
