"""🆕 v2.10.3 SKILL-7 三层裁判（原 dm_skills.py 第 796-970 行）

铁律层（iron）/ 可然层（plausible）/ 自由层（free）三层判断玩家行为。

🆕 v1.7.29 修复塌房 5：意图词典 + 哪些身份不能做。
"""
from __future__ import annotations

import re

from history_footnote.dm_skills.types import ThreeLayerVerdict


# 🆕 v1.7.29 修复：意图词典
# 塌房 5：原 cannot_access 用子串匹配，玩家换说法就绕过
# 新方案：定义"行为意图" + 哪些身份不能做
# 每个 intent 是一个正则，匹配到就触发身份铁律

INTENT_PATTERNS = {
    # 科举：织工/商贩/农户不能
    "participate_imperial_exam": [
        r"科举", r"考试", r"考秀才", r"考举人", r"考进士",
        r"进学", r"入学", r"府学", r"县学", r"书院",
        r"考[一-龥]个秀才", r"考[一-龥]个举人",
        r"做秀才", r"当秀才", r"中举", r"中秀才",
    ],
    # 拜见皇帝/上朝：所有百姓不能
    "audience_emperor": [
        r"见皇帝", r"面圣", r"上朝", r"觐见", r"晋见",
        r"求见圣上", r"求见天子", r"叩见皇上",
    ],
    # 军营/参军：普通百姓不能
    "join_army": [
        r"参军", r"从军", r"当兵", r"入伍",
        r"投军", r"进军营",
    ],
    # 告御状/击鼓鸣冤
    "appeal_to_emperor": [
        r"告御状", r"击鼓鸣冤", r"进京告状",
    ],
    # 去京城/边关
    "go_capital": [
        r"去京城", r"上京", r"进京", r"去北京",
        r"去边关", r"出关",
    ],
    # 当和尚/出家：需要明确放弃户籍，不是简单说"当和尚"就允许
    "become_monk": [
        r"出家当和尚", r"出家为僧", r"剃度出家",
        r"落发为僧", r"遁入空门",
    ],
}

# 哪些身份不能做哪些 intent
INTENT_FORBIDDEN_IDS = {
    "participate_imperial_exam": [
        "weaving_male", "weaving_female",
        "merchant_male", "merchant_female",
        "farmer_male", "farmer_female",
        # 秀才理论上可以考举人，所以不在内
    ],
    "audience_emperor": [  # 任何百姓身份
        "weaving_male", "weaving_female",
        "merchant_male", "merchant_female",
        "farmer_male", "farmer_female",
        "scholar_male",  # 秀才也不能见皇帝
    ],
    "join_army": [
        "weaving_male", "weaving_female",
        "merchant_male", "merchant_female",
        "farmer_male", "farmer_female",
    ],
    "appeal_to_emperor": [  # 任何百姓
        "weaving_male", "weaving_female",
        "merchant_male", "merchant_female",
        "farmer_male", "farmer_female",
        "scholar_male",
    ],
    "go_capital": [
        # 限制：单身男性织工/商贩等可能能去，但需要"路引"且朝廷有事不宜
        # 简化：所有农/工/商身份不主动写时也不能
        "weaving_male", "weaving_female",
        "farmer_male", "farmer_female",
    ],
    "become_monk": [
        # 需明确放弃户籍，简化：默认允许（玩家应有主控权）
        # 实际需要：年龄、健康、家庭同意等
    ],
}

# 意图 → 叙事拒绝模板
INTENT_REJECT_TEMPLATES = {
    "participate_imperial_exam": (
        "{narrative}：你被人拦下，'读书人才能入考场，你一个织工/商贩/农户，"
        "连童生都不是，考什么？赶紧回作坊干活。' 明朝科举取士，匠户、商籍、"
        "军籍皆在'不许入试'之列。"
    ),
    "audience_emperor": (
        "{narrative}：你被差役拦住，'你是什么人？京城重地，岂容闲杂人等靠近！'"
    ),
    "join_army": (
        "{narrative}：招募官看了看你，'你这副手无缚鸡之力的样子，还是去织布吧。'"
    ),
    "appeal_to_emperor": (
        "{narrative}：差役把你推开，'你一个织工/商贩/农户，也想告御状？"
        "回去找你们里长！'"
    ),
    "go_capital": (
        "{narrative}：里长说，'你这户籍出不了远门，'路引'还没办呢。'"
    ),
}

# 编译正则（启动时）
INTENT_COMPILED = {}
for intent, patterns in INTENT_PATTERNS.items():
    INTENT_COMPILED[intent] = [re.compile(p) for p in patterns]


def _detect_intent(player_input: str) -> str | None:
    """检测玩家输入的意图

    Returns:
        intent 名称（如 "participate_imperial_exam"）或 None
    """
    for intent, regexes in INTENT_COMPILED.items():
        for rx in regexes:
            if rx.search(player_input):
                return intent
    return None


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
    # 2. 意图铁律层（🆕 v1.7.29 修复塌房 5）
    # 优先于 iron_laws，因为意图层判定更细（"去京城"对商贩可能允许）
    identity = state.get("selected_identity", "")
    intent = _detect_intent(player_input)

    if intent:
        forbidden_ids = INTENT_FORBIDDEN_IDS.get(intent, [])
        if identity in forbidden_ids:
            template = INTENT_REJECT_TEMPLATES.get(intent, "{narrative}")
            return ThreeLayerVerdict(
                layer="plausible",       # 历史制度层
                verdict="reject_narratively",
                narrative_constraint=template.format(narrative="用时代逻辑拒绝"),
            )

    # 1. 铁律层：iron_laws（仅"皇帝"相关铁律，不替代意图层）
    iron_laws = era_config.get("world", {}).get("iron_laws", [])
    for law in iron_laws:
        fact = law.get("fact", "")
        # 任何涉及"皇帝/上朝/视朝"的 iron_law，且玩家说"见皇帝/上朝" → 铁律拒绝
        if any(kw in fact for kw in ["不上朝", "不视朝", "怠政", "皇帝"]) and \
           any(kw in player_input for kw in ["见皇帝", "面圣", "上朝"]):  # 去掉"去京城"（意图层已处理）
            return ThreeLayerVerdict(
                layer="iron",
                verdict="reject_narratively",
                narrative_constraint=f"用叙事拒绝：你托人递的话，石沉大海。{fact}",
            )

    # 3. 兼容旧逻辑：检查 era_config 中的 cannot_access 子串
    # （保留向后兼容，但优先级低于意图识别）
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