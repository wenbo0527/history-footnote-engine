"""🆕 v2.10.3 SKILL-6 失败叙事化（原 dm_skills.py 第 752-795 行）

失败不是终点，是岔路口。映射到 failure_mappings 中的具体转化。
"""
from __future__ import annotations

from history_footnote.dm_skills.types import FailureNarrative


FAILURE_TYPES = {
    "action": "行动失败（技能不足）→ 失败开启新路径",
    "persuasion": "说服失败 → NPC拒绝但暴露信息",
    "exploration": "探索失败 → 看到意料之外的东西",
    "choice": "选择失败 → 后果比预期更复杂",
}


def skill_6_handle_failure(
    era_config: dict,
    state: dict,
    failure_type: str = "",
) -> FailureNarrative | None:
    """SKILL-6 失败叙事化

    失败不是终点，是岔路口。映射到 failure_mappings 中的具体转化。
    """
    if not failure_type:
        return None

    mappings = era_config.get("world", {}).get("failure_mappings", {}) or era_config.get("failure_mappings", {})
    conversion = mappings.get(failure_type, "")

    if not conversion:
        # 默认转化
        defaults = {
            "action": "失败开启新路径：你做不到 A，但发现了 B 的可能",
            "persuasion": "说服失败但 NPC 透露了关键信息：'不卖给你，但有件事...让你知道'",
            "exploration": "找不到目标，但翻到/看到意料之外的东西",
            "choice": "后果比预期复杂：'你以为会怎样，实际却...'",
        }
        conversion = defaults.get(failure_type, "失败转化为新故事")

    return FailureNarrative(
        failure_type=failure_type,
        conversion=conversion,
        new_path="",
    )