"""DiceEngine——DND式掷骰子系统

支持标准DND骰子表达式：
- d20, d12, d10, d8, d6, d4, d100
- 组合：2d6+3, 1d20-1, 3d8+2d6
- 优势/劣势（双骰取高/取低）
- 大成功/大失败（d20=20/1）

设计：DiceEngine是**确定性服务的随机性补充**——
- 规则引擎：严格计算（赋税、变量变更）
- DiceEngine：随机判定（谈判、遭遇、机会）

DND的精髓：**选择+判定+后果**。
"""
from __future__ import annotations

import random
import re
from typing import Any


class DiceResult:
    """单次掷骰结果"""

    def __init__(
        self,
        expression: str,
        rolls: list[int],
        modifier: int,
        total: int,
        purpose: str = "",
    ):
        self.expression = expression
        self.rolls = rolls
        self.modifier = modifier
        self.total = total
        self.purpose = purpose
        self.is_critical_success = False
        self.is_critical_fail = False
        self._compute_criticals()

    def _compute_criticals(self):
        """大成功/大失败判定（d20=20或1）"""
        if len(self.rolls) == 1 and self.rolls[0] == 20:
            self.is_critical_success = True
        elif len(self.rolls) == 1 and self.rolls[0] == 1:
            self.is_critical_fail = True

    def to_dict(self) -> dict:
        return {
            "expression": self.expression,
            "rolls": self.rolls,
            "modifier": self.modifier,
            "total": self.total,
            "purpose": self.purpose,
            "is_critical_success": self.is_critical_success,
            "is_critical_fail": self.is_critical_fail,
        }

    def __repr__(self):
        crit = " 💥" if self.is_critical_success else (" 💀" if self.is_critical_fail else "")
        return f"<Dice {self.expression} = {self.total}{crit}>"


class DiceEngine:
    """DND式掷骰子引擎"""

    # 支持的骰子面数
    SUPPORTED_DICE = {3, 4, 6, 8, 10, 12, 20, 100}

    # 骰子表达式正则
    DICE_PATTERN = re.compile(r"(\d*)d(\d+)([+\-]\d+)?", re.IGNORECASE)

    def __init__(self, seed: int | None = None):
        """初始化骰子引擎

        Args:
            seed: 随机种子（None=系统时间，用于可重现测试）
        """
        self.rng = random.Random(seed)
        self.history: list[DiceResult] = []

    def roll(
        self,
        dice_expr: str,
        modifier: int = 0,
        purpose: str = "",
    ) -> DiceResult:
        """掷骰子

        Args:
            dice_expr: 骰子表达式（如"2d6+3"、"d20"）
            modifier: 额外的修正值（叠加在表达式后）
            purpose: 这次掷骰的用途（用于日志）

        Returns:
            DiceResult对象

        Examples:
            engine.roll("d20")            → 1-20
            engine.roll("2d6+3", -1)     → 2d6+3-1
            engine.roll("1d20", purpose="牙行谈判")
        """
        expr = dice_expr.strip().lower().replace(" ", "")
        match = self.DICE_PATTERN.fullmatch(expr)

        if not match:
            raise ValueError(f"无效骰子表达式: {dice_expr}")

        count = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))
        expr_modifier = int(match.group(3)) if match.group(3) else 0

        if sides not in self.SUPPORTED_DICE:
            raise ValueError(f"不支持d{sides}，可选: {sorted(self.SUPPORTED_DICE)}")
        if count < 1 or count > 100:
            raise ValueError(f"骰子数量应在1-100之间，实际: {count}")

        # 掷骰子
        rolls = [self.rng.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + expr_modifier + modifier

        result = DiceResult(
            expression=f"{count}d{sides}{('+' + str(expr_modifier)) if expr_modifier >= 0 else str(expr_modifier)}{('+' + str(modifier)) if modifier else ''}",
            rolls=rolls,
            modifier=expr_modifier + modifier,
            total=total,
            purpose=purpose,
        )

        self.history.append(result)
        return result

    def roll_with_advantage(self, purpose: str = "") -> DiceResult:
        """优势（d20掷两次取高）"""
        r1 = self.roll("d20", purpose=purpose + " [优势#1]")
        r2 = self.roll("d20", purpose=purpose + " [优势#2]")
        # 合并为一个结果
        final_rolls = [max(r1.total, r2.total)]
        result = DiceResult(
            expression="d20 (advantage)",
            rolls=final_rolls,
            modifier=0,
            total=max(r1.total, r2.total),
            purpose=purpose,
        )
        self.history.append(result)
        return result

    def roll_with_disadvantage(self, purpose: str = "") -> DiceResult:
        """劣势（d20掷两次取低）"""
        r1 = self.roll("d20", purpose=purpose + " [劣势#1]")
        r2 = self.roll("d20", purpose=purpose + " [劣势#2]")
        final_rolls = [min(r1.total, r2.total)]
        result = DiceResult(
            expression="d20 (disadvantage)",
            rolls=final_rolls,
            modifier=0,
            total=min(r1.total, r2.total),
            purpose=purpose,
        )
        self.history.append(result)
        return result

    def check(
        self,
        difficulty: int,
        dice_expr: str = "d20",
        modifier: int = 0,
        purpose: str = "",
    ) -> dict:
        """DC（困难等级）判定

        DND标准：roll d20+modifier vs DC
        - total >= DC: success
        - total < DC: fail
        - d20=20: 自动成功（大成功）
        - d20=1: 自动失败（大失败）

        Args:
            difficulty: DC（困难等级），通常5/10/15/20/25
            dice_expr: 骰子表达式（默认d20）
            modifier: 修正值
            purpose: 用途

        Returns:
            {
                "result": DiceResult,
                "dc": int,
                "success": bool,
                "margin": int,  # total - DC
                "is_critical_success": bool,
                "is_critical_fail": bool,
            }
        """
        result = self.roll(dice_expr, modifier=modifier, purpose=purpose)
        return {
            "result": result,
            "dc": difficulty,
            "success": result.is_critical_success or (not result.is_critical_fail and result.total >= difficulty),
            "margin": result.total - difficulty,
            "is_critical_success": result.is_critical_success,
            "is_critical_fail": result.is_critical_fail,
        }

    def weighted_choice(self, choices: list[dict], key: str = "item") -> dict:
        """加权随机选择

        Args:
            choices: [{"<key>": anything, "weight": int}, ...]
            key: 提取哪个字段作为返回值（默认"item"，也可以是"outcome"等）

        Returns:
            被选中的choice的<key>字段

        Examples:
            e.weighted_choice([{"item": "A", "weight": 3}])  # 旧API
            e.weighted_choice([{"outcome": {...}, "weight": 3}], key="outcome")  # 新API
        """
        if not choices:
            raise ValueError("choices不能为空")
        weights = [c.get("weight", 1) for c in choices]
        selected = self.rng.choices(choices, weights=weights, k=1)[0]
        if key not in selected:
            # 兼容：直接返回整个dict
            return selected
        return selected[key]

    def chance(self, probability: float) -> bool:
        """按概率判定

        Args:
            probability: 0-1之间

        Returns:
            True=触发，False=不触发
        """
        return self.rng.random() < probability

    def get_recent_history(self, n: int = 5) -> list[DiceResult]:
        """获取最近n次掷骰结果"""
        return self.history[-n:]

    def clear_history(self) -> None:
        """清空历史（每回合开始时调用）"""
        self.history = []