"""规则引擎——配置驱动的状态机

设计参考：设计文档v1.0.md 第3.2节"规则引擎" + 第7.5节"规则引擎解释器核心逻辑"

核心职责（确定性逻辑，全部由代码执行，不交给LLM判断）：
- 条件求值（JSON结构化条件，替代eval）
- 行动边界检查（小人物身份约束）
- 触发条件检查（triggers）
- 历史锚点注入（force_trigger=true的事件强制触发）
- 节奏推进指令计算（pacing_rules的condition由代码计算，结论注入DM）
- 认知解锁候选（insight_tree的双路解锁）
- 变量变更应用（含合理性校验，max_shift_per_round）
- 每回合自动结算（round_settlement）
- 终局生成（finale_templates匹配）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# === 工具函数 ===

def clamp(value: float, lo: float, hi: float) -> float:
    """将值限制在[lo, hi]区间"""
    return max(lo, min(hi, value))


# === 条件求值 ===

class ConditionEvaluator:
    """JSON结构化条件求值器

    支持两种条件结构：
    1. 原子条件：{"field": "x", "op": "lt", "value": 10}
    2. 复合条件：{"and": [...]} / {"or": [...]}

    field可以是：
    - 变量（self.variables）
    - 元数据字段（self.round_number / self.player_idle_rounds等）
    - 特殊字段：unlocked_insights / triggered_events
    """

    OPS = {
        "lt": lambda a, v: a < v,
        "lte": lambda a, v: a <= v,
        "gt": lambda a, v: a > v,
        "gte": lambda a, v: a >= v,
        "eq": lambda a, v: a == v,
        "ne": lambda a, v: a != v,
    }

    def __init__(self, state: "GameStateView"):
        self.state = state

    def eval(self, condition: dict) -> bool:
        if "and" in condition:
            return all(self.eval(c) for c in condition["and"])
        if "or" in condition:
            return any(self.eval(c) for c in condition["or"])
        if "not" in condition:
            return not self.eval(condition["not"])

        # 原子条件
        field = condition.get("field")
        op = condition.get("op")
        value = condition.get("value")
        if not field or op not in self.OPS:
            return False

        actual = self._get_field_value(field)
        if actual is None:
            return False
        return self.OPS[op](actual, value)

    def _get_field_value(self, field: str) -> Any:
        """从state视图读取字段值"""
        # 变量
        if field in self.state.variables:
            return self.state.variables[field]
        # 元数据
        if hasattr(self.state, field):
            return getattr(self.state, field)
        # 特殊列表字段：检查是否包含某值
        if field == "unlocked_insight":
            return value if (value := self._list_contains(self.state.unlocked_insights, condition.get("value", ""))) else None
        return None

    @staticmethod
    def _list_contains(lst: list, target: str) -> str | None:
        return target if target in lst else None


# 简化版：把GameState当作view用
class GameStateView:
    """规则引擎用的state视图——暴露必要字段"""

    def __init__(self, state):
        self._state = state

    @property
    def variables(self) -> dict:
        return self._state.variables

    @property
    def round_number(self) -> int:
        return self._state.round_number

    @property
    def player_idle_rounds(self) -> int:
        return self._state.player_idle_rounds

    @property
    def rounds_since_last_insight(self) -> int:
        return self._state.rounds_since_last_insight

    @property
    def triggered_events(self) -> list:
        return self._state.triggered_events

    @property
    def triggered_triggers(self) -> list:
        return self._state.triggered_triggers

    @property
    def unlocked_insights(self) -> list:
        return self._state.unlocked_insights

    @property
    def value_shifts(self) -> dict:
        return self._state.value_shifts

    @property
    def selected_identity(self) -> str:
        return self._state.selected_identity

    @property
    def player_gender(self) -> str:
        return self._state.player_gender


@dataclass
class ForcedEvent:
    """强制触发的历史事件"""

    event_id: str
    event_name: str
    date: str
    description: str
    scope: str
    player_visibility: str
    narrative_mandatory: bool


@dataclass
class PacingDirective:
    """节奏推进指令"""

    id: str
    direction: str
    hint: str
    constraint: str


@dataclass
class InsightCandidate:
    """认知解锁候选"""

    id: str
    topic: str
    trigger_type: str  # player_explore / narrative_guided
    confirm_needed: bool
    unlock_knowledge: list[str]
    narrative_hint: str


@dataclass
class TriggeredRule:
    """触发的trigger"""

    id: str
    narrative_hint: str
    effect: dict


# === 规则引擎主类 ===

class RuleEngine:
    """配置驱动的规则引擎

    每个游戏回合按以下顺序执行：
    1. 行动边界检查（check_action）
    2. 强制历史事件注入（check_forced_events）
    3. 触发条件检查（check_triggers）
    4. 节奏规则计算（check_pacing）
    5. 认知解锁候选（check_insights）
    6. 玩家行动语义匹配
    7. 每回合结算（settle_round）
    8. 应用DM提议的变量变更（apply_changes）
    9. 推进回合（advance_round）
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.var_meta = {v["id"]: v for v in config.get("mechanics", {}).get("variables", [])}
        self.value_meta = {v["id"]: v for v in config.get("growth", {}).get("value_dimensions", [])}

    def make_view(self, state) -> GameStateView:
        return GameStateView(state)

    # === 1. 行动边界检查 ===

    def check_action(self, view: GameStateView, action_description: str) -> dict:
        """检查玩家行动是否允许

        v1.1+：根据selected_identity使用对应的action_boundaries
        Phase 1用关键词匹配实现，Phase 2可升级为embedding语义匹配。
        """
        # 根据selected_identity选择对应的action_boundaries
        selected_id = view.selected_identity if hasattr(view, "selected_identity") else ""
        identity = {}
        if selected_id:
            identities = self.config.get("world", {}).get("player_identities", {})
            identity = identities.get(selected_id, {})
        if not identity:
            # 兼容旧格式
            identity = self.config.get("world", {}).get("player_identity", {})

        boundaries = identity.get("action_boundaries", {})

        # 不能接触
        for forbidden in boundaries.get("cannot_access", []):
            if self._semantic_match(action_description, forbidden):
                return {
                    "allowed": False,
                    "reason": f"身份约束：{identity.get('role', '小人物')}无法接触《{forbidden}》",
                }

        # 不能影响
        for forbidden in boundaries.get("cannot_influence", []):
            if self._semantic_match(action_description, forbidden):
                return {
                    "allowed": False,
                    "reason": f"影响范围：{identity.get('role', '小人物')}无法影响《{forbidden}》",
                }

        return {"allowed": True, "reason": ""}

    @staticmethod
    def _semantic_match(text: str, keyword: str) -> bool:
        """关键词匹配（Phase 1简化版）

        支持：
        1. 直接包含
        2. 标点切分后的token匹配
        3. 2-4字滑动窗口（处理"科举考场" vs "科举考试"这种局部匹配）
        Phase 2可替换为embedding相似度>0.7
        """
        text = text.lower()
        keyword = keyword.lower()

        # 1. 直接包含
        if keyword in text:
            return True

        # 2. 标点切分后匹配
        tokens = re.split(r"[，,、\s（）()【】\[\]]", keyword)
        for token in tokens:
            if len(token) >= 2 and token in text:
                return True

        # 3. 2-4字滑动窗口（处理"科举考场" vs "科举考试"）
        # 把keyword切成所有可能的2-4字子串，任一在text中即匹配
        for size in (2, 3, 4):
            for i in range(len(keyword) - size + 1):
                substr = keyword[i : i + size]
                if substr in text:
                    return True

        return False

    # === 2. 强制历史事件注入 ===

    def check_forced_events(self, view: GameStateView) -> list[ForcedEvent]:
        """检查本回合是否有强制触发的历史事件"""
        events = self.config.get("mechanics", {}).get("historical_events", [])
        forced = []
        for event in events:
            if not event.get("force_trigger"):
                continue
            if event["round"] != view.round_number:
                continue
            if event["event_id"] in view.triggered_events:
                continue
            forced.append(
                ForcedEvent(
                    event_id=event["event_id"],
                    event_name=event["event_name"],
                    date=event["date"],
                    description=event["description"],
                    scope=event.get("scope", "national"),
                    player_visibility=event.get("player_visibility", "rumor"),
                    narrative_mandatory=event.get("narrative_mandatory", False),
                )
            )
        return forced

    # === 3. 触发条件检查 ===

    def check_triggers(self, view: GameStateView) -> list[TriggeredRule]:
        """检查变量触发的trigger（每次都要重新评估，不只once）"""
        evaluator = ConditionEvaluator(view)
        triggers = self.config.get("mechanics", {}).get("triggers", [])
        triggered = []
        for trigger in triggers:
            # once=true的trigger如果已触发则跳过
            if trigger.get("once", False) and trigger["id"] in view.triggered_triggers:
                continue
            if not evaluator.eval(trigger["condition"]):
                continue
            triggered.append(
                TriggeredRule(
                    id=trigger["id"],
                    narrative_hint=trigger.get("narrative_hint", ""),
                    effect=trigger.get("effect", {}),
                )
            )
            # 标记为已触发
            if trigger.get("once", False):
                view._state.triggered_triggers.append(trigger["id"])
        return triggered

    # === 4. 节奏推进指令 ===

    def check_pacing(self, view: GameStateView) -> list[PacingDirective]:
        """计算节奏推进规则——确定性计算，结论注入DM"""
        evaluator = ConditionEvaluator(view)
        rules = self.config.get("mechanics", {}).get("pacing_rules", [])
        directives = []
        for rule in rules:
            if not evaluator.eval(rule["condition"]):
                continue
            directives.append(
                PacingDirective(
                    id=rule["id"],
                    direction=rule.get("direction", ""),
                    hint=rule.get("hint", ""),
                    constraint=rule.get("constraint", ""),
                )
            )
        return directives

    # === 5. 认知解锁候选 ===

    def check_insights(
        self,
        view: GameStateView,
        player_input: str,
        dm_guided: bool = False,
    ) -> list[InsightCandidate]:
        """检查认知解锁——双路机制

        路径A: player_explore —— 关键词+语义匹配初筛，DM终判（confirm_needed=True）
        路径B: narrative_guided —— DM已植入线索，玩家回应即触发（confirm_needed=False）

        路径B由dm_guided参数控制（DM在叙事中调用Tool告知"我已植入线索"）
        """
        candidates = []
        insights = self.config.get("growth", {}).get("insight_tree", [])
        for insight in insights:
            if insight["id"] in view.unlocked_insights:
                continue
            # 前置条件检查
            prereqs = insight.get("prerequisites", [])
            if not all(p in view.unlocked_insights for p in prereqs):
                continue

            confirm_needed = True

            if insight.get("trigger_type") == "player_explore":
                # 关键词匹配
                keywords = insight.get("trigger_keywords", [])
                if not any(kw in player_input for kw in keywords):
                    continue
                # 语义提示匹配
                semantic_hints = insight.get("semantic_hints", [])
                if semantic_hints and not any(hint in player_input for hint in semantic_hints):
                    # 有关键词命中但语义提示未匹配，仍然作为候选（DM终判）
                    pass

            elif insight.get("trigger_type") == "narrative_guided":
                # DM植入线索后，玩家回应即触发
                # v1.2+：前置满足 + 玩家输入匹配trigger_keywords/topic/hint
                if not dm_guided:
                    topic = insight.get("topic", "")
                    trigger_keywords = insight.get("trigger_keywords", [])
                    semantic_hints = insight.get("semantic_hints", [])
                    narrative_hint = insight.get("narrative_hint", "")
                    input_relevant = False

                    # 1. trigger_keywords直接匹配（v1.2+扩展）
                    if any(kw in player_input for kw in trigger_keywords):
                        input_relevant = True

                    # 2. topic包含
                    if not input_relevant and topic and topic in player_input:
                        input_relevant = True

                    # 3. 从hint/narrative_hint里提取中文词
                    if not input_relevant:
                        all_text = topic + " " + " ".join(semantic_hints) + " " + narrative_hint
                        import re
                        chinese_words = re.findall(r"[\u4e00-\u9fa5]{2,}", all_text)
                        skip = {"玩家", "之后", "之前", "其中", "或者", "引导", "理解", "安排",
                                "反思", "场景", "线索", "追问", "线索后", "做出", "选择",
                                "通过", "之口", "提问", "一个", "一次", "植入",
                                "海外", "白银流入", "白银流通"}
                        hint_keywords = [w for w in chinese_words if w not in skip]
                        if any(hk in player_input for hk in hint_keywords):
                            input_relevant = True

                    if not input_relevant:
                        continue
                confirm_needed = False

            candidates.append(
                InsightCandidate(
                    id=insight["id"],
                    topic=insight.get("topic", ""),
                    trigger_type=insight["trigger_type"],
                    confirm_needed=confirm_needed,
                    unlock_knowledge=insight.get("unlock_knowledge", []),
                    narrative_hint=insight.get("narrative_hint", ""),
                )
            )
        return candidates

    # === 6. 每回合自动结算 ===

    def settle_round(self, view: GameStateView) -> list[dict]:
        """每回合自动结算（无条件或带条件的变量变化）"""
        evaluator = ConditionEvaluator(view)
        settlements = self.config.get("mechanics", {}).get("round_settlement", [])
        changes = []
        for s in settlements:
            if "condition" in s and not evaluator.eval(s["condition"]):
                continue
            for var_id, change in s.get("effect", {}).items():
                if var_id in self.var_meta:
                    meta = self.var_meta[var_id]
                    view.variables[var_id] = clamp(
                        view.variables[var_id] + change,
                        meta.get("min", 0),
                        meta.get("max", 100),
                    )
            changes.append(s)
        return changes

    # === 7. 应用DM提议的变量变更 ===

    def apply_changes(self, view: GameStateView, state_changes: dict) -> dict:
        """应用DM提议的变量变更，含max_shift_per_round合理性校验

        Returns:
            {"adjusted": {var_id: {"requested": x, "actual": y, "reason": str}}}
        """
        adjusted = {}
        for var_id, change in state_changes.items():
            if var_id not in view.variables:
                continue
            meta = self.var_meta.get(var_id, {})
            max_shift = meta.get("max_shift_per_round", 10)

            # 截断超限变更
            actual_change = clamp(change, -max_shift, max_shift)
            new_value = clamp(
                view.variables[var_id] + actual_change,
                meta.get("min", 0),
                meta.get("max", 100),
            )

            if actual_change != change:
                adjusted[var_id] = {
                    "requested": change,
                    "actual": actual_change,
                    "reason": f"超过单回合最大偏移量({max_shift})，已截断",
                }
            view.variables[var_id] = new_value
        return {"adjusted": adjusted}

    # === 8. 应用update（insight/npc/value） ===

    def apply_updates(self, view: GameStateView, updates: dict | None) -> None:
        """应用DM提议的update字典

        key前缀区分类型：
        - insight:ins_01 → 解锁认知
        - npc:npc_xxx:+1 → 关系等级变化
        - value:tradition_vs_change:-1 → 价值观偏移
        """
        if not updates:
            return

        for key, value in updates.items():
            if ":" not in key:
                continue
            kind, rest = key.split(":", 1)

            if kind == "insight":
                if rest not in view.unlocked_insights:
                    view.unlocked_insights.append(rest)
                    view._state.rounds_since_last_insight = 0

            elif kind == "npc":
                # npc:npc_xxx:+1 或 npc:npc_xxx:level_name
                parts = rest.split(":")
                if len(parts) >= 2:
                    npc_id = parts[0]
                    change = parts[1]
                    current = view.npc_levels.get(npc_id, "陌生")
                    if change.startswith("+") or change.startswith("-"):
                        # 数值变化（暂不实现关系等级升级逻辑，Phase 2）
                        pass
                    else:
                        view.npc_levels[npc_id] = change

            elif kind == "value":
                if rest in self.value_meta:
                    meta = self.value_meta[rest]
                    max_shift = meta.get("max_shift_per_round", 2)
                    actual_change = clamp(int(value), -max_shift, max_shift)
                    view.value_shifts[rest] = view.value_shifts.get(rest, 0) + actual_change

    # === 9. 推进回合 ===

    def advance_round(self, view: GameStateView) -> None:
        """推进到下一回合，更新日期等元数据"""
        view._state.round_number += 1
        # 重置某些元数据
        view._state.consecutive_light_rounds = 0
        # 更新日期
        timeline = self.config.get("world", {}).get("timeline", {})
        start = timeline.get("start", {})
        total_months = (timeline.get("end", {}).get("year", 1587) - start.get("year", 1587)) * 12 + (
            timeline.get("end", {}).get("month", 12) - start.get("month", 1)
        )
        new_months_from_start = view.round_number - 1
        year = start.get("year", 1587) + new_months_from_start // 12
        month = start.get("month", 1) + new_months_from_start % 12
        if month > 12:
            month -= 12
            year += 1
        view._state.current_date = f"{year}年{month}月"

    # === 10. 终局生成 ===

    def get_finale(self, view: GameStateView) -> dict:
        """根据变量值和价值观偏移生成终局"""
        # 简化实现：先匹配优先级最高的finale_rule
        finale_rules = self.config.get("growth", {}).get("finale_rules", [])
        templates = self.config.get("growth", {}).get("finale_templates", {})

        evaluator = ConditionEvaluator(view)
        # 按priority排序
        sorted_rules = sorted(finale_rules, key=lambda r: r.get("priority", 99))

        template_key = "mixed"  # 默认
        for rule in sorted_rules:
            cond = rule.get("condition", {})
            # 处理特殊字段：unlocked_insight
            if cond.get("field") == "unlocked_insight" or (
                "and" in cond and any(c.get("field") == "unlocked_insight" for c in cond.get("and", []))
            ):
                # 转换条件
                target = cond.get("value", "")
                if "unlocked_insight" in str(cond) and target in view.unlocked_insights:
                    template_key = rule.get("template", "mixed")
                    break
            elif evaluator.eval(cond):
                template_key = rule.get("template", "mixed")
                break

        return {
            "template": templates.get(template_key, templates.get("mixed", "")),
            "final_variables": dict(view.variables),
            "value_profile": dict(view.value_shifts),
            "unlocked_insights": list(view.unlocked_insights),
            "npc_relationships": dict(view.npc_levels),
        }

    # === 辅助 ===

    def get_current_date(self, round_number: int) -> str:
        """根据回合数计算游戏内日期"""
        timeline = self.config.get("world", {}).get("timeline", {})
        start = timeline.get("start", {})
        new_months_from_start = round_number - 1
        year = start.get("year", 1587) + new_months_from_start // 12
        month = start.get("month", 1) + new_months_from_start % 12
        if month > 12:
            month -= 12
            year += 1
        return f"{year}年{month}月"
