"""🆕 v1.7.45 Ending System（自由结局 + 多结局）

依据高自由度 RPG 调研：
> 真正优秀的结局，是确定性代码+LLM 叙事结合

设计：
- 8 种结局：盛世商贾 / 小康安稳 / 勉强维持 / 破产流民 / 忠义抗税 / 出海冒险 / 学而优 / 田园归隐
- 每个结局 1 段判定条件（代码）+ 1 段 narrative 模板（LLM/手写）
- check_ending(state) → 触发的结局（最多 1 个）
- 多结局同时触发时优先级排序

数据流：
1. 每轮 game_loop 步骤 7 后调 check_ending
2. 命中结局 → state.ending = {...} + 显示
3. 不命中 → 继续

依据用户洞察：
> 现在游戏支持自由结局和多结局么 → 不支持
> 高自由度 RPG 必须有结局系统
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


_LOG = logging.getLogger("history_footnote.ending_system")


# ============= 结局类型 =============

class EndingType(Enum):
    """8 种结局（按优先级排序：高端 > 中端 > 低端）"""
    # 高端
    MERCHANT_EMPIRE = "merchant_empire"  # 盛世商贾
    SCHOLAR_SUCCESS = "scholar_success"  # 学而优
    OVERSEAS_PIONEER = "overseas_pioneer"  # 出海冒险
    LOYAL_RESIST = "loyal_resist"  # 忠义抗税
    # 中端
    PEACEFUL_FAMILY = "peaceful_family"  # 田园归隐
    COMFORTABLE = "comfortable"  # 小康安稳
    STRUGGLING = "struggling"  # 勉强维持
    # 低端
    BANKRUPT_BEGGAR = "bankrupt_beggar"  # 破产流民


# ============= 结局定义 =============

@dataclass
class EndingCondition:
    """结局触发条件"""
    type: str  # "cash" / "debt" / "event" / "city" / "identity" / "task"
    op: str = ">="  # ">", "<", ">=", "<=", "==", "has"
    value: any = 0

    def evaluate(self, state, triggered_events: list, completed_quests: list) -> bool:
        if self.type == "cash":
            return self._compare(state.cash or 0, self.op, self.value)
        if self.type == "debt":
            return self._compare(state.debt or 0, self.op, self.value)
        if self.type == "rice":
            return self._compare(state.rice or 0, self.op, self.value)
        if self.type == "round":
            return self._compare(state.round_number, self.op, self.value)
        if self.type == "event":
            # triggered_events 是 state.triggered_events
            return self.value in triggered_events
        if self.type == "city":
            return (state.current_city or "") == self.value
        if self.type == "identity":
            identity = getattr(state, "identity", "") or ""
            return identity == self.value or self.value in identity
        if self.type == "task":
            return self.value in [q.get("id") for q in completed_quests]
        if self.type == "debt_zero":
            return (state.debt or 0) == 0
        return False

    def _compare(self, actual, op, target) -> bool:
        if op == ">=":
            return actual >= target
        if op == "<=":
            return actual <= target
        if op == ">":
            return actual > target
        if op == "<":
            return actual < target
        if op == "==":
            return actual == target
        return False


@dataclass
class Ending:
    """结局"""
    type: str  # EndingType.value
    name: str  # 中文名
    icon: str  # emoji
    conditions: list = field(default_factory=list)  # list[EndingCondition] AND 关系
    narrative_template: str = ""  # narrative 模板（手写或 LLM）
    priority: int = 50  # 优先级（数字大优先）
    era_appropriate: bool = True  # 是否适合本时代

    def matches(self, state, triggered_events: list, completed_quests: list) -> bool:
        """所有条件 AND"""
        return all(c.evaluate(state, triggered_events, completed_quests) for c in self.conditions)


# ============= 8 种结局 =============

ENDING_MERCHANT_EMPIRE = Ending(
    type=EndingType.MERCHANT_EMPIRE.value,
    name="盛世商贾",
    icon="🏆",
    conditions=[
        EndingCondition("cash", ">=", 50),
        EndingCondition("debt_zero"),
        EndingCondition("round", ">=", 30),
    ],
    narrative_template=(
        "三十年后，你已是江南首屈一指的大丝绸商。从盛泽到苏州，从京城到月港，"
        "你的丝绸行销天下。朝廷派来的税吏对你恭恭敬敬，地方官见了你也得称一声'沈公'。"
        "你一生经历了小冰河期的灾荒、葛贤抗税的风波、努尔哈赤崛起的动荡，"
        "但每一次危机，你都用织机前的耐心和精明撑了过来。"
        "盛泽镇上的人都说，沈家的绸庄，是万历年间最稳的买卖。"
    ),
    priority=100,
)

ENDING_LOYAL_RESIST = Ending(
    type=EndingType.LOYAL_RESIST.value,
    name="忠义抗税",
    icon="⚔️",
    conditions=[
        EndingCondition("event", op="==", value="evt.guoben_dispute"),
        EndingCondition("debt_zero"),
    ],
    narrative_template=(
        "万历二十九年（1601年）六月，苏州织工葛贤聚众抗税，你亲历了那场风暴。"
        "你没有站在税监孙隆一边，也没有在织工群中领头，但你默默资助了那些受难者。"
        "事后朝廷追查，你本可以撇清关系，但你选择承认参与——"
        "沈氏在你身后哭，你只说了一句：'织户的辛苦，总要有人知道。'"
        "你被流放辽东，但你的名字，和葛贤一起，被写进了万历年间最光辉的篇章。"
    ),
    priority=90,
)

ENDING_OVERSEAS_PIONEER = Ending(
    type=EndingType.OVERSEAS_PIONEER.value,
    name="出海冒险",
    icon="⛵",
    conditions=[
        EndingCondition("city", op="==", value="yuegang"),
        EndingCondition("cash", ">=", 5),
    ],
    narrative_template=(
        "你离开了盛泽，搭船到了福建月港——那是万历年间唯一合法的通商口岸。"
        "你从江南收丝，到月港卖给海商。一个月后，你的第一艘船出海了。"
        "闽南商人垄断着大部分生意，但你靠着织工的精细和对丝路的熟悉，"
        "在东南亚建立了自己的贸易网。"
        "五年后，你已是月港最大的丝客。朝廷的禁海令对你来说只是一纸空文——"
        "海上丝绸之路的繁荣，你正是其中之一。"
    ),
    priority=80,
)

ENDING_SCHOLAR_SUCCESS = Ending(
    type=EndingType.SCHOLAR_SUCCESS.value,
    name="学而优",
    icon="📚",
    conditions=[
        EndingCondition("identity", op="==", value="scholar"),
        EndingCondition("event", op="==", value="evt.imperial_exam_pass"),
    ],
    narrative_template=(
        "你弃织从文，三十岁中举人，三十五岁中进士。"
        "你被派往地方做父母官，亲眼看见了你年轻时织户们受的苦。"
        "你推行减税、修建水利、整顿牙行，让丝绸之乡重新焕发生机。"
        "你母亲在你赴任那天说：'儿啊，做官要记得自己也是织户出身。'"
        "你用一生证明：万历年间，读书人也能为织户说话。"
    ),
    priority=80,
)

ENDING_PEACEFUL_FAMILY = Ending(
    type=EndingType.PEACEFUL_FAMILY.value,
    name="田园归隐",
    icon="🏡",
    conditions=[
        EndingCondition("task", op="==", value="quest.family_meet"),
        EndingCondition("cash", ">=", 10),
        EndingCondition("debt", "<=", 1),
    ],
    narrative_template=(
        "你没有成为巨富，也没有做官。你守着盛泽的一方小院，"
        "和沈氏生儿育女，把家传织技传给了下一代。"
        "你把多余的钱拿出来给阿宝念书，每到小满节就带全家去先蚕祠拜祭。"
        "邻居张婶常来串门，说沈家的日子，是镇上最安稳的。"
        "你用一生证明：平平淡淡，才是真。"
    ),
    priority=60,
)

ENDING_COMFORTABLE = Ending(
    type=EndingType.COMFORTABLE.value,
    name="小康安稳",
    icon="🏠",
    conditions=[
        EndingCondition("cash", ">=", 20),
        EndingCondition("debt", "<=", 3),
        EndingCondition("round", ">=", 20),
    ],
    narrative_template=(
        "你用十年时间，从五两银子的织工，变成了有三十两家底的小康人家。"
        "你没有大富大贵，但日子过得踏实：织机不停、口粮不愁、债务不忧。"
        "你让阿宝学了织绸，沈氏持家有方，"
        "整个家族在盛泽镇上站稳了脚跟。"
        "你常在茶馆听人聊国家大事，"
        "但心里想的，是下一季的丝价能不能再好些。"
    ),
    priority=50,
)

ENDING_STRUGGLING = Ending(
    type=EndingType.STRUGGLING.value,
    name="勉强维持",
    icon="🪵",
    conditions=[
        EndingCondition("cash", ">=", 0),
        EndingCondition("debt", "<=", 10),
    ],
    narrative_template=(
        "你的生活并不容易，但也没有崩溃。"
        "一年的收成刚好够嚼用，明年的债明年再说。"
        "盛泽镇上和你一样的织户有千百户，"
        "你不比别人好，也不比别人差。"
        "这就是万历年间最普通的织户人生——"
        "在乱世中求一口安稳，在小冰河期的寒潮里咬牙撑过去。"
    ),
    priority=30,
)

ENDING_BANKRUPT_BEGGAR = Ending(
    type=EndingType.BANKRUPT_BEGGAR.value,
    name="破产流民",
    icon="💀",
    conditions=[
        EndingCondition("cash", "<", 0),
    ],
    narrative_template=(
        "万历年间的小冰河期，江南水灾、北方旱灾，丝绸生意越来越难做。"
        "你欠下的债滚成了雪球，最后连织机都被牙行收走了。"
        "沈氏带着阿宝回了娘家，你一个人蹲在盛泽镇西码头上，"
        "看着来来往往的商船——那些船上有你曾织过的绸。"
        "你没有去死，万历年间的流民比你想活得多。"
        "你加入了流民群，去苏州找活路，听说葛贤的抗税队伍里也需要人——"
        "你站起身，往苏州的方向走去。"
    ),
    priority=20,
)


# ============= 结局集 =============

ALL_ENDINGS = [
    ENDING_MERCHANT_EMPIRE,
    ENDING_LOYAL_RESIST,
    ENDING_OVERSEAS_PIONEER,
    ENDING_SCHOLAR_SUCCESS,
    ENDING_PEACEFUL_FAMILY,
    ENDING_COMFORTABLE,
    ENDING_STRUGGLING,
    ENDING_BANKRUPT_BEGGAR,
]


# ============= 结局系统 =============

class EndingSystem:
    """结局判定系统

    使用：
    1. 初始化：EndingSystem()
    2. 每轮后：check(state) → Optional[Ending]
    3. 命中：state.ending = ending.to_dict()
    """

    def __init__(self, endings: list = None):
        self.endings = sorted(endings or ALL_ENDINGS, key=lambda e: -e.priority)
        self._checked: list = []  # 历史检查记录

    def check(self, state) -> Optional[Ending]:
        """检查是否触发结局

        Returns:
            触发的 Ending（最高优先级），或 None
        """
        triggered_events = list(state.triggered_events or [])
        # quest_states 可能在 state 或 facade 上
        quest_states = getattr(state, "quest_states", None) or {}
        # 也尝试从 quest_system 获取
        if not quest_states and hasattr(state, "triggered_events"):
            pass
        completed_list = []
        # 提取 completed quest ids
        for qid, qst in quest_states.items():
            if isinstance(qst, dict) and qst.get("status") == "completed":
                completed_list.append({"id": qid, "name": qid})

        # 优先级从高到低检查
        for ending in self.endings:
            if ending.matches(state, triggered_events, completed_list):
                record = {
                    "ending": ending,
                    "state_at_trigger": {
                        "cash": state.cash,
                        "debt": state.debt,
                        "rice": state.rice,
                        "city": state.current_city,
                        "round": state.round_number,
                    },
                    "triggered_events": triggered_events,
                    "completed_quests": completed_list,
                }
                self._checked.append(record)
                return ending
        return None

    def get_ending_summary(self) -> dict:
        """获取所有结局的判定条件（用于 UI 显示）"""
        return {
            e.type: {
                "name": e.name,
                "icon": e.icon,
                "priority": e.priority,
                "conditions": [
                    {"type": c.type, "op": c.op, "value": c.value}
                    for c in e.conditions
                ],
                "narrative": e.narrative_template,
            }
            for e in self.endings
        }

    def get_history(self) -> list:
        """获取检查历史"""
        return [
            {
                "ending": r["ending"].name,
                "icon": r["ending"].icon,
                "round": r["state_at_trigger"]["round"],
                "cash": r["state_at_trigger"]["cash"],
            }
            for r in self._checked
        ]


# ============= 烟雾测试 =============

if __name__ == "__main__":
    from history_footnote.game_state import GameState

    print("=== EndingSystem 烟雾测试 ===\n")

    # 1. 盛世商贾
    s = GameState()
    s.cash = 60.0
    s.debt = 0.0
    s.round_number = 50
    s.triggered_events = ["evt.little_ice_age"]
    es = EndingSystem()
    ending = es.check(s)
    print(f"  cash=60, debt=0, round=50 → {ending.name} ({ending.icon})" if ending else "  1. 无")
    assert ending and ending.type == "merchant_empire"

    # 2. 破产流民
    s2 = GameState()
    s2.cash = -5.0
    s2.debt = 0.0
    s2.round_number = 30
    ending2 = es.check(s2)
    print(f"  cash=-5, debt=0, round=30 → {ending2.name} ({ending2.icon})" if ending2 else "  2. 无")
    assert ending2 and ending2.type == "bankrupt_beggar"

    # 3. 忠义抗税
    s3 = GameState()
    s3.cash = 10.0
    s3.debt = 0.0
    s3.round_number = 30
    s3.triggered_events = ["evt.guoben_dispute"]
    ending3 = es.check(s3)
    print(f"  cash=10, debt=0, evt.guoben_dispute → {ending3.name} ({ending3.icon})" if ending3 else "  3. 无")
    assert ending3 and ending3.type == "loyal_resist"

    # 4. 优先级：cash=60 + evt.guoben_dispute → merchant_empire 优先（priority 100 vs 90）
    s4 = GameState()
    s4.cash = 60.0
    s4.debt = 0.0
    s4.round_number = 50
    s4.triggered_events = ["evt.guoben_dispute"]
    ending4 = es.check(s4)
    print(f"  cash=60 + evt.guoben_dispute → {ending4.name} (priority 100 vs 90)" if ending4 else "  4. 无")
    assert ending4 and ending4.type == "merchant_empire"

    # 5. 全部 8 结局
    print(f"\n=== 8 结局概览 ===")
    summary = es.get_ending_summary()
    for etype, info in sorted(summary.items(), key=lambda x: -x[1]["priority"]):
        print(f"  {info['icon']} {info['name']} (priority={info['priority']})")
        for c in info["conditions"]:
            print(f"    {c['type']} {c['op']} {c['value']}")

    print(f"\n  check 历史: {es.get_history()}")
