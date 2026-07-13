"""🆕 v2.10.3 SKILL-8 认知框架锁定（原 dm_skills.py 第 972-1003 行）

玩家选择路线后，叙事中自然突出/抑制某些信息。
"""
from __future__ import annotations

from history_footnote.dm_skills.types import CognitiveFrame


def skill_8_lock_cognitive_frame(
    era_config: dict,
    state: dict,
) -> CognitiveFrame | None:
    """SKILL-8 认知框架锁定：路线 → 信息过滤

    玩家选择路线后，叙事中自然突出/抑制某些信息。
    """
    route = state.get("route_tendency", "")
    if not route:
        # 从已解锁的 insight 推断
        unlocked = state.get("unlocked_insights", [])
        if "ins_imperial_exam" in unlocked:
            route = "imperial_exam"
        elif "ins_business" in unlocked:
            route = "business"

    if not route:
        return None

    frames = era_config.get("world", {}).get("cognitive_frames", {}) or era_config.get("cognitive_frames", {})
    if route not in frames:
        return None

    return CognitiveFrame(
        frame_id=route,
        highlight=frames[route].get("highlight", []),
        suppress=frames[route].get("suppress", []),
    )