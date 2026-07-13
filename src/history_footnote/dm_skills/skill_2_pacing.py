"""🆕 v2.10.3 SKILL-2 节奏控制（原 dm_skills.py 第 330-522 行）

根据读场结果选择 4 种时间模式：slow_time / now_time / abstract_time / sharp_cut。
"""
from __future__ import annotations

from history_footnote.dm_skills.types import PacingDecision, SceneAssessment


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


# ============================================================
# 🆕 v1.7.29 辅助：判定玩家是否在"问询"（不是行动）
# ============================================================
# 塌房 4 修复：原代码"含看看/听听+6+字"就判 slow_time，导致"先看看家里情况"也被误判
# 真正的"问询"需要：明确的问询对象 + 问询动词，且不是"自己去"

INQUIRE_VERBS = [
    "问", "打听", "询问", "探听", "查询", "查探",
    "请教", "求教", "讨教", "访问", "拜访", "拜见",
    "聊聊", "谈", "请教",
    "如何", "怎么", "怎样", "怎么着",
]

INQUIRE_OBJECTS = [
    # 人
    "王掌柜", "王癞子", "赵里长", "李秀才", "赵牙人", "牙人",
    "客", "客商", "邻居", "乡亲", "里老",
    # 概念
    "行情", "价", "价儿", "价目", "价钱", "路", "路怎么走",
    "消息", "事", "事儿", "情况", "情形", "现状", "近况",
    "怎么", "如何", "怎么办",
    # 地点
    "镇", "城里", "市集", "茶馆", "牙行",
    "县衙", "苏州", "杭州", "南京", "京城",
]

# 反模式：玩家只是"自己看"，不是"问别人"
SELF_VERBS = [
    "先", "我要", "我准备", "打算", "准备",
    "我去看", "我去瞧", "我去瞅", "我去瞅瞅",
    "我去瞧一瞧", "我去看一看", "我去看看", "我去瞅瞅",
]

# 慢时间应保留的"看"句式（确实是细看）
DETAIL_VERBS = [
    "细看", "细看一遍", "环顾", "环视", "打量", "扫视",
    "端详", "审视", "巡视", "勘察", "观", "凝视",
    "细听", "倾听", "静听", "聆听",
]


def _is_genuine_inquire(player_input: str) -> bool:
    """判定玩家是否在"问询"（而不是自己看/行动）

    规则：
    1. 必须含问询动词（问/打听/请教 等）
    2. 必须有具体对象（人/概念/地点 等）
    3. 不能是"自己看"模式（先看看/我要去看看）

    Returns:
        True = 真问询（慢时间）
        False = 行动/自查（按其他规则判定）
    """
    text = player_input.strip()
    if not text or len(text) < 2:
        return False

    # 反模式：先看看/我准备看看（自查，不问人）
    for sv in SELF_VERBS:
        if sv in text:
            return False

    # 反模式：纯细看（这种走"先看看家里"路线，自己去）
    for dv in DETAIL_VERBS:
        if dv in text:
            return False

    # 必须是 5+ 字（"我问"单字太短）
    if len(text) < 5:
        return False

    # 1. 问询动词命中
    has_verb = any(verb in text for verb in INQUIRE_VERBS)
    if not has_verb:
        return False

    # 2. 问询对象命中
    has_obj = any(obj in text for obj in INQUIRE_OBJECTS)
    return has_obj


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
    # 🆕 v1.7.29 修复：区分"问询"vs"行动"
    # 塌房：旧代码"含看看+6+字"就触发慢时间，导致"先看看家里情况"也被判慢时间
    # 新规则：必须有明确的"问询对象"（人/物/地点 + 问词），且不是"自己去看"
    if _is_genuine_inquire(player_input):
        return PacingDecision(
            time_mode="slow_time",
            detail_level=4,
            internal_monologue=False,
            values_voice=False,
            correction_needed=False,
            rationale="玩家主动问询 → 慢时间，给足环境细节",
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