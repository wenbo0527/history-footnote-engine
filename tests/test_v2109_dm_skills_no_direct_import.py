"""🆕 v2.10.9 P1-3 dm_skills 内部封装回归测试

约束：外部代码（包括 dm_skills 之外的所有 src/、tests/）禁止直接
引用 `history_footnote.dm_skills.skill_X_*.py` 子模块——必须通过
`history_footnote.dm_skills` 顶层 re-export。

dm_skills 包内部允许直接 import（director.py 等需要组装的代码）。

为什么这条约束重要：
- 防止 dm_skills 内部重构时（比如 skill_2_pacing 拆成两个文件），
  所有调用方都得改路径
- 强制走 __init__.py 的 re-export，让 dm_skills 成为一个"稳定 API"
"""
from __future__ import annotations

import re
from pathlib import Path


def test_no_external_direct_skill_submodule_imports():
    """外部代码不应直接 import dm_skills 的子模块"""
    src_root = Path("src/history_footnote")
    tests_root = Path("tests")

    # 允许直接引用的位置：dm_skills 包内部
    allowed = {src_root / "dm_skills"}

    bad: list[str] = []
    pattern = re.compile(r"^from history_footnote\.dm_skills\.skill_\d+_\w+\s+import")

    for root in [src_root, tests_root]:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            # 跳过 dm_skills 包内部
            if any(py_file.is_relative_to(a) for a in allowed):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    bad.append(f"{py_file}:{i}: {line.strip()}")

    assert not bad, (
        "外部代码不应直接 import dm_skills 的子模块，应通过顶层 re-export：\n"
        + "\n".join(bad)
    )


def test_dm_skills_init_reexports_all_public_skills():
    """dm_skills/__init__.py 必须 re-export 所有 8 个 SKILL 函数"""
    from history_footnote.dm_skills import (
        skill_1_assess_scene,
        skill_2_decide_pacing,
        skill_3_plan_lead,
        skill_4_anchor_history,
        skill_5_activate_voices,
        skill_6_handle_failure,
        skill_7_three_layer_verdict,
        skill_8_lock_cognitive_frame,
    )
    # 全部应是 callable
    for fn in [
        skill_1_assess_scene, skill_2_decide_pacing, skill_3_plan_lead,
        skill_4_anchor_history, skill_5_activate_voices, skill_6_handle_failure,
        skill_7_three_layer_verdict, skill_8_lock_cognitive_frame,
    ]:
        assert callable(fn), f"{fn} 应为 callable"


def test_dm_skills_init_reexports_director_functions():
    """dm_skills/__init__.py 必须 re-export 调度函数"""
    from history_footnote.dm_skills import (
        run_all_skills,
        run_dm_skills,
        _build_skill_directive,
        _detect_intent_type,
    )
    for fn in [run_all_skills, run_dm_skills, _build_skill_directive, _detect_intent_type]:
        assert callable(fn)


def test_dm_skills_init_reexports_types():
    """dm_skills/__init__.py 必须 re-export 9 个数据类型"""
    from history_footnote.dm_skills import (
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
    # 全部应是 class
    for cls in [
        SceneAssessment, PacingDecision, LeadPlan, HistoricalAnchor,
        VoiceActivation, FailureNarrative, ThreeLayerVerdict,
        CognitiveFrame, DMContext,
    ]:
        assert isinstance(cls, type), f"{cls} 应为 class"


def test_dm_skills_init_reexports_constants():
    """dm_skills/__init__.py 必须 re-export 关键常量"""
    from history_footnote.dm_skills import (
        ROUTE_KEYWORDS,
        TIME_MODES,
        INQUIRE_VERBS,
        LEAD_TYPES,
        FAILURE_TYPES,
        INTENT_PATTERNS,
    )
    # 至少是非空
    for c in [ROUTE_KEYWORDS, TIME_MODES, INQUIRE_VERBS, LEAD_TYPES, FAILURE_TYPES, INTENT_PATTERNS]:
        assert c, f"{c} 应为非空"