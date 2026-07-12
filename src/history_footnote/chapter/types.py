"""v2.8.0 章节制核心数据结构

设计原则：
1. 嵌套 dataclass（ChapterState）— 不让 GameState 字段超 250
2. 所有字段都有默认值 — 旧存档反序列化时不破
3. 枚举优先字符串 — 减少 LLM 拼写错误
4. JSON 序列化往返一致 — 配合 v2.7 重放承诺

字段组织：
- 枚举类：ActType / NodeRole / TransitionType / ClosureStatus
- 数据类：ChapterState / ChapterBlueprint / BlueprintNode / ChapterMeta
- 工具方法：to_dict / from_dict（兼容 asdict 和 JSON 字符串）

段二新增：
- ChapterMeta：章节元属性（act/role/emotion_tone/choice_type）— LLM 不可改的硬约束
- ActType：三幕枚举（departure/initiation/return）
- ChapterBlueprint.nodes 改 List[BlueprintNode]（段一用 List[dict]，段二升级）
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


# ============= 枚举（段一先用字符串字段，枚举类型预留） =============

class ActType(str, Enum):
    """三幕枚举——英雄之旅元结构

    - DEPARTURE：启程幕（玩家离开日常）
    - INITIATION：启蒙幕（试炼/觉醒）
    - RETURN：回归幕（回归/终极选择）
    """
    DEPARTURE = "departure"
    INITIATION = "initiation"
    RETURN = "return"

    @classmethod
    def from_string(cls, value: str) -> "ActType":
        """容错解析：未匹配时回退到 DEPARTURE"""
        try:
            return cls(value)
        except ValueError:
            return cls.DEPARTURE


class NodeRole(str, Enum):
    """节点角色——LLM 不可改的硬约束

    4 节点模板（pressure_divide_choose_consequence）：
    - INTRODUCTION：引入冲突
    - ESCALATION：冲突升级
    - CLIMAX：高潮抉择
    - RESOLUTION：后果收束
    """
    INTRODUCTION = "introduction"
    ESCALATION = "escalation"
    CLIMAX = "climax"
    RESOLUTION = "resolution"

    @classmethod
    def from_string(cls, value: str) -> "NodeRole":
        """容错解析：未匹配时回退到 INTRODUCTION"""
        try:
            return cls(value)
        except ValueError:
            return cls.INTRODUCTION


class TransitionType(str, Enum):
    """章节转化方式——段一先支持 3 种，段三扩展"""
    SEASON = "season"             # 季节/时间推进
    RELATIONSHIP = "relationship"  # 关系变化
    IDENTITY = "identity"          # 身份/Build 转变

    @classmethod
    def from_string(cls, value: str) -> "TransitionType":
        try:
            return cls(value)
        except ValueError:
            return cls.SEASON


class ClosureStatus(str, Enum):
    """收束状态"""
    INIT = "INIT"                 # 章节未初始化
    CONTINUE = "CONTINUE"         # 继续游玩
    SOFT_READY = "SOFT_READY"     # 软收束（关键节点完成）
    HARD_FORCED = "HARD_FORCED"   # 硬收束（时间窗口到期）


# ============= 核心数据结构 =============

# 🆕 v2.10.1 W85: 5 类叙事位置（章节模板类型）
# 章节制叙事的"骨架标签"。玩家行为触发关键词/价值偏移后,
# RouteDetector 会把章节的 narrative_position 在这 5 类之间切换。
NARRATIVE_POSITIONS = [
    "opening",           # 开篇：铺陈日常，建立关系
    "rising_conflict",   # 上升：冲突升级，逼迫表态
    "crisis",            # 危机：不可逆事件发生
    "convergence",       # 汇合：历史铁轨落地
    "resolution",        # 收束：所有线索收束
]

# 🆕 v2.10.1 W85: 节奏类型
PACE_TYPES = ["slow", "accelerating", "fast", "variable", "decelerating"]

# 🆕 v2.10.1 W85: 钩子类型
HOOK_TYPES = ["suspense", "conflict_imminent", "reversal", "emotional_blank", "none"]

# 🆕 v2.10.1 W85: 当前路线默认值（兜底，Phase 1 纯规则版无 LLM）
DEFAULT_CURRENT_ROUTE: dict = {
    "template": "opening",
    "trigger": None,          # "keyword:抗税" / "value_shift:trust=-0.8"
    "entered_at_round": 1,
    "dm_instruction": "",
}


@dataclass
class ChapterState:
    """章节运行时状态——嵌套在 GameState.chapter_state

    设计要点：
    - 所有字段有默认值 → 旧存档反序列化时自动建空对象
    - 蓝图段一存 dict（避免 dataclass 序列化测试受冲击）
    - 段三再升级为 ChapterBlueprint dataclass

    🆕 v2.10.1 W85 新增 current_route / route_history:
    - current_route: 当前章节所属的"涌现路线"状态
    - route_history: 本局所有路线变更记录
    - 旧 session 反序列化时自动用 DEFAULT_CURRENT_ROUTE 兜底
    """

    # === 当前章节 ===
    current_chapter: int = 0              # 0 = 未初始化
    current_node: int = 1                 # 章节内 1-4
    chapter_start_round: int = 1          # 当前章节开始的 round_number

    # === 蓝图（段一存 dict，段三升级为 ChapterBlueprint） ===
    blueprint: Optional[dict] = None      # 章节蓝图（JSON dict 形式）
    blueprint_loaded_at: str = ""         # 蓝图加载时间戳（调试用）

    # === 收束状态 ===
    last_closure_status: str = "INIT"     # INIT / CONTINUE / SOFT_READY / HARD_FORCED

    # === 🆕 v2.8.0 段三 W13 章节初始化标记 ===
    # PathSwitcher 触发器 4 用：just_initialized=True 时重排路径优先级
    # Coordinator 在 post_step 末尾清空
    just_initialized: bool = False

    # === 章节历史（每章结算后追加） ===
    chapter_history: list[dict] = field(default_factory=list)
    # 形如：
    # [{"chapter": 1, "summary": "...", "transition": "season", "rounds_in_chapter": 12}]

    # === 🆕 v2.10.1 W85: 涌现式路线状态 ===
    # current_route: 玩家当前所处路线的运行时快照
    #   - template: "opening" / "rising_conflict" / "crisis" / "convergence" / "resolution"
    #   - trigger: "keyword:抗税" / "value_shift:trust=-0.8" / "historical_anchor:hai_rui_death"
    #   - entered_at_round: 进入此路线的回合号
    #   - dm_instruction: 给 DM 的创作指令（由 RouteDetector 生成）
    current_route: dict = field(default_factory=lambda: dict(DEFAULT_CURRENT_ROUTE))

    # route_history: 本局所有路线变更的轨迹
    #   每条: {"round": int, "from_template": str, "to_template": str, "trigger": str}
    route_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterState":
        """从 dict 反序列化（容错）"""
        if data is None:
            return cls()
        return cls(
            current_chapter=data.get("current_chapter", 0),
            current_node=data.get("current_node", 1),
            chapter_start_round=data.get("chapter_start_round", 1),
            blueprint=data.get("blueprint"),
            blueprint_loaded_at=data.get("blueprint_loaded_at", ""),
            last_closure_status=data.get("last_closure_status", "INIT"),
            chapter_history=data.get("chapter_history", []),
            just_initialized=data.get("just_initialized", False),
            # 🆕 v2.10.1 W85: 旧 session 兜底
            current_route=data.get("current_route") or dict(DEFAULT_CURRENT_ROUTE),
            route_history=data.get("route_history", []),
        )


@dataclass
class BlueprintNode:
    """蓝图节点——章节内的单个叙事节点

    段一用 dict 形式（避免 dataclass 序列化影响），段三升级为正式 dataclass
    """

    index: int                            # 1-4
    role: str                             # introduction/escalation/climax/resolution
    scene: str = ""                       # 场景描述
    npc_ids: list[str] = field(default_factory=list)
    option_directions: list[dict] = field(default_factory=list)
    knowledge_ids: list[str] = field(default_factory=list)
    completion_condition: str = ""        # 段一硬编码（round_X_reached）

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BlueprintNode":
        return cls(
            index=data.get("index", 1),
            role=data.get("role", "introduction"),
            scene=data.get("scene", ""),
            npc_ids=data.get("npc_ids", []),
            option_directions=data.get("option_directions", []),
            knowledge_ids=data.get("knowledge_ids", []),
            completion_condition=data.get("completion_condition", ""),
        )


@dataclass
class ChapterBlueprint:
    """章节蓝图——完整章节的内容结构

    段二 W5 升级：增加 meta 字段（元属性硬约束）
    段一阶段蓝图用 JSON dict 形式存于 ChapterState.blueprint,
    段三可选择是否升级为正式 dataclass

    🆕 v2.10.1 W85 新增 5 个"涌现式模板字段":
    - narrative_position: 5 类之一(opening/rising_conflict/crisis/convergence/resolution)
      RouteDetector 在 post_step 触发路线变更时,会在 _maybe_advance_node 把
      current_route.template 同步到此字段(让下一节点的叙事骨架变化)
    - pace: 节奏(slow/accelerating/fast/variable/decelerating)
    - hook_type: 章节开头钩子(suspense/conflict_imminent/reversal/emotional_blank/none)
    - must_resolve: 本章必须解决的冲突列表(LLM 在生成节点时不能跳过)
    - dm_instruction: 给 DM 的创作指令,DM system prompt 可读
    """

    chapter_id: int
    chapter_title: str = ""               # "且听下回分解 · 春蚕"
    chapter_subtitle: str = ""            # 情绪基调副标
    nodes: list[BlueprintNode] = field(default_factory=list)
    transition_hint: str = "season"       # 建议的下一章转化方式
    meta: Optional[ChapterMeta] = None    # 🆕 v2.8.0 段二元属性

    # === 🆕 v2.10.1 W85: 涌现式模板字段 ===
    narrative_position: str = "opening"   # 5 类之一
    pace: str = "slow"                    # 节奏
    hook_type: str = "none"               # 钩子类型
    must_resolve: list[str] = field(default_factory=list)  # 必解冲突
    dm_instruction: str = ""              # DM 创作指令

    def to_dict(self) -> dict:
        return {
            "chapter_id": self.chapter_id,
            "chapter_title": self.chapter_title,
            "chapter_subtitle": self.chapter_subtitle,
            "nodes": [n.to_dict() for n in self.nodes],
            "transition_hint": self.transition_hint,
            "meta": self.meta.to_dict() if self.meta else None,
            # 🆕 v2.10.1 W85
            "narrative_position": self.narrative_position,
            "pace": self.pace,
            "hook_type": self.hook_type,
            "must_resolve": list(self.must_resolve),
            "dm_instruction": self.dm_instruction,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterBlueprint":
        meta_data = data.get("meta")
        meta = ChapterMeta.from_dict(meta_data) if meta_data else None
        return cls(
            chapter_id=data.get("chapter_id", 1),
            chapter_title=data.get("chapter_title", ""),
            chapter_subtitle=data.get("chapter_subtitle", ""),
            nodes=[BlueprintNode.from_dict(n) for n in data.get("nodes", [])],
            transition_hint=data.get("transition_hint", "season"),
            meta=meta,
            # 🆕 v2.10.1 W85: 旧蓝图文件兜底
            narrative_position=data.get("narrative_position", "opening"),
            pace=data.get("pace", "slow"),
            hook_type=data.get("hook_type", "none"),
            must_resolve=data.get("must_resolve", []),
            dm_instruction=data.get("dm_instruction", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ChapterBlueprint":
        """从 JSON 字符串加载（chapter{N}_blueprint.json）"""
        return cls.from_dict(json.loads(json_str))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============= 🆕 v2.8.0 段二 ChapterMeta =============

@dataclass
class ChapterMeta:
    """章节元属性——LLM 不可改的硬约束

    设计原则：
    - act / role / emotion_tone / choice_type 由规则引擎产出
    - LLM 自由生成节点内容，但必须遵守这 4 个硬约束
    - suggested_node_count 是软建议（段二 LLM 可在 3-5 浮动）
    - suggested_template 是软建议（LLM 可改）

    字段说明：
    - act：三幕（departure/initiation/return）
    - role：章节角色（ordinary/call/threshold/trial/allies/...）
    - emotion_tone：情绪基调（"unease→resolve"）
    - choice_type：选择类型（"whether_to_step_out"）
    - suggested_node_count：建议节点数（LLM 可在 3-5 浮动）
    - suggested_template：建议模板（"pressure_divide_choose_consequence"）
    """

    chapter_id: int
    act: str = "departure"                     # ActType 字符串
    role: str = "ordinary"                     # 章节角色字符串
    emotion_tone: str = "neutral"
    choice_type: str = "open_ended"
    suggested_node_count: int = 4              # LLM 可浮动 3-5
    suggested_template: str = "pressure_divide_choose_consequence"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterMeta":
        return cls(
            chapter_id=data.get("chapter_id", 1),
            act=data.get("act", "departure"),
            role=data.get("role", "ordinary"),
            emotion_tone=data.get("emotion_tone", "neutral"),
            choice_type=data.get("choice_type", "open_ended"),
            suggested_node_count=data.get("suggested_node_count", 4),
            suggested_template=data.get("suggested_template", "pressure_divide_choose_consequence"),
        )

    def validate(self) -> list[str]:
        """校验元属性（返回错误列表，空列表=通过）"""
        errors = []
        # act 必须是 ActType 之一
        try:
            ActType(self.act)
        except ValueError:
            errors.append(f"act 非法: {self.act}")
        # role 至少 1 个字符
        if not self.role.strip():
            errors.append("role 不能为空")
        # emotion_tone 必须含箭头
        if "→" not in self.emotion_tone and self.emotion_tone != "neutral":
            errors.append(f"emotion_tone 应含箭头 '→': {self.emotion_tone}")
        # 节点数 1-10（防御性）
        if not (1 <= self.suggested_node_count <= 10):
            errors.append(f"suggested_node_count 超出范围: {self.suggested_node_count}")
        return errors


# ============= 工具函数 =============

def make_default_chapter_state() -> ChapterState:
    """工厂函数：创建默认 ChapterState（v2.8.0 初始化用）"""
    return ChapterState()


def is_chapter_active(state: "ChapterState") -> bool:
    """判断章节是否已激活（current_chapter > 0）"""
    return state.current_chapter > 0
