"""🆕 v2.10.3 dm_skills 子包

历史背景：
- 之前 dm_skills.py 是单文件 1229 行
- v2.10.3 拆为子包（types.py + 8 个 skill_X.py + director.py）
- 100% 向后兼容：从 history_footnote.dm_skills import 仍可访问所有公开符号

子模块索引：
- types.py — 8 个 SKILL dataclass + DMContext 容器
- skill_1_scene.py — SKILL-1 读场判断（ROUTE_KEYWORDS + 4 个 _assess_* helper）
- skill_2_pacing.py — SKILL-2 节奏控制（TIME_MODES + 问询判定）
- skill_3_lead.py — SKILL-3 线索投放（LEAD_TYPES）
- skill_4_history.py — SKILL-4 史实锚定（铺垫/触发/应对）
- skill_5_voice.py — SKILL-5 价值观发声（5 维度）
- skill_6_failure.py — SKILL-6 失败叙事化（FAILURE_TYPES）
- skill_7_verdict.py — SKILL-7 三层裁判（INTENT 词典）
- skill_8_frame.py — SKILL-8 认知框架锁定
- director.py — 综合调度（run_all_skills + _build_skill_directive + run_dm_skills + _detect_intent_type）
"""
from __future__ import annotations

# ============================================================
# 公开符号 re-export（保持 100% 向后兼容）
# ============================================================

# 数据类型
from history_footnote.dm_skills.types import (
    SceneAssessment,
    PacingDecision,
    LeadPlan,
    HistoricalAnchor,
    VoiceActivation,
    FailureNarrative,
    ThreeLayerVerdict,
    CognitiveFrame,
    DMContext,
)

# SKILL 函数
from history_footnote.dm_skills.skill_1_scene import (
    ROUTE_KEYWORDS,
    skill_1_assess_scene,
)
from history_footnote.dm_skills.skill_2_pacing import (
    TIME_MODES,
    INQUIRE_VERBS,
    INQUIRE_OBJECTS,
    SELF_VERBS,
    DETAIL_VERBS,
    skill_2_decide_pacing,
)
from history_footnote.dm_skills.skill_3_lead import (
    LEAD_TYPES,
    skill_3_plan_lead,
)
from history_footnote.dm_skills.skill_4_history import (
    skill_4_anchor_history,
)
from history_footnote.dm_skills.skill_5_voice import (
    skill_5_activate_voices,
)
from history_footnote.dm_skills.skill_6_failure import (
    FAILURE_TYPES,
    skill_6_handle_failure,
)
from history_footnote.dm_skills.skill_7_verdict import (
    INTENT_PATTERNS,
    INTENT_FORBIDDEN_IDS,
    INTENT_REJECT_TEMPLATES,
    INTENT_COMPILED,
    _detect_intent,
    skill_7_three_layer_verdict,
)
from history_footnote.dm_skills.skill_8_frame import (
    skill_8_lock_cognitive_frame,
)

# 综合调度
from history_footnote.dm_skills.director import (
    run_all_skills,
    _build_skill_directive,
    _detect_intent_type,
    run_dm_skills,
)


__all__ = [
    # 类型
    "SceneAssessment",
    "PacingDecision",
    "LeadPlan",
    "HistoricalAnchor",
    "VoiceActivation",
    "FailureNarrative",
    "ThreeLayerVerdict",
    "CognitiveFrame",
    "DMContext",
    # SKILL 函数
    "skill_1_assess_scene",
    "skill_2_decide_pacing",
    "skill_3_plan_lead",
    "skill_4_anchor_history",
    "skill_5_activate_voices",
    "skill_6_handle_failure",
    "skill_7_three_layer_verdict",
    "skill_8_lock_cognitive_frame",
    # 调度
    "run_all_skills",
    "_build_skill_directive",
    "_detect_intent_type",
    "run_dm_skills",
    # 常量
    "ROUTE_KEYWORDS",
    "TIME_MODES",
    "INQUIRE_VERBS",
    "INQUIRE_OBJECTS",
    "SELF_VERBS",
    "DETAIL_VERBS",
    "LEAD_TYPES",
    "FAILURE_TYPES",
    "INTENT_PATTERNS",
    "INTENT_FORBIDDEN_IDS",
    "INTENT_REJECT_TEMPLATES",
    "INTENT_COMPILED",
    "_detect_intent",
]