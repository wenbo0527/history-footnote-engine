"""🆕 v2.10.24 — D&D 检定服务

从 engine.py 拆分出来, 独立负责:
- 表达式解析
- d20 投骰
- 属性解析
"""
from __future__ import annotations

import logging
import random
from typing import Optional, Tuple

from history_footnote.story_mode.constants import (
    ABSTRACT_ATTR_BASE,
    ATTR_MOD_FLAGS,
    CHECK_RESULT_FAIL,
    CHECK_RESULT_GREAT,
    CHECK_RESULT_SUCCESS,
    DC_BASE,
    DC_PER_VALUE,
    RESOURCE_ATTRS,
    TIER_GREAT_BONUS,
    VALID_CHECK_RESULTS,
)

logger = logging.getLogger(__name__)


def roll_d20() -> int:
    """D&D 风格的 d20 投骰 (1-20)"""
    return random.randint(1, 20)


class CheckService:
    """D&D 检定服务 - 表达式解析 + 属性解析 + d20 投骰"""

    def __init__(self, rng: Optional[random.Random] = None):
        """rng: 可注入 random 实例用于测试"""
        self._rng = rng or random.Random()

    def roll(self) -> int:
        """d20 投骰 (1-20)"""
        return self._rng.randint(1, 20)

    def do_check(self, check_expr: str, game_state: dict) -> Tuple[str, int]:
        """执行 D&D 检定

        check_expr 格式:
        - "charisma >= 2" → 属性检定 (d20+charisma vs DC)
        - "cash >= 3"      → 资源硬性检查
        - "luck >= 4"      → 随机检定
        - "flag.has_debt"  → flag 存在检查

        返回 (结果档位, d20 值)
        """
        try:
            attr, op, value = self._parse_check(check_expr)
        except ValueError as e:
            logger.warning(f"check parse failed: {e}")
            return (CHECK_RESULT_FAIL, 0)

        actual = self.resolve_attr(attr, game_state)

        # 硬性检查 (compare)
        if not self._compare(actual, op, value):
            return (CHECK_RESULT_FAIL, 0)

        # 资源 / flag 是硬性检查, 无 d20
        if attr in RESOURCE_ATTRS or attr.startswith("flag."):
            return (CHECK_RESULT_SUCCESS, 0)

        # 抽象属性: d20 + attr vs DC
        d20 = self.roll()
        total = d20 + actual
        dc = DC_BASE + value * DC_PER_VALUE

        if total >= dc + TIER_GREAT_BONUS:
            return (CHECK_RESULT_GREAT, d20)
        if total >= dc:
            return (CHECK_RESULT_SUCCESS, d20)
        return (CHECK_RESULT_FAIL, d20)

    def resolve_attr(self, attr: str, game_state: dict) -> int:
        """解析属性值

        支持:
        - charisma / skill / luck / courage: 默认 2, flag 加成
        - cash / rice / debt / looms / stamina: 从 game_state 取
        - flag.<name>: 1 if flag exists else 0
        """
        if attr.startswith("flag."):
            flag_name = attr[5:]
            flags = game_state.get("scripted_flags") or []
            return 1 if flag_name in flags else 0

        if attr in RESOURCE_ATTRS:
            return game_state.get(attr, 0) or 0

        # 抽象属性 (默认 2)
        base = ABSTRACT_ATTR_BASE
        flags = game_state.get("scripted_flags") or []
        for f in ATTR_MOD_FLAGS.get(attr, []):
            if f in flags:
                base += 1
        return base

    def _parse_check(self, check_expr: str) -> Tuple[str, str, int]:
        """解析 check 表达式为 (attr, op, value)

        支持格式:
        - "<attr> <op> <value>" (e.g. "charisma >= 2")
        - "flag.<name>" (默认 >= 1)
        """
        parts = check_expr.split()
        if len(parts) != 3:
            # 特殊情况: "flag.<name>"
            if parts and parts[0].startswith("flag."):
                return (parts[0], ">=", 1)
            raise ValueError(f"invalid check expression: {check_expr!r}")
        attr, op, value_str = parts
        return (attr, op, int(value_str))

    @staticmethod
    def _compare(actual: int, op: str, value: int) -> bool:
        """比较运算"""
        if op == ">=":
            return actual >= value
        if op == ">":
            return actual > value
        if op == "<=":
            return actual <= value
        if op == "<":
            return actual < value
        if op == "==":
            return actual == value
        return False