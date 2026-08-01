"""🆕 v2.10.16 Phase 10 — 故事模式数据模型

设计目标：
- 静态剧本（无需 LLM 调用）
- 节点 (Node) + 选项 (VoiceOption) 的有限状态机
- D&D 风格：flag 组合 + 触发条件 + effects 副作用

兼容性：
- VoiceOption 跟现有 voice_options 完全兼容（前端零改动）
- Narrative 跟现有 narrative 完全兼容

🆕 v2.10.25: narrative_sections (多声部) 优先于 narrative 字符串
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from history_footnote.story_mode.rich import NarrativeSection


@dataclass
class ScriptedVoiceOption:
    """一个静态剧本选项（跟现有 VoiceOption 对齐）"""
    voice_id: str                           # 唯一 id (在 chapter 内)
    voice_name: str                         # 短名（如 "💰 向牙行借银子"）
    description: str = ""                   # 详细描述
    inner_voice: Optional[str] = None       # DM 内心独白（玩家会看到）

    # 🆕 v2.10.22: 跟主游戏 VoiceOption 对齐 (intent_text 必填)
    intent_text: str = ""                   # 语义化玩家行动 ("我先去查查家里有什么...")
    value_dimension: Optional[str] = None  # 价值维度 (跟主游戏对齐)

    # 触发逻辑
    next_node_id: str = ""                  # 选项 → 下个节点
    effects: dict[str, Any] = field(default_factory=dict)
    # e.g. {"cash_delta": -1, "rice_delta": 5, "city_move": "suzhou", "flag_set": ["met_zhang"]}

    # D&D 风格检定（可选）
    check: Optional[str] = None             # e.g. "charisma >= 3"
    check_success_node: Optional[str] = None
    check_fail_node: Optional[str] = None
    check_hint: Optional[str] = None        # 检定失败提示


@dataclass
class ScriptedNode:
    """故事模式的一个场景节点"""
    node_id: str                            # 唯一 id (chapter 内)
    round_min: int = 1                      # 最小触发回合
    round_max: int = 999                    # 最大触发回合
    narrative: str = ""                     # 静态 narrative 文本 (兜底)

    # 🆕 v2.10.25: 多声部叙事 (优先于 narrative)
    narrative_sections: list["NarrativeSection"] = field(default_factory=list)
    # 注: 多声部格式见 rich.py: NarrativeSection (narrator/text/emotion/sound/action/italic)

    # 触发条件（可选）
    required_city: Optional[str] = None     # 必须在此城（如 "shengze"）
    required_flags: list[str] = field(default_factory=list)   # 必须有这些 flag
    forbidden_flags: list[str] = field(default_factory=list)  # 不能有这些 flag

    # 节点角色（章节进度用）
    role: str = "intro"                     # intro/escalation/climax/resolution

    # 选项（3-5 个）
    voice_options: list[ScriptedVoiceOption] = field(default_factory=list)

    # 自动跳转（无选项时）
    auto_next_node_id: Optional[str] = None

    # 节点触发时的副作用
    on_enter_effects: dict[str, Any] = field(default_factory=dict)
    on_enter_text: str = ""                 # 进入节点时的额外 narrative


@dataclass
class ScriptedChapter:
    """完整一章剧本"""
    chapter_id: int
    title: str                              # e.g. "第一章：家贫"
    subtitle: str = ""                      # e.g. "万历十五年·盛泽镇"
    description: str = ""

    nodes: dict[str, ScriptedNode] = field(default_factory=dict)
    start_node_id: str = ""

    # 章节结束条件
    end_node_ids: list[str] = field(default_factory=list)  # 这些节点触发后进入下一章
    total_rounds: int = 16                  # 章节总回合数

    # 元信息
    estimated_play_minutes: int = 8         # 预计游玩时间
    theme: str = ""                         # 主题（"求生"、"抉择"）

    # 🆕 v2.10.17: 随机事件列表（运行时注入）
    random_encounters: list = field(default_factory=list)


# ============================================================
# State 扩展（写入现有 GameState）
# ============================================================

# These fields 加到 GameState（story_mode 状态）
SCRIPTED_STATE_KEYS = {
    "scripted_mode": False,        # 是否处于故事模式
    "scripted_chapter_id": 0,      # 当前章节 (1=家贫, 2=织染)
    "scripted_node_id": "",        # 当前节点
    "scripted_flags": [],          # 已设置的 flag 列表
    "scripted_visits": [],         # 已访问节点历史
    "scripted_chapter_complete": False,
}