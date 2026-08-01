"""🆕 v2.10.24 — 故事模式常量

集中所有 magic string / 数字常量，避免散落各处
"""
from __future__ import annotations


# ============================================================
# D&D 检定常量
# ============================================================

# 三档结果
CHECK_RESULT_GREAT = "great_success"
CHECK_RESULT_SUCCESS = "success"
CHECK_RESULT_FAIL = "fail"

VALID_CHECK_RESULTS = {CHECK_RESULT_GREAT, CHECK_RESULT_SUCCESS, CHECK_RESULT_FAIL}

# D&D DC: total = d20 + attr; DC = 10 + value * 2
# value=2 → DC=14, value=3 → DC=16, value=4 → DC=18
DC_BASE = 10
DC_PER_VALUE = 2

# D&D 检定档位阈值 (great_success 比 success 高 8)
TIER_GREAT_BONUS = 8


# ============================================================
# 属性 + 加成 flag
# ============================================================

# 抽象属性默认值
ABSTRACT_ATTR_BASE = 2

# 各抽象属性的加成 flag
ATTR_MOD_FLAGS = {
    "charisma": ["zhou_favor", "met_big_merchant", "knew_color_master"],
    "skill": ["master_dyer", "learned_qixia", "knew_scale_trick"],
    "luck": ["has_debt", "sold_loom", "lone_warrior"],
    "courage": ["joined_resistance", "led_resistance", "lone_warrior"],
}

# 资源类属性 (硬性检查, 无 d20)
RESOURCE_ATTRS = {"cash", "rice", "debt", "looms", "stamina"}

# 所有支持的属性
ALL_ATTRS = set(ATTR_MOD_FLAGS.keys()) | RESOURCE_ATTRS


# ============================================================
# State 字段 (从 types.py 搬过来)
# ============================================================

SCRIPTED_STATE_KEYS = {
    "scripted_mode": False,
    "scripted_chapter_id": 0,
    "scripted_node_id": "",
    "scripted_flags": [],
    "scripted_visits": [],
    "scripted_chapter_complete": False,
}


# ============================================================
# 章节元信息 (前端用)
# ============================================================

CHAPTER_INFO = {
    1: {
        "title": "家贫",
        "subtitle": "万历十五年三月 · 盛泽镇",
        "description": "父亲病重、债台初筑、织工小子在江南的春日抉择。",
        "theme": "抉择 / 求生",
        "estimated_minutes": 10,
    },
    2: {
        "title": "织染",
        "subtitle": "万历十五年六月至九月 · 盛泽镇 / 苏州府",
        "description": "苏州订单 · 家庭考验 · 织机扩张 · 染色危机 · 父亲秘密。",
        "theme": "抉择 / 兴衰 / 家庭",
        "estimated_minutes": 15,
    },
    3: {
        "title": "丝绢案",
        "subtitle": "万历十五年九月至次年二月 · 盛泽镇 / 苏州府 / 织造衙门",
        "description": "织造太监采办 · 税关压迫 · 父亲冤案 · 抗税起义。",
        "theme": "抉择 / 政治 / 复仇 / 生死",
        "estimated_minutes": 15,
    },
}


# ============================================================
# 城市
# ============================================================

DEFAULT_CITY = "shengze"
VALID_CITIES = {"shengze", "suzhou", "hangzhou", "nanjing"}


# ============================================================
# Effect 类型
# ============================================================

EFFECT_TYPES_DELTA = {
    "cash_delta", "rice_delta", "debt_delta", "looms_delta",
    "stamina_delta", "round_delta",
}
EFFECT_TYPES_SET = {"flag_set", "city_move"}


# ============================================================
# Chapter role
# ============================================================

ROLES = {"intro", "escalation", "climax", "resolution"}