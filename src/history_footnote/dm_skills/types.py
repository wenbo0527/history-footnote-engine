"""🆕 v2.10.3 dm_skills 数据类型

原 dm_skills.py 第 1-122 行（8 个 SKILL dataclass + DMContext 容器）
单独抽出，方便子模块 import 而不互相依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# SKILL-1 读场判断
# ============================================================

@dataclass
class SceneAssessment:
    """SKILL-1 读场判断"""
    engagement: str = "normal"  # high | normal | low | stuck
    emotion: str = "engaged"     # excited | anxious | bored | confused | engaged
    tension: str = "medium"      # high | medium | low
    progress: str = "with_leisure"  # near_anchor | with_leisure | past_anchor
    route_tendency: str = ""     # weaving | imperial_exam | leave | monk | tax_resist | business | ...
    deviation: str = "normal"    # normal | slight | serious | stuck
    idle_rounds: int = 0         # 连续空转回合数
    player_input_length: int = 0
    need_correction: bool = False
    correction_type: str = ""    # npc_visit | new_event | lead_supplement | sharp_cut_back
    notes: str = ""


@dataclass
class PacingDecision:
    """SKILL-2 节奏控制"""
    time_mode: str = "now_time"  # slow_time | now_time | abstract_time | sharp_cut
    detail_level: int = 3         # 1-5
    internal_monologue: bool = False
    values_voice: bool = False
    correction_needed: bool = False
    correction_type: str = ""
    rationale: str = ""
    time_span: str = "半天"       # 1回合对应的游戏时间


@dataclass
class LeadPlan:
    """SKILL-3 线索投放"""
    lead_type: str = ""           # push | guide | reveal | pressure
    lead_content: str = ""        # 线索内容
    delivery_method: str = ""     # npc_chat | environment | search | gossip
    target_route: str = ""        # 这条线索推向哪个方向


@dataclass
class HistoricalAnchor:
    """SKILL-4 史实锚定"""
    anchor_id: str = ""
    trigger_date: str = ""        # 史实锚点日期
    description: str = ""
    time_mode: str = "now_time"   # 这个锚点应该用什么时间模式
    foreshadowing_lead: str = ""  # 铺垫阶段用什么线索
    dm_instruction: str = ""      # DM 触发时的具体指令
    triggered: bool = False


@dataclass
class VoiceActivation:
    """SKILL-5 价值观发声"""
    voice_id: str = ""
    voice_name: str = ""
    intensity: int = 1            # 1-5，等级越高发声越强
    expression: str = ""          # 实际发出的"声音"内容


@dataclass
class FailureNarrative:
    """SKILL-6 失败叙事化"""
    failure_type: str = ""        # action | persuasion | exploration | choice
    conversion: str = ""          # 失败转化为新故事
    new_path: str = ""            # 失败后开启的路径


@dataclass
class ThreeLayerVerdict:
    """SKILL-7 三层裁判"""
    layer: str = "free"           # iron | plausible | free
    verdict: str = "allow"        # allow | reject_narratively | force_event
    narrative_constraint: str = ""  # 叙事化约束的描述


@dataclass
class CognitiveFrame:
    """SKILL-8 认知框架锁定"""
    frame_id: str = ""            # weaving | imperial_exam | business | monk | ...
    highlight: list[str] = field(default_factory=list)  # 突出呈现的信息类型
    suppress: list[str] = field(default_factory=list)   # 自然抑制的信息类型


@dataclass
class DMContext:
    """所有 SKILL 的综合结果"""
    scene: SceneAssessment = field(default_factory=SceneAssessment)
    pacing: PacingDecision = field(default_factory=PacingDecision)
    lead: LeadPlan | None = None
    historical: HistoricalAnchor | None = None
    voices: list[VoiceActivation] = field(default_factory=list)
    failure: FailureNarrative | None = None
    three_layer: ThreeLayerVerdict | None = None
    cognitive_frame: CognitiveFrame | None = None
    skill_directive: str = ""  # 综合注入到 LLM 的指令