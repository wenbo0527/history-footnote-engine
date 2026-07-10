"""v2.8.0 段二 W7 PromptBuilder（喂 LLM 的完整上下文）

设计目标：
- 给 LLM 构建章节生成所需的完整 prompt 上下文
- 4 个上下文区：硬约束 / 历史摘要 / 玩家画像 / 时代包资源
- 4 条 focus_points 规则：价值维度 / 路径未完成 / 财务压力 / 上一章选择

约束：
- 0 LLM 调用
- 纯函数式（输入 state + meta + era_config → 输出 dict）
- token 估算可控（~2400 tokens）
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from history_footnote.chapter.types import ChapterMeta

_LOG = logging.getLogger("history_footnote.chapter.prompt_builder")


# focus_points 数量上限
MAX_FOCUS_POINTS = 5

# 价值维度偏移阈值
VALUE_DIMENSION_THRESHOLD = 0.6

# 路径亲和度低于此视为未完成
PATH_AFFINITY_LOW_THRESHOLD = 0.5


class ChapterPromptBuilder:
    """章节 Prompt 上下文构建器（v2.8.0 段二 W7）

    用法：
        builder = ChapterPromptBuilder(state, era_config)
        context = builder.build(meta)  # dict
        # 喂给 LLM → 生成 llm_output → 调 facade.convert_llm_to_blueprint
    """

    def __init__(self, state, era_config: Optional[dict] = None):
        self.state = state
        self.era_config = era_config or {}

    def build(self, chapter_meta: ChapterMeta) -> dict:
        """构建喂给 LLM 的完整上下文

        Returns:
            dict: 包含 4 个区
            {
                "chapter_meta": {...},          # 硬约束
                "chapter_history": [...],       # 全部历史摘要
                "focus_points": [...],          # 增量规则（最多 5 条）
                "player": {...},                # 玩家画像
                "available_*": {...},           # 时代包资源
            }
        """
        return {
            "chapter_meta": self._build_meta_context(chapter_meta),
            "chapter_history": self._build_history_context(),
            "focus_points": self._build_focus_points(),
            "player": self._build_player_context(),
            "available_npcs": self._list_npcs(),
            "available_knowledge": self._list_knowledge(),
            "available_paths": self._list_paths(),
        }

    # ============= 区 1：硬约束 =============

    def _build_meta_context(self, meta: ChapterMeta) -> dict:
        """硬约束：LLM 不可改"""
        return {
            "chapter_id": meta.chapter_id,
            "act": meta.act,                          # "departure"
            "role": meta.role,                        # "ordinary"
            "emotion_tone": meta.emotion_tone,        # "unease→resolve"
            "choice_type": meta.choice_type,          # "whether_to_step_out"
        }

    # ============= 区 2：历史摘要 =============

    def _build_history_context(self) -> list[dict]:
        """全部历史章节摘要（从 chapter_state.chapter_history）"""
        cs = getattr(self.state, "chapter_state", None)
        if cs is None:
            return []
        history = getattr(cs, "chapter_history", []) or []
        # 每条只需保留核心信息
        return [
            {
                "chapter": h.get("chapter"),
                "summary": h.get("summary", ""),
                "transition": h.get("transition", ""),
            }
            for h in history
        ]

    # ============= 区 3：玩家画像 =============

    def _build_player_context(self) -> dict:
        """玩家画像：build + value_dimensions + active_paths"""
        return {
            "build": getattr(self.state, "player_build", ""),
            "value_dimensions": getattr(self.state, "value_dimensions", {}) or {},
            "active_paths": self._get_active_paths(),
        }

    def _get_active_paths(self) -> list[str]:
        """当前活跃路径（从 path_state）"""
        ps = getattr(self.state, "path_state", None)
        if ps is None:
            return []
        return getattr(ps, "active_paths", []) or []

    # ============= 区 4：时代包资源 =============

    def _list_npcs(self) -> list[str]:
        """时代包 NPC 列表（限制 30 个避免 prompt 爆炸）"""
        npcs = self.era_config.get("npcs", {}) or {}
        return list(npcs.keys())[:30]

    def _list_knowledge(self) -> list[str]:
        """知识条目 ID 列表（限制 50 个）"""
        knowledge = self.era_config.get("knowledge", {}) or {}
        entries = knowledge.get("entries", []) or []
        return [e.get("id", "") for e in entries if isinstance(e, dict)][:50]

    def _list_paths(self) -> list[str]:
        """路径 ID 列表（段三才用）"""
        narrative = self.era_config.get("narrative", {}) or {}
        paths = narrative.get("paths", []) or []
        return [p.get("id", "") for p in paths if isinstance(p, dict)]

    # ============= 增量规则：focus_points =============

    def _build_focus_points(self) -> list[str]:
        """根据状态推算本章 focus（最多 5 条）"""
        focus: list[str] = []

        # 规则 1：价值维度偏移
        for dim, val in self._get_value_dimensions().items():
            try:
                v = float(val)
                if abs(v) > VALUE_DIMENSION_THRESHOLD:
                    direction = "偏正" if v > 0 else "偏负"
                    focus.append(
                        f"玩家 {dim} {direction} {v:+.1f}（>{VALUE_DIMENSION_THRESHOLD} 阈值），"
                        f"应体现该价值观的冲突"
                    )
            except (TypeError, ValueError):
                continue

        # 规则 2：路径未完成（亲和度低）
        for path_id in self._get_active_paths():
            affinity = self._get_path_affinity(path_id)
            if affinity < PATH_AFFINITY_LOW_THRESHOLD:
                focus.append(
                    f"路径 {path_id} 进度 {affinity:.0%}（<{PATH_AFFINITY_LOW_THRESHOLD:.0%}），"
                    f"本章应推进"
                )

        # 规则 3：财务压力
        cash = getattr(self.state, "cash", 0)
        try:
            cash_val = float(cash)
            if cash_val < 0:
                focus.append(
                    f"玩家现金 {cash_val:+.1f} 两（负债），"
                    f"本章应体现生存压力"
                )
            elif cash_val < 1:
                focus.append(
                    f"玩家现金 {cash_val:.1f} 两（<1 两），"
                    f"本章应有财务紧张"
                )
        except (TypeError, ValueError):
            pass

        # 规则 4：上一章选择延续
        history = self._build_history_context()
        if history:
            last = history[-1]
            if last.get("summary"):
                focus.append(
                    f"上一章摘要：{last['summary'][:60]}，"
                    f"本章应体现后果"
                )

        return focus[:MAX_FOCUS_POINTS]

    def _get_value_dimensions(self) -> dict:
        """value_dimensions 字段容错读取"""
        return getattr(self.state, "value_dimensions", {}) or {}

    def _get_path_affinity(self, path_id: str) -> float:
        """path_state.path_affinity 容错读取"""
        ps = getattr(self.state, "path_state", None)
        if ps is None:
            return 0.5
        affinities = getattr(ps, "path_affinity", {}) or {}
        return float(affinities.get(path_id, 0.5))


def build_chapter_prompt_context(
    state,
    chapter_meta: ChapterMeta,
    era_config: Optional[dict] = None,
) -> dict:
    """便捷函数：单次构建"""
    return ChapterPromptBuilder(state, era_config).build(chapter_meta)
