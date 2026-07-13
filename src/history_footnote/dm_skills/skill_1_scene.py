"""🆕 v2.10.3 SKILL-1 读场判断（原 dm_skills.py 第 125-329 行）

感知玩家当前状态：投入度 / 情绪 / 张力 / 进度 / 路线倾向 / 偏离程度。
"""
from __future__ import annotations

from history_footnote.dm_skills.types import SceneAssessment


# 路线关键词库（被 director/其他 skill 复用）
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