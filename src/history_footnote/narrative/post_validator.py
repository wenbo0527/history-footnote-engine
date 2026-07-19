"""DM 叙事后校验器（Post-Validator）— v1.6+

设计目标（来自 v1.0 产品文档 §7.6）：
- 优先用 DMResponse 结构化字段（events_to_save / updates）
- 叙事文本只做兜底校验（已死人物主动互动 vs 被动提及）
- 返回 issues 列表，供 dm_agent.regenerate 重试使用
- 2 次重试仍失败 → game_loop 调用 generate_safe_narrative 兜底

四层校验：
1. 铁律校验（iron_laws + triggered_events）
2. 行动边界校验（action_boundaries + DM reported state_changes）
3. 时间一致性校验（DM 叙事不能"快进"或"倒退"游戏时间）
4. 史实锚点校验（historical_anchors 不能被改写）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any
from enum import Enum


class ValidationLayer(str, Enum):
    """校验层级"""
    IRON = "iron"               # 铁律层（铁定违反）
    PLAUSIBLE = "plausible"     # 可然层（可能但不当）
    TIME = "time"               # 时间一致性
    FORMAT = "format"           # 输出格式


@dataclass
class ValidationIssue:
    """单个校验问题"""
    layer: str               # iron | plausible | time | format
    severity: str            # error | warning
    message: str             # 人类可读描述
    details: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """校验结果"""
    valid: bool                            # True = 通过，False = 有 error
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def _extract_person_name(iron_law: dict) -> str:
    """从 iron_law 中提取人名（简化版：取 fact 中的人名关键词）"""
    fact = iron_law.get("fact", "")
    # 简化：从 fact 中匹配 "X 病逝/卒/死" 的 X
    m = re.search(r"([一-龥]{2,4})(?:病逝|卒|死|被)", fact)
    if m:
        return m.group(1)
    return ""


def _is_passive_mention(narrative: str, person: str) -> bool:
    """判断 narrative 中 person 是否是"被动提及"（不是主动互动）

    被动提及例子：
    - "海瑞已死"
    - "听说海瑞去世了"
    - "回想海瑞当年的风采"

    主动互动例子：
    - "海瑞对你说..."
    - "海瑞走了过来"
    """
    if not person:
        return True  # 无法判断 → 默认通过
    if person not in narrative:
        return True   # 没出现 → 不算违反

    # 主动互动动词模式：紧跟在 person 后
    active_patterns = [
        rf"{person}[，,。]?\s*(?:对你|向你|跟我|对玩家)",
        rf"{person}\s*(?:说|讲|问|答|点头|摇头|走过来|走过来|望过来|笑了笑|叹了口气)",
        rf"(?:你见到|见到|看到)\s*{person}",
    ]
    for pat in active_patterns:
        if re.search(pat, narrative):
            return False  # 主动互动
    return True  # 被动提及


def post_validate(
    dm_response: dict,
    state: dict,
    era_config: dict,
    player_input: str = "",
) -> ValidationResult:
    """DM 叙事后校验

    Args:
        dm_response: DM 生成的响应（含 narrative / events_to_save / updates 等）
        state: 当前游戏状态（含 triggered_events / current_date）
        era_config: 时代配置（含 iron_laws / historical_events）
        player_input: 玩家原始输入（用于判断一致性）

    Returns:
        ValidationResult(valid=..., issues=[...])
    """
    issues = []

    narrative = dm_response.get("narrative", "") or ""
    events_to_save = dm_response.get("events_to_save", []) or []
    state_changes = dm_response.get("state_changes", {}) or {}
    updates = dm_response.get("updates") or {}

    triggered_events = set(state.get("triggered_events", []) or [])
    current_date = state.get("current_date", "")
    current_round = state.get("round_number", 1)

    # === 第一层：输出格式校验 ===
    issues.extend(_validate_format(dm_response, narrative))

    # === 第二层：铁律校验（iron_laws + triggered_events）===
    issues.extend(_validate_iron_laws(
        narrative=narrative,
        events_to_save=events_to_save,
        triggered_events=triggered_events,
        era_config=era_config,
    ))

    # === 第三层：行动边界校验 ===
    issues.extend(_validate_action_boundaries(
        player_input=player_input,
        narrative=narrative,
        state_changes=state_changes,
        era_config=era_config,
        selected_identity=state.get("selected_identity", ""),
    ))

    # === 第四层：时间一致性校验 ===
    issues.extend(_validate_time_consistency(
        narrative=narrative,
        current_date=current_date,
        current_round=current_round,
        time_cost=dm_response.get("time_cost", 1),
    ))

    # === 第五层：史实锚点校验（historical_anchors 不能被改写）===
    issues.extend(_validate_anchors(
        events_to_save=events_to_save,
        updates=updates,
        triggered_events=triggered_events,
        era_config=era_config,
    ))

    # === 综合：valid=True 表示没有 error ===
    has_error = any(i.severity == "error" for i in issues)
    return ValidationResult(valid=not has_error, issues=issues)


def _validate_format(dm_response: dict, narrative: str) -> list[ValidationIssue]:
    """格式校验"""
    issues = []

    if not narrative:
        issues.append(ValidationIssue(
            layer=ValidationLayer.FORMAT.value,
            severity="error",
            message="narrative 字段为空",
        ))

    # 🆕 v2.3 narrative 长度检查（按时间模式分档，详见 system_base.md "字数控制"）
    # 默认上限 800 字；具体上限由 time_mode 决定（在 dm_agent 里用）
    # 这里只兜底：> 1500 一定是错的（即使是慢时间也不该写这么长）
    if narrative and len(narrative) < 100:
        issues.append(ValidationIssue(
            layer=ValidationLayer.FORMAT.value,
            severity="warning",
            message=f"叙事过短（{len(narrative)} 字），可能不够丰富",
        ))
    if narrative and len(narrative) > 1500:
        issues.append(ValidationIssue(
            layer=ValidationLayer.FORMAT.value,
            severity="error",  # 升级为 error，配合 agent 重试
            message=f"叙事过长（{len(narrative)} 字），违反字数控制（慢时间上限 700）",
        ))

    # voice_options 检查
    voice_options = dm_response.get("voice_options", []) or []
    if voice_options:
        if len(voice_options) > 4:
            issues.append(ValidationIssue(
                layer=ValidationLayer.FORMAT.value,
                severity="warning",
                message=f"voice_options 数量过多（{len(voice_options)}），建议 2-4 个",
            ))
        for i, opt in enumerate(voice_options):
            if not opt.get("intent_text"):
                issues.append(ValidationIssue(
                    layer=ValidationLayer.FORMAT.value,
                    severity="warning",
                    message=f"voice_options[{i}] 缺少 intent_text",
                ))

    return issues


def _validate_iron_laws(
    narrative: str,
    events_to_save: list[str],
    triggered_events: set,
    era_config: dict,
) -> list[ValidationIssue]:
    """铁律校验：已死人物不能主动互动；已触发的历史事件不能被改写"""
    issues = []
    iron_laws = era_config.get("world", {}).get("iron_laws", []) or era_config.get("iron_laws", [])

    for iron_law in iron_laws:
        iron_id = iron_law.get("id", "")
        # 1. 检查"已死"类铁律
        fact = iron_law.get("fact", "")
        if not any(kw in fact for kw in ["病逝", "卒", "死", "被清算", "被抄"]):
            continue  # 不是死亡/清算类铁律，跳过
        if iron_id not in triggered_events:
            continue  # 铁律还未触发，不强制约束

        # 2. 提取人名并检查 narrative
        person = _extract_person_name(iron_law)
        if not person:
            continue
        if person not in narrative:
            continue

        if not _is_passive_mention(narrative, person):
            issues.append(ValidationIssue(
                layer=ValidationLayer.IRON.value,
                severity="error",
                message=f"已死/被清算人物『{person}』在叙事中主动互动（违反铁律）",
                details={"iron_law_id": iron_id, "person": person, "fact": fact},
            ))

    return issues


def _validate_action_boundaries(
    player_input: str,
    narrative: str,
    state_changes: dict,
    era_config: dict,
    selected_identity: str,
) -> list[ValidationIssue]:
    """行动边界校验：DM 不能在叙事中描述玩家做出超出身份边界的事"""
    issues = []

    if not selected_identity:
        return issues

    identities = era_config.get("world", {}).get("player_identities", {})
    identity = identities.get(selected_identity, {})
    if not identity:
        return issues

    boundaries = identity.get("action_boundaries", {})
    cannot_influence = boundaries.get("cannot_influence", [])

    # 检查叙事中是否出现了"玩家影响 X"的描述
    # 简化：检查 cannot_influence 关键词 + 影响动词
    for forbidden in cannot_influence:
        forbidden_kw = forbidden[:3] if len(forbidden) >= 3 else forbidden  # 取前 3 字
        # 影响动词模式
        influence_patterns = [
            rf"你.{0,5}{forbidden_kw}",
            rf"{forbidden_kw}.{{0,10}}(?:改变|决定|说服|影响|推翻)",
        ]
        for pat in influence_patterns:
            if re.search(pat, narrative):
                issues.append(ValidationIssue(
                    layer=ValidationLayer.PLAUSIBLE.value,
                    severity="error",
                    message=f"叙事描述玩家影响『{forbidden}』（超出身份边界）",
                    details={"forbidden": forbidden, "identity": selected_identity},
                ))
                break  # 一个 forbidden 不重复报

    return issues


def _validate_time_consistency(
    narrative: str,
    current_date: str,
    current_round: int,
    time_cost: int,
) -> list[ValidationIssue]:
    """时间一致性校验：time_cost=3 (数日) 但叙事只描写了一刻钟"""
    issues = []

    if time_cost is None or time_cost <= 0:
        return issues

    # 1. 检查叙事中是否有"快进"暗示但 time_cost 很小
    if time_cost == 1:
        # time_cost=1 (半日) 但叙事含"数日"等暗示
        if re.search(r"(数日|数天|数月|三日后|十日后)", narrative):
            issues.append(ValidationIssue(
                layer=ValidationLayer.TIME.value,
                severity="warning",
                message=f"time_cost=1（半日）但叙事描述了更长时间",
                details={"time_cost": time_cost},
            ))

    # 2. 检查时间倒退（叙事中出现比 current_date 更早的日期）
    # 简化：检查叙事中是否有"回到 X 年"等
    if re.search(r"回到.*年前", narrative):
        issues.append(ValidationIssue(
            layer=ValidationLayer.TIME.value,
            severity="warning",
            message="叙事暗示时间倒退",
        ))

    return issues


def _validate_anchors(
    events_to_save: list[str],
    updates: dict,
    triggered_events: set,
    era_config: dict,
) -> list[ValidationIssue]:
    """史实锚点校验：已触发的 historical_anchors 不能被改写"""
    issues = []

    # 收集所有已触发的历史事件
    all_events = []
    raw_events = era_config.get("mechanics", {}).get("historical_events", []) or []
    for ev in raw_events:
        ev_id = ev.get("event_id", "")
        if ev_id in triggered_events:
            all_events.append(ev)

    # 检查 events_to_save 中是否有与已触发事件矛盾的描述
    for event_summary in events_to_save:
        for event in all_events:
            event_name = event.get("event_name", "")
            # 简化匹配：检查事件摘要是否包含"未发生"、"没发生"、"推迟"
            negation_patterns = [
                rf"{event_name}.*?(?:没发生|未发生|没有发生|推迟|取消)",
                rf"(?:没有|未|没有).*?{event_name}",
            ]
            for pat in negation_patterns:
                if re.search(pat, event_summary):
                    issues.append(ValidationIssue(
                        layer=ValidationLayer.IRON.value,
                        severity="error",
                        message=f"事件摘要与已触发事件矛盾：{event_summary[:50]}",
                        details={"anchor_id": event.get("event_id"), "event_name": event_name},
                    ))
                    break

    return issues


# ============================================================
# 兜底叙事生成器
# ============================================================

def generate_safe_narrative(
    state: dict,
    era_config: dict,
    failed_response: dict | None = None,
) -> dict:
    """安全叙事兜底：2 次重试仍失败时使用

    用 era_config + state 生成模板化过渡叙事，保证游戏不卡死。

    Returns:
        dict（DMResponse 格式）
    """
    triggered_events = sorted(state.get("triggered_events", []) or [])
    current_date = state.get("current_date", "未知")
    current_round = state.get("round_number", 1)
    era_name = era_config.get("era_name", "未知时代")

    # 1. 检查是否有强制触发的史实事件
    forced_event_text = ""
    raw_events = era_config.get("mechanics", {}).get("historical_events", []) or []
    for ev in raw_events:
        if ev.get("event_id") in triggered_events:
            forced_event_text = f"你听说了『{ev.get('event_name', '')}』的消息。"
            break

    # 2. 构造安全叙事
    safe_narrative = (
        f"时间悄然流逝。【{era_name}】第{current_round}回合，{current_date}。\n\n"
        f"这一天里，镇上没有发生什么特别的事。{forced_event_text}\n\n"
        f"（系统提示：DM 连续 2 次生成不符合约束，为保证游戏不卡死，已切换到模板化过渡叙事。下次输入可正常继续。）"
    )

    return {
        "narrative": safe_narrative,
        "state_changes": {},
        "events_to_save": [f"第{current_round}回合：时间流逝（兜底）"],
        "updates": None,
        "is_action": True,
        "time_cost": 1,
        "intent_type": "action",
        "voice_options": [
            {
                "voice_id": "voice_observe",
                "voice_name": "继续观察",
                "intent_text": "我在镇上走走看看今天有什么动静",
            },
            {
                "voice_id": "voice_action",
                "voice_name": "继续做手头的事",
                "intent_text": "我回到织机前继续织布",
            },
        ],
        "validation_passed": True,
        "_is_safe_narrative": True,
    }