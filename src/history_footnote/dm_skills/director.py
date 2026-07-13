"""🆕 v2.10.3 dm_skills 综合调度（原 dm_skills.py 第 1005-1229 行）

- run_all_skills — 跑完 8 个 SKILL，汇总为 DMContext
- _build_skill_directive — 把 DMContext 序列化成 prompt 指令
- run_dm_skills — v1.3 兼容旧接口（dict 格式）
- _detect_intent_type — DE 风格意图识别
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from history_footnote.dm_skills.skill_1_scene import skill_1_assess_scene
from history_footnote.dm_skills.skill_2_pacing import TIME_MODES, skill_2_decide_pacing
from history_footnote.dm_skills.skill_3_lead import skill_3_plan_lead
from history_footnote.dm_skills.skill_4_history import skill_4_anchor_history
from history_footnote.dm_skills.skill_5_voice import skill_5_activate_voices
from history_footnote.dm_skills.skill_6_failure import skill_6_handle_failure
from history_footnote.dm_skills.skill_7_verdict import skill_7_three_layer_verdict
from history_footnote.dm_skills.skill_8_frame import skill_8_lock_cognitive_frame
from history_footnote.dm_skills.types import (
    DMContext,
    FailureNarrative,
    HistoricalAnchor,
    LeadPlan,
    PacingDecision,
    SceneAssessment,
    ThreeLayerVerdict,
    CognitiveFrame,
    VoiceActivation,
)


def run_all_skills(
    player_input: str,
    state: dict,
    era_config: dict,
    recent_scenes: list[str] = None,
    recent_inputs: list[str] = None,
    idle_rounds: int = 0,
    failure_type: str = "",
) -> DMContext:
    """跑完所有 8 个 DM skill，返回综合结果 DMContext

    这是 DM 节点在每次生成前调用的入口。
    """
    recent_scenes = recent_scenes or []
    recent_inputs = recent_inputs or []

    # SKILL-1 读场判断
    assessment = skill_1_assess_scene(
        player_input, state, era_config, recent_scenes, recent_inputs, idle_rounds
    )

    # SKILL-2 节奏控制
    pacing = skill_2_decide_pacing(assessment, era_config, state, player_input)

    # SKILL-3 线索投放
    lead = skill_3_plan_lead(assessment, pacing, era_config, state, player_input)

    # SKILL-4 史实锚定
    historical = skill_4_anchor_history(era_config, state, player_input)

    # SKILL-5 价值观发声
    voices = skill_5_activate_voices(era_config, state, assessment, pacing)

    # SKILL-6 失败叙事化
    failure = skill_6_handle_failure(era_config, state, failure_type) if failure_type else None

    # SKILL-7 三层裁判
    three_layer = skill_7_three_layer_verdict(era_config, player_input, state)

    # SKILL-8 认知框架锁定
    cognitive_frame = skill_8_lock_cognitive_frame(era_config, state)

    # 综合所有结果为 prompt 指令
    skill_directive = _build_skill_directive(
        assessment, pacing, lead, historical, voices, failure, three_layer, cognitive_frame
    )

    return DMContext(
        scene=assessment,
        pacing=pacing,
        lead=lead,
        historical=historical,
        voices=voices,
        failure=failure,
        three_layer=three_layer,
        cognitive_frame=cognitive_frame,
        skill_directive=skill_directive,
    )


def _build_skill_directive(
    assessment: SceneAssessment,
    pacing: PacingDecision,
    lead: LeadPlan | None,
    historical: HistoricalAnchor | None,
    voices: list[VoiceActivation],
    failure: FailureNarrative | None,
    three_layer: ThreeLayerVerdict,
    cognitive_frame: CognitiveFrame | None,
) -> str:
    """把所有 8 个 SKILL 结果汇总成一个 prompt 指令"""
    parts = []

    # === SKILL-1 读场判断 ===
    parts.append(f"\n## 📊 SKILL-1 读场判断")
    parts.append(f"  投入度: {assessment.engagement} | 情绪: {assessment.emotion} | 张力: {assessment.tension}")
    parts.append(f"  进度: {assessment.progress} | 路线倾向: {assessment.route_tendency or '未明'}")
    if assessment.deviation != "normal":
        parts.append(f"  ⚠️ 偏离程度: {assessment.deviation}（空转{assessment.idle_rounds}回合）")
        if assessment.need_correction:
            parts.append(f"  → 需要『扶正』：{assessment.correction_type}")

    # === SKILL-2 节奏控制 ===
    mode_info = TIME_MODES.get(pacing.time_mode, TIME_MODES["now_time"])
    parts.append(f"\n## ⏱️ SKILL-2 节奏控制 → {pacing.time_mode}")
    parts.append(f"  {mode_info['description']}")
    parts.append(f"  时间跨度: {pacing.time_span}")
    parts.append(f"  细节等级: {pacing.detail_level}/5")
    if pacing.internal_monologue:
        parts.append(f"  → 插入内心独白")
    if pacing.values_voice:
        parts.append(f"  → 触发价值观发声")
    parts.append(f"  DM 行为: {mode_info['dm_behavior']}")
    if pacing.correction_needed:
        parts.append(f"  → 扶正机制：{pacing.correction_type}")

    # === SKILL-3 线索投放 ===
    if lead:
        parts.append(f"\n## 🪝 SKILL-3 线索投放")
        parts.append(f"  类型: {lead.lead_type} | 方式: {lead.delivery_method}")
        parts.append(f"  线索内容: {lead.lead_content}")

    # === SKILL-4 史实锚定 ===
    if historical:
        parts.append(f"\n## 📜 SKILL-4 史实锚定")
        if historical.foreshadowing_lead:
            parts.append(f"  📍 阶段：铺垫")
            parts.append(f"  锚点: {historical.description}")
            parts.append(f"  铺垫线索: {historical.foreshadowing_lead}")
        else:
            parts.append(f"  📍 阶段：触发")
            parts.append(f"  锚点: {historical.description}")
            parts.append(f"  时间模式: {historical.time_mode}")
            parts.append(f"  DM 指令: {historical.dm_instruction}")

    # === SKILL-5 价值观发声 ===
    if voices:
        parts.append(f"\n## 🎭 SKILL-5 价值观发声（{len(voices)}个声音）")
        for v in voices:
            strength = "弱" if v.intensity <= 2 else "中" if v.intensity <= 4 else "强"
            parts.append(f"  [{strength}] {v.voice_name}（强度{v.intensity}/5）：{v.expression}")

    # === SKILL-6 失败叙事化 ===
    if failure:
        parts.append(f"\n## 💔 SKILL-6 失败叙事化")
        parts.append(f"  失败类型: {failure.failure_type}")
        parts.append(f"  转化方向: {failure.conversion}")

    # === SKILL-7 三层裁判 ===
    parts.append(f"\n## ⚖️ SKILL-7 三层裁判")
    parts.append(f"  层级: {three_layer.layer} | 判定: {three_layer.verdict}")
    if three_layer.narrative_constraint:
        parts.append(f"  叙事化约束: {three_layer.narrative_constraint}")

    # === SKILL-8 认知框架锁定 ===
    if cognitive_frame:
        parts.append(f"\n## 🔍 SKILL-8 认知框架锁定 → {cognitive_frame.frame_id}")
        if cognitive_frame.highlight:
            parts.append(f"  突出呈现: {', '.join(cognitive_frame.highlight)}")
        if cognitive_frame.suppress:
            parts.append(f"  自然抑制: {', '.join(cognitive_frame.suppress)}")

    parts.append(f"\n## 📌 综合指令")
    parts.append(f"  本回合采用【{pacing.time_mode}】，写作时请按上述所有 SKILL 指令调整。")
    parts.append(f"  **核心原则**：失败不是终点，是岔路口；让玩家有'走进这个时代'的体验。")

    # 🆕 v1.6.7 P0 Bug 修复：明确禁止 LLM 把 SKILL 指令复制到 narrative
    parts.append(f"\n## ⚠️ 关键禁忌")
    parts.append(f"  **绝对不要**将本 SKILL 指令中的任何内容（包括 '## ⏱️ SKILL-X'、'## 📌 综合指令' 等）")
    parts.append(f"  复制或粘贴到 narrative 字段。narrative 字段必须是给玩家看的具体场景描写，")
    parts.append(f"  不能包含 '=== COMPILED SKILLS ==='、'Decision Mode:'、'Applied Skills' 等元数据。")

    return "\n".join(parts)


def _detect_intent_type(player_input: str) -> str:
    """检测玩家输入意图类型（v1.5+ DE 风格）

    返回值：action | inquire | describe | voice
    """
    text = player_input.strip()
    if not text:
        return "action"

    # 1️⃣ describe：玩家描述身份/环境/性格/来历（最高优先）
    describe_prefixes = ["我是", "我叫", "我来自", "我住在", "我所在", "我是个", "我家", "我这"]
    describe_strong_kw = ["我的身份", "我的性格", "我这人", "我这人性子", "我这个人"]
    if any(text.startswith(prefix) for prefix in describe_prefixes):
        return "describe"
    if any(kw in text[:20] for kw in describe_strong_kw):
        return "describe"

    # 2️⃣ inquire：问询/观察（中等优先）
    inquire_strong = ["看看", "听听", "瞧瞧", "环顾", "环视", "打听", "问路"]
    inquire_ask = ["问问", "问一", "请问", "问："]
    if any(kw in text for kw in inquire_strong) or any(kw in text for kw in inquire_ask):
        # 但如果同一句话也包含真正的强动作（织/卖/纳/建/搬等），则按 action
        # 注："去/走/跑"不算强动作——它们常被用作虚词（"我去看看"）
        real_action = ["织", "卖", "买", "纳", "交", "收", "建", "造", "修", "借", "还", "搬", "挖", "砍"]
        if not any(akw in text for akw in real_action):
            return "inquire"

    # 3️⃣ action（默认）
    return "action"


# 兼容旧接口（v1.3 时的）
def run_dm_skills(player_input: str, state: dict, era_config: dict, recent_scenes: list[str] | None = None) -> dict[str, Any]:
    """兼容旧接口，返回 dict"""
    ctx = run_all_skills(player_input, state, era_config, recent_scenes or [])

    # 包装成旧格式
    return {
        "pacing": {
            "pacing": ctx.pacing.time_mode,
            "detail_level": ctx.pacing.detail_level,
            "rationale": ctx.pacing.rationale,
            "should_linger": ctx.pacing.time_mode == "slow_time",
            "player_engagement": {"high": 0.9, "normal": 0.6, "low": 0.3, "stuck": 0.2}.get(ctx.scene.engagement, 0.5),
        },
        "action": {
            "is_action": not any(kw in player_input for kw in ["看看", "听听", "问"]),
            "time_cost": 1,
            "exhaustion": "none",
            "intent_type": _detect_intent_type(player_input),
            "rationale": "v1.4 兼容",
        },
        "scene": {
            "scene": "未分类",
            "matched_keywords": [],
            "is_new_scene": False,
            "should_linger": ctx.pacing.time_mode == "slow_time",
            "suggested_pacing": ctx.pacing.time_mode,
        },
        "active_voices": [asdict(v) for v in ctx.voices],
        "voices_prompt": "\n".join([v.expression for v in ctx.voices]),
        "skill_directive": ctx.skill_directive,
        "dm_context": asdict(ctx),  # 新格式
    }