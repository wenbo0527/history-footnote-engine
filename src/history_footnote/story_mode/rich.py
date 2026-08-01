"""🆕 v2.10.17 Phase 11 — 丰富度引擎

提供:
- NarrativeSection: 多声部段落（旁白 / NPC / 内心独白 / 音效）
- EnvironmentContext: 季节/天气/时辰/城市场景
- 环境模板注入（自动丰富 narrative）
- 随机事件 + D&D 检定（重玩价值）
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class NarrativeSection:
    """一段叙事，可属于不同声部"""
    narrator: str           # "旁白" / "张氏" / "父亲" / "钱老板" / "母亲" / "张叔" / "周大娘"
    text: str               # 文本
    emotion: str = ""       # "忧" / "喜" / "怒" / "哀" / "平静" / "假笑"
    sound: str = ""         # 音效/拟声: "咳嗽" / "算盘响" / "婴儿啼"
    action: str = ""        # 动作: "攥紧借据" / "叹气" / "转身"
    italic: bool = False    # 斜体（内心独白用）


@dataclass
class EnvironmentContext:
    """当前环境"""
    season: str = "春"          # 春/夏/秋/冬
    month: int = 3              # 1-12
    weather: str = "晴"         # 晴/雨/阴/雪/雾
    hour: str = "辰时"          # 古代时辰
    city: str = "shengze"
    city_chinese: str = "盛泽镇"

    def env_label(self) -> str:
        return f"【{self.season}季·{self.weather}·{self.city_chinese}·{self.hour}】"


# ============================================================
# 环境描写模板 (按 season x weather x city 索引)
# ============================================================

ENV_TEMPLATES: dict[tuple[str, str, str], list[str]] = {
    # ===== 春季 =====
    ("春", "晴", "shengze"): [
        "春阳和煦，桑芽初绿。盛泽镇东河埠头泊着几条乌篷船。",
        "春风拂过屋脊的瓦当，远处的织机声此起彼伏。",
        "油菜花金黄一片，蜜蜂嗡嗡，织工们趁着好天气浆洗纱罗。",
    ],
    ("春", "雨", "shengze"): [
        "春雨蒙蒙，盛泽镇的青石板路上积着浅浅的水洼。",
        "细雨打在桑叶上，远处的绸庄屋檐下挂着水珠。",
        "雨雾中，盛泽镇的石桥如一道墨痕，织坊里却灯火通明赶织春绸。",
    ],
    ("春", "阴", "shengze"): [
        "春云低垂，盛泽镇的河面上漂着薄雾，织机声在雾气中闷响。",
    ],
    ("春", "雾", "shengze"): [
        "晨雾未散，盛泽镇笼罩在一片乳白中。桥下的乌篷船像悬浮在云里。",
    ],

    # ===== 夏季 =====
    ("夏", "晴", "shengze"): [
        "夏日炎炎，盛泽镇的河埠头有孩子在戏水，蝉鸣声声。",
        "午后的阳光烤得青石板发烫，织工们在棚下摇扇，蚕室却要闷热加湿。",
    ],
    ("夏", "雨", "shengze"): [
        "夏雨急促，盛泽镇的瓦檐下挂着水帘，远处的雷声隆隆。",
    ],

    # ===== 秋季 =====
    ("秋", "晴", "shengze"): [
        "秋高气爽，盛泽镇的桑叶转黄，织工们赶织秋罗，牙行的秤砣叮当响。",
        "秋风送来桂花香，盛泽镇的绸庄门前堆着成匹的纱罗。",
    ],
    ("秋", "阴", "shengze"): [
        "秋阴沉沉的，盛泽镇的街上人少，织工们在家中赶夜工。",
    ],

    # ===== 冬季 =====
    ("冬", "晴", "shengze"): [
        "冬日惨淡，盛泽镇的河面结了一层薄冰，织工们围着炭盆搓手。",
        "雪后初晴，盛泽镇屋檐挂着冰凌，呼出的气化作白雾。",
    ],
    ("冬", "雪", "shengze"): [
        "大雪纷纷，盛泽镇的桥上积着厚雪，织工们在暖阁里赶织冬绸。",
    ],

    # ===== 苏州 =====
    ("春", "晴", "suzhou"): [
        "苏州阊门码头人声鼎沸，绸缎牙行鳞次栉比。",
        "春雨初霁，苏州山塘街的画舫缓缓驶过，河岸茶馆里飘出评弹声。",
    ],
    ("春", "雨", "suzhou"): [
        "春雨绵绵，苏州观前街的行人撑着油纸伞，绸缎铺的柜台前挤满买家。",
    ],
    ("夏", "晴", "suzhou"): [
        "夏日午后，苏州织造署前的石狮子被晒得发烫，绸缎铺里凉茶飘香。",
    ],
    ("秋", "晴", "suzhou"): [
        "秋阳明媚，苏州虎丘的山路上游人如织，绸缎铺的招牌在风中摇晃。",
    ],
    ("冬", "雪", "suzhou"): [
        "苏州城大雪，织造署前的衙役搓手跺脚，远处的寒山寺钟声悠悠。",
    ],
}


def random_env_phrase(env: EnvironmentContext) -> str:
    """随机取一个环境描写"""
    key = (env.season, env.weather, env.city)
    candidates = ENV_TEMPLATES.get(key) or ENV_TEMPLATES.get((env.season, "晴", env.city)) or [
        f"{env.season}季的{env.city_chinese}，时光静静流淌。"
    ]
    return random.choice(candidates)


# ============================================================
# 模板变量替换
# ============================================================

@dataclass
class TemplateEngine:
    """模板引擎: 支持 {var} 替换 + 条件块 {?flag}...{/flag}"""

    # state → 变量
    state: dict[str, Any] = field(default_factory=dict)

    def render(self, template: str) -> str:
        # 1. 替换变量 {var}
        def repl(m: re.Match) -> str:
            key = m.group(1)
            val = self._resolve(key)
            return str(val) if val is not None else ""

        text = re.sub(r"\{([\w_.|]+)\}", repl, template)

        # 2. 条件块 {?flag}...{/flag}
        text = self._render_conditional(text)

        # 3. 清理空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _resolve(self, key: str) -> Any:
        # 支持 a.b.c 嵌套
        parts = key.split(".")
        v: Any = self.state
        for p in parts:
            if isinstance(v, dict):
                v = v.get(p)
            else:
                v = getattr(v, p, None)
            if v is None:
                return None
        return v

    def _render_conditional(self, text: str) -> str:
        # {?flag}...{/flag} — 仅当 flag 存在时保留
        def repl(m: re.Match) -> str:
            cond = m.group(1)
            body = m.group(2)
            if cond.startswith("!"):
                # {!flag} — 当 flag 不存在
                flag = cond[1:]
                return "" if self._has_flag(flag) else body
            return body if self._has_flag(cond) else ""

        return re.sub(r"\{(\!?[\w_]+)\}(.*?)\{/\1\}", repl, text, flags=re.DOTALL)

    def _has_flag(self, flag: str) -> bool:
        flags = self.state.get("scripted_flags") or []
        return flag in flags


# ============================================================
# 随机事件 + D&D 检定
# ============================================================

@dataclass
class RandomEncounter:
    """一个随机事件"""
    encounter_id: str
    name: str
    description: str

    # 触发条件
    trigger_round_min: int = 1
    trigger_round_max: int = 999
    trigger_flags: list[str] = field(default_factory=list)
    trigger_city: Optional[str] = None
    probability: float = 0.3   # 基础触发概率

    # D&D 检定 (可选)
    check_attribute: Optional[str] = None  # "luck" / "charisma" / "skill"
    check_difficulty: int = 10             # d20 + attr >= difficulty

    # 三档结果 (叙事 + 效果)
    great_success_sections: list[NarrativeSection] = field(default_factory=list)
    success_sections: list[NarrativeSection] = field(default_factory=list)
    fail_sections: list[NarrativeSection] = field(default_factory=list)

    great_success_effects: dict[str, Any] = field(default_factory=dict)
    success_effects: dict[str, Any] = field(default_factory=dict)
    fail_effects: dict[str, Any] = field(default_factory=dict)


def roll_d20() -> int:
    """D&D d20 检定"""
    return random.randint(1, 20)


def perform_check(attr_value: int, difficulty: int = 10) -> tuple[str, int]:
    """返回 (结果档位, d20值)"""
    d20 = roll_d20()
    total = d20 + attr_value
    if total >= difficulty + 8:
        return "great_success", d20
    elif total >= difficulty:
        return "success", d20
    else:
        return "fail", d20


def maybe_trigger_encounter(
    encounters: list[RandomEncounter],
    state: dict,
    round_num: int,
) -> Optional[RandomEncounter]:
    """根据 state + round 检查是否触发"""
    for e in encounters:
        if not (e.trigger_round_min <= round_num <= e.trigger_round_max):
            continue
        if e.trigger_city and state.get("city") != e.trigger_city:
            continue
        if e.trigger_flags:
            flags = state.get("scripted_flags") or []
            if not all(f in flags for f in e.trigger_flags):
                continue
        if random.random() < e.probability:
            return e
    return None