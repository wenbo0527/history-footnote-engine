"""🆕 v2.10.3 SKILL-5 价值观发声（原 dm_skills.py 第 684-751 行）

根据状态激活内在声音（5 个价值维度 × 5 个等级）。
"""
from __future__ import annotations

import re

from history_footnote.dm_skills.types import PacingDecision, SceneAssessment, VoiceActivation


def skill_5_activate_voices(
    era_config: dict,
    state: dict,
    assessment: SceneAssessment,
    pacing: PacingDecision,
) -> list[VoiceActivation]:
    """SKILL-5 价值观发声：根据状态激活内在声音

    5 个价值维度：
    - tradition_vs_change
    - duty_vs_freedom
    - pragmatism_vs_idealism
    - independence_vs_network
    - acceptance_vs_resistance

    等级 1-5，越高声音越响。

    只有在 slow_time（慢时间）或重大抉择时才会激活。
    """
    voices_def = era_config.get("world", {}).get("voices", []) or era_config.get("voices", [])
    if not voices_def:
        return []

    value_shifts = state.get("value_shifts", {})
    variables = state.get("variables", {})
    unlocked_insights = state.get("unlocked_insights", [])

    activated = []
    for v in voices_def:
        voice_id = v.get("id", "")
        voice_name = v.get("name", "未命名")
        trigger = v.get("trigger", "")

        # 计算强度
        intensity = 1
        if "always" in trigger:
            intensity = 3
        elif value_shifts.get(voice_id, 0) >= 3:
            intensity = 4  # 玩家内化了这种价值观
        elif voice_id in unlocked_insights:
            intensity = 5  # 玩家解锁了相关认知 → 强发声
        else:
            # 检查变量阈值
            m = re.match(r"(\w+)\s*([><=]+)\s*(\d+)", trigger)
            if m:
                var_id, op, threshold = m.group(1), m.group(2), int(m.group(3))
                cur = variables.get(var_id, 0)
                if op == ">" and cur > threshold:
                    intensity = 3
                elif op == "<" and cur < threshold:
                    intensity = 3
                elif op == ">=" and cur >= threshold:
                    intensity = 3

        # 只有在慢时间或重大抉择时发声
        if pacing.time_mode == "slow_time" and intensity >= 3:
            activated.append(VoiceActivation(
                voice_id=voice_id,
                voice_name=voice_name,
                intensity=intensity,
                expression=v.get("prompt_fragment", ""),
            ))

    return activated