"""DM 公共技能（DM Public Skills）— v1.4.0

设计灵感来自：
- Disco Elysium 的「24 技能 = 24 脑海中的声音」+ 「思想内阁」+ 「主动/被动检定」
- 剧本杀 DM 控场方法论（节奏、线索、扶正）
- DND 四种时间模式（Robin D. Laws）：慢时间/现在时间/抽象时间/锐切

8 个核心 SKILL：
场控层：SKILL-1 读场判断 / SKILL-2 节奏控制 / SKILL-3 线索投放
叙事层：SKILL-4 史实锚定 / SKILL-5 价值观发声 / SKILL-6 失败叙事化
约束层：SKILL-7 三层裁判 / SKILL-8 认知框架锁定

这些 skill 是**与时代包无关**的通用能力，AI DM 必须在每次生成时调用。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================
# 数据结构
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


# ============================================================
# SKILL-1 读场判断
# ============================================================

ROUTE_KEYWORDS = {
    "imperial_exam": [
        # 科举相关
        "科举", "考试", "秀才", "举人", "进学", "书院", "经义", "读书", "诗", "文章", "考",
        "乡试", "会试", "府学", "县学", "院试", "殿试", "进士", "解元", "生员",
        "儒学", "秀才相公", "李秀才", "范进", "孔孟", "圣贤书", "笔砚", "墨", "纸",
        "私塾", "蒙童", "束脩", "教席", "学问", "文曲星", "八股", "制艺",
    ],
    "monk": [
        "出家", "当和尚", "佛寺", "寺里", "剃头", "了却尘缘", "和尚", "佛门",
        "出家当", "法号", "受戒", "僧人", "禅寺", "庵", "道观", "玄奘", "和尚庙",
        "削发", "遁入空门", "出家修行", "了断尘缘", "皈依", "晨钟暮鼓",
        "剃度", "披剃", "落发", "沙弥", "比丘", "佛堂", "香火", "念经", "打坐",
    ],
    "leave": [
        "离开", "逃", "去苏州", "去杭州", "去南京", "投亲", "逃难", "去城里",
        "去上海", "去北京", "走他乡", "出门", "北上", "南行", "远走", "走亲戚",
        "投奔", "逃荒", "避乱", "远行",
    ],
    "tax_resist": [
        "不交税", "抗税", "逃税", "告状", "鼓动", "反", "起义", "民变",
        "逼税", "官逼民反", "拒不缴纳", "税银", "加派", "辽饷", "剿饷",
        "练饷", "矿监", "税监", "逼反", "齐民", "罢市", "聚众",
    ],
    "business": [
        "做买卖", "扩大", "加机", "雇工", "牙行", "客户", "订单", "做批",
        "开铺", "铺子", "货款", "本金", "翻本", "投资", "入股", "分利",
        "商人", "学徒", "伙计", "掌柜", "进货", "出货", "行商", "坐贾",
        "行会", "商帮", "票号", "当铺", "典当",
    ],
    "weaving": [
        "织", "织机", "络丝", "缫丝", "上机", "落机",
        "经线", "纬线", "梭子", "丝线", "生丝", "熟丝", "桑叶", "蚕",
        "桑田", "蚕种", "织女", "湖绫", "绢", "绸", "缎", "罗",
        "丝织", "织造", "上机", "落机", "挑花", "提花",
    ],
}


def _assess_engagement(player_input: str, recent_scenes: list[str], idle_rounds: int) -> tuple[str, int]:
    """判断玩家投入度"""
    length = len(player_input)
    # 优先检查空转/重复（不管长度）
    if idle_rounds >= 3:
        return "stuck", length
    if recent_scenes and len(recent_scenes) >= 2 and recent_scenes[-1] == recent_scenes[-2]:
        return "stuck", length
    # 然后按长度判断
    if length > 50:
        return "high", length
    if length < 10:
        return "low", length
    return "normal", length


def _assess_emotion(player_input: str) -> str:
    """判断玩家情绪"""
    anxious_kw = ["怎么办", "怎么", "愁", "怕", "不敢", "急"]
    excited_kw = ["好", "想", "试", "走", "去", "冲", "赶"]
    bored_kw = ["无聊", "没意思", "算了", "再说"]
    confused_kw = ["不知道", "什么", "咦", "嗯"]
    if any(kw in player_input for kw in anxious_kw):
        return "anxious"
    if any(kw in player_input for kw in excited_kw):
        return "excited"
    if any(kw in player_input for kw in bored_kw):
        return "bored"
    if any(kw in player_input for kw in confused_kw):
        return "confused"
    return "engaged"


def _assess_route_tendency(player_input: str, recent_inputs: list[str]) -> str:
    """判断玩家路线倾向"""
    all_text = " ".join([player_input] + recent_inputs[-3:])
    scores = {}
    for route, kws in ROUTE_KEYWORDS.items():
        scores[route] = sum(1 for kw in kws if kw in all_text)
    if not scores:
        return ""
    return max(scores, key=scores.get) if max(scores.values()) > 0 else ""


def _detect_anchors_near(era_config: dict, current_date: str, current_round: int, triggered_events: list = None) -> tuple[str, list[dict]]:
    """检查是否有史实锚点临近

    Bug #1+#2 修复：合并 historical_events + pacing_anchors，且排除已触发
    """
    triggered_events = triggered_events or []
    custom_anchors = era_config.get("world", {}).get("pacing_anchors", []) or era_config.get("pacing_anchors", [])
    raw_events = era_config.get("mechanics", {}).get("historical_events", [])

    # 派生锚点（与 skill_4 一致）
    derived_anchors = []
    for ev in raw_events:
        ev_id = ev.get("event_id", "")
        if any(a.get("id") == ev_id for a in custom_anchors):
            continue
        derived_anchors.append({
            "id": ev_id,
            "trigger_round": ev.get("round", 0),
        })

    anchors = custom_anchors + derived_anchors
    near_anchors = []
    if not current_date:
        return "with_leisure", near_anchors

    # ⚠️ Bug #2 修复：已触发的锚点排除
    for anchor in anchors:
        anchor_id = anchor.get("id", "")
        if anchor_id in triggered_events:
            continue  # 已触发过，不再"near"
        trigger_round = anchor.get("trigger_round", 0)
        if current_round >= trigger_round and current_round <= trigger_round + 3:
            near_anchors.append(anchor)
        elif trigger_round - current_round <= 3 and trigger_round > current_round:
            # 即将触发（铺垫阶段）→ 也算 near_anchor
            near_anchors.append(anchor)

    if near_anchors:
        return "near_anchor", near_anchors
    return "with_leisure", near_anchors


def skill_1_assess_scene(
    player_input: str,
    state: dict,
    era_config: dict,
    recent_scenes: list[str],
    recent_inputs: list[str] = None,
    idle_rounds: int = 0,
) -> SceneAssessment:
    """SKILL-1 读场判断：感知玩家当前状态

    6 个判断维度：
    - 投入度：engagement
    - 情绪状态：emotion
    - 叙事张力：tension（基于 player_idle_rounds 反推）
    - 进度位置：progress
    - 路线倾向：route_tendency
    - 偏离程度：deviation
    """
    recent_inputs = recent_inputs or []

    # 1. 投入度
    engagement, input_length = _assess_engagement(player_input, recent_scenes, idle_rounds)

    # 2. 情绪
    emotion = _assess_emotion(player_input)

    # 3. 张力
    if idle_rounds >= 3:
        tension = "low"
    elif engagement == "high" and "!" in player_input or "！" in player_input:
        tension = "high"
    else:
        tension = "medium"

    # 4. 进度
    progress, near_anchors = _detect_anchors_near(
        era_config,
        state.get("current_date", ""),
        state.get("round_number", 1),
        triggered_events=state.get("triggered_events", []),
    )

    # 5. 路线倾向
    route_tendency = _assess_route_tendency(player_input, recent_inputs)

    # 6. 偏离
    deviation = "normal"
    need_correction = False
    correction_type = ""
    if engagement == "stuck":
        deviation = "stuck"
        need_correction = True
        correction_type = "new_event"  # 抽象时间+新事件
    elif input_length < 5 and idle_rounds >= 1:
        deviation = "slight"
        need_correction = False
    elif emotion == "confused" and idle_rounds >= 2:
        deviation = "serious"
        need_correction = True
        correction_type = "npc_visit"  # NPC主动上门

    return SceneAssessment(
        engagement=engagement,
        emotion=emotion,
        tension=tension,
        progress=progress,
        route_tendency=route_tendency,
        deviation=deviation,
        idle_rounds=idle_rounds,
        player_input_length=input_length,
        need_correction=need_correction,
        correction_type=correction_type,
        notes=f"近场:{','.join(recent_scenes[-3:])}" if recent_scenes else "",
    )


# ============================================================
# SKILL-2 节奏控制
# ============================================================

TIME_MODES = {
    "slow_time": {
        "description": "慢时间：关键时刻放慢",
        "time_span": "1刻钟~1时辰",
        "dm_behavior": "逐句描写+内心独白+价值观发声；不急于推进；可能一个行动拆2-3回合",
    },
    "now_time": {
        "description": "现在时间：正常推进",
        "time_span": "半天",
        "dm_behavior": "正常回应+环境描写；推进半天时间",
    },
    "abstract_time": {
        "description": "抽象时间：快速跳过",
        "time_span": "数天~数月",
        "dm_behavior": "一句话跳过数天；只汇报关键变化；检查是否有新事件",
    },
    "sharp_cut": {
        "description": "锐切：突然切入",
        "time_span": "瞬间切换",
        "dm_behavior": "无过渡直接切入；制造紧迫感；不给玩家准备时间",
    },
}


def skill_2_decide_pacing(
    assessment: SceneAssessment,
    era_config: dict,
    state: dict,
    player_input: str,
) -> PacingDecision:
    """SKILL-2 节奏控制：根据读场结果选择时间模式

    决策树（按优先级）：
    1. 锐切：史实锚点触发
    2. 抽象时间：玩家空转/停滞（最高优先——必须扶正）
    3. 慢时间：高张力+高投入（重大抉择）
    4. 慢时间：玩家主动探索
    5. 现在时间：默认
    """
    # 1. 锐切触发：检查史实锚点（仅当锚点已到达 trigger_round）
    if assessment.progress == "near_anchor":
        for anchor in (era_config.get("world", {}).get("pacing_anchors", []) or era_config.get("pacing_anchors", [])):
            current_round = state.get("round_number", 1)
            trigger_round = anchor.get("trigger_round", 0)
            if anchor.get("time_mode") == "sharp_cut" and current_round >= trigger_round:
                return PacingDecision(
                    time_mode="sharp_cut",
                    detail_level=5,
                    internal_monologue=True,
                    values_voice=False,
                    correction_needed=False,
                    rationale=f"史实锚点『{anchor.get('description', '')}』触发 → 锐切",
                    time_span="瞬间切换",
                )

    # 2. 抽象时间：玩家陷入重复/停滞（最高优先——必须扶正）
    if assessment.deviation == "stuck" or assessment.engagement == "stuck":
        return PacingDecision(
            time_mode="abstract_time",
            detail_level=2,
            internal_monologue=False,
            values_voice=False,
            correction_needed=True,
            correction_type="new_event",
            rationale=f"玩家空转{assessment.idle_rounds}回合 → 抽象时间跳过+新事件",
            time_span="数天",
        )

    # 3. 慢时间：玩家面临重大抉择
    if assessment.tension == "high" and assessment.engagement == "high":
        return PacingDecision(
            time_mode="slow_time",
            detail_level=5,
            internal_monologue=True,
            values_voice=True,
            correction_needed=False,
            rationale="高投入+高张力 → 慢时间，逐句展开",
            time_span="1刻钟~1时辰",
        )

    # 4. 慢时间：玩家问询/首次进入场景
    inquire_kw = ["看看", "听听", "了解", "打听", "问路"]
    if any(kw in player_input for kw in inquire_kw) and len(player_input) > 5:
        return PacingDecision(
            time_mode="slow_time",
            detail_level=4,
            internal_monologue=False,
            values_voice=False,
            correction_needed=False,
            rationale="玩家主动探索 → 慢时间，给足环境细节",
            time_span="1时辰",
        )

    # 5. 默认：现在时间
    return PacingDecision(
        time_mode="now_time",
        detail_level=3,
        internal_monologue=False,
        values_voice=False,
        correction_needed=assessment.need_correction,
        correction_type=assessment.correction_type,
        rationale="正常推进",
        time_span="半天",
    )


# ============================================================
# SKILL-3 线索投放
# ============================================================

LEAD_TYPES = {
    "push": "推动型：玩家无所事事时",
    "guide": "引导型：玩家跑偏时",
    "reveal": "揭示型：玩家主动探索时",
    "pressure": "压力型：需制造紧迫感时",
}


def skill_3_plan_lead(
    assessment: SceneAssessment,
    pacing: PacingDecision,
    era_config: dict,
    state: dict,
    player_input: str,
) -> LeadPlan | None:
    """SKILL-3 线索投放：在恰当时机释放信息

    4 种线索类型：
    - push（推动型）：玩家无所事事 → NPC闲话/环境变化
    - guide（引导型）：玩家跑偏 → NPC主动提及/巧合
    - reveal（揭示型）：玩家主动探索 → 搜索发现/NPC深谈
    - pressure（压力型）：需制造紧迫感 → 传闻/倒计时
    """
    # 玩家停滞 → 推动型
    if pacing.correction_type == "new_event" or assessment.deviation == "stuck":
        return LeadPlan(
            lead_type="push",
            lead_content="镇上出了件大事 / 邻居来说消息",
            delivery_method="npc_chat",
            target_route="",
        )

    # 玩家跑偏/困惑 → 引导型
    if assessment.deviation == "serious" or assessment.emotion == "confused":
        return LeadPlan(
            lead_type="guide",
            lead_content="王婶说某件事 / 偶遇某人",
            delivery_method="npc_chat",
            target_route="",
        )

    # 锐切/重大抉择 → 压力型
    if pacing.time_mode == "sharp_cut":
        return LeadPlan(
            lead_type="pressure",
            lead_content="税吏三日后到镇 / 矿监来了",
            delivery_method="gossip",
            target_route="",
        )

    # 玩家主动探索 → 揭示型
    if pacing.time_mode == "slow_time" and assessment.engagement == "high":
        return LeadPlan(
            lead_type="reveal",
            lead_content="你发现/听到的细节",
            delivery_method="environment",
            target_route=assessment.route_tendency,
        )

    return None


# ============================================================
# SKILL-4 史实锚定
# ============================================================

def skill_4_anchor_history(
    era_config: dict,
    state: dict,
    player_input: str,
) -> HistoricalAnchor | None:
    """SKILL-4 史实锚定：检查史实锚点 + 决定操作

    三层操作：
    - 铺垫：临近锚点 → 投放线索
    - 触发：到达日期 → 锐切
    - 应对：事件后 → 多选项
    """
    # ⚠️ Bug #1 修复：合并两个机制
    # 1. 优先用 world.pacing_anchors（v1.4.0 SKILL 专用）
    # 2. fallback 用 mechanics.historical_events（v1.0 旧机制，自动派生）
    # 3. 两者通过 anchor_id == event_id 关联
    custom_anchors = era_config.get("world", {}).get("pacing_anchors", []) or era_config.get("pacing_anchors", [])
    raw_events = era_config.get("mechanics", {}).get("historical_events", [])

    # 派生：从 historical_events 转成 pacing_anchors
    derived_anchors = []
    for ev in raw_events:
        ev_id = ev.get("event_id", "")
        # 如果 custom_anchors 已有同 id 配置，跳过（用 custom）
        if any(a.get("id") == ev_id for a in custom_anchors):
            continue
        # 派生
        derived_anchors.append({
            "id": ev_id,
            "trigger_round": ev.get("round", 0),
            "trigger_date": ev.get("date", ""),
            "description": ev.get("event_name", ""),
            "time_mode": "sharp_cut" if ev.get("scope") == "national" else "now_time",
            "foreshadowing_lead": "",
            "dm_instruction": f"按 {ev.get('description', '')} 推进",
            "derived_from": "historical_events",
        })

    anchors = custom_anchors + derived_anchors
    current_round = state.get("round_number", 1)
    triggered_events = state.get("triggered_events", [])

    for anchor in anchors:
        anchor_id = anchor.get("id", "")
        # 已经触发过
        if anchor_id in triggered_events:
            continue

        trigger_round = anchor.get("trigger_round", 0)
        foreshadow_round = anchor.get("foreshadow_round", trigger_round - 3)

        # 已到触发回合
        if current_round >= trigger_round:
            return HistoricalAnchor(
                anchor_id=anchor_id,
                trigger_date=anchor.get("trigger_date", ""),
                description=anchor.get("description", ""),
                time_mode=anchor.get("time_mode", "now_time"),
                dm_instruction=anchor.get("dm_instruction", ""),
                triggered=False,  # 让 LLM 在叙事中触发
            )

        # 临近锚点 → 铺垫阶段
        if current_round >= foreshadow_round:
            return HistoricalAnchor(
                anchor_id=anchor_id,
                trigger_date=anchor.get("trigger_date", ""),
                description=anchor.get("description", ""),
                time_mode="now_time",
                foreshadowing_lead=anchor.get("foreshadowing_lead", ""),
                dm_instruction=f"铺垫：{anchor.get('foreshadowing_lead', '投放相关线索')}",
                triggered=False,
            )

    return None


# ============================================================
# SKILL-5 价值观发声
# ============================================================

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


# ============================================================
# SKILL-6 失败叙事化
# ============================================================

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


# ============================================================
# SKILL-7 三层裁判
# ============================================================

def skill_7_three_layer_verdict(
    era_config: dict,
    player_input: str,
    state: dict,
) -> ThreeLayerVerdict:
    """SKILL-7 三层裁判：判断玩家行为/叙事落在哪一层

    铁律层（iron）：史实明确 → 严格执行
    可然层（plausible）：史实无记载但可能 → 检验
    自由层（free）：玩家个人选择 → 尊重
    """
    # 简化：检查是否触发铁律
    iron_laws = era_config.get("world", {}).get("iron_laws", [])
    for law in iron_laws:
        fact = law.get("fact", "")
        # 任何涉及"皇帝/上朝/视朝"的 iron_law，且玩家说"去京城/见皇帝" → 铁律拒绝
        if any(kw in fact for kw in ["不上朝", "不视朝", "怠政", "皇帝"]) and \
           any(kw in player_input for kw in ["去京城", "见皇帝", "京中", "面圣", "上京"]):
            return ThreeLayerVerdict(
                layer="iron",
                verdict="reject_narratively",
                narrative_constraint=f"用叙事拒绝：你托人递的话，石沉大海。{fact}",
            )

    # 简化：检查身份边界
    identity = state.get("selected_identity", "")
    action_boundaries = era_config.get("world", {}).get("player_identities", {}).get(identity, {}).get("action_boundaries", {})
    cannot_access = action_boundaries.get("cannot_access", [])
    for forbidden in cannot_access:
        if forbidden in player_input:
            return ThreeLayerVerdict(
                layer="plausible",
                verdict="reject_narratively",
                narrative_constraint=f"用时代逻辑拒绝：守门人/官差拦住你，'你是什么人？'",
            )

    # 自由层
    return ThreeLayerVerdict(layer="free", verdict="allow", narrative_constraint="")


# ============================================================
# SKILL-8 认知框架锁定
# ============================================================

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


# ============================================================
# 综合调用接口
# ============================================================

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
