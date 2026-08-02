"""🆕 v2.10.30 — NodeFilter (节点可见性过滤)

根据 game_state 判断 ScriptedNode 是否应该被访问

检查规则:
1. required_city: game_state.city 必须匹配
2. required_flags: 所有 flag 必须在 scripted_flags 中
3. forbidden_flags: 任一 flag 必须在 scripted_flags 中 → 不可访问
4. round_min/round_max: 当前 round 在范围内
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from history_footnote.story_mode.types import ScriptedNode

logger = logging.getLogger(__name__)


class NodeFilter:
    """节点可见性过滤服务"""

    @staticmethod
    def is_accessible(node: "ScriptedNode", game_state: dict) -> bool:
        """判断节点是否可在当前 game_state 下访问"""
        # 1. city 检查
        if node.required_city:
            current_city = game_state.get("city", "shengze")
            if current_city != node.required_city:
                return False

        # 2. required_flags (所有都必须有)
        if node.required_flags:
            current_flags = set(game_state.get("scripted_flags") or [])
            for flag in node.required_flags:
                if flag not in current_flags:
                    return False

        # 3. forbidden_flags (任一有都不可访问)
        if node.forbidden_flags:
            current_flags = set(game_state.get("scripted_flags") or [])
            for flag in node.forbidden_flags:
                if flag in current_flags:
                    return False

        # 4. round 范围检查
        current_round = game_state.get("round", 1)
        if current_round < node.round_min:
            return False
        if current_round > node.round_max:
            return False

        return True

    @staticmethod
    def get_unmet_requirements(node: "ScriptedNode", game_state: dict) -> list[str]:
        """返回所有未满足的要求 (用于调试)

        返回 list[reason]:
        - "city:mismatch (need shengze, got suzhou)"
        - "flag:missing (need has_debt)"
        - "flag:forbidden (has has_debt)"
        - "round:too_low (need >=3, got 1)"
        - "round:too_high (need <=5, got 10)"
        """
        reasons = []

        if node.required_city:
            current_city = game_state.get("city", "shengze")
            if current_city != node.required_city:
                reasons.append(
                    f"city:mismatch (need {node.required_city}, got {current_city})"
                )

        if node.required_flags:
            current_flags = set(game_state.get("scripted_flags") or [])
            for flag in node.required_flags:
                if flag not in current_flags:
                    reasons.append(f"flag:missing (need {flag})")

        if node.forbidden_flags:
            current_flags = set(game_state.get("scripted_flags") or [])
            for flag in node.forbidden_flags:
                if flag in current_flags:
                    reasons.append(f"flag:forbidden (has {flag})")

        current_round = game_state.get("round", 1)
        if current_round < node.round_min:
            reasons.append(
                f"round:too_low (need >={node.round_min}, got {current_round})"
            )
        if current_round > node.round_max:
            reasons.append(
                f"round:too_high (need <={node.round_max}, got {current_round})"
            )

        return reasons