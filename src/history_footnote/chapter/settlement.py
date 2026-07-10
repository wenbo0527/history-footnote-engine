"""v2.8.0 段二 W8 ChapterSettlement（章节结算 + 摘要生成）

设计目标：
- 章节收束后生成摘要（4 必填项：核心事件/关键选择/Build画像/当前路径）
- 段二 W8：mock LLM 模式（不真打 LLM，规则生成摘要）
- 段三/W10 升级：接真 LLM（temperature=0）

约束：
- 0 真 LLM 调用（mock 模式）
- 4 必填项校验（缺一不通过）
- 纯函数式

摘要内容：
1. 核心事件：本章发生了什么（从 state.event_log 提取）
2. 关键选择：玩家做了什么选择（从 voice_options.last_voice_options 提取）
3. Build 画像：当前 value_dimensions 偏移描述
4. 当前路径：当前 active_paths（段三才完整，段二空）
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from history_footnote.chapter.types import TransitionType

_LOG = logging.getLogger("history_footnote.chapter.settlement")


# 摘要最大长度
MAX_SUMMARY_LENGTH = 200

# 价值维度偏移阈值（超过则纳入画像描述）
VALUE_DIMENSION_NOTABLE_THRESHOLD = 0.4

# 4 必填项 key
REQUIRED_FIELDS = [
    "core_event",
    "key_choice",
    "build_summary",
    "path_summary",
]


class ChapterSettlement:
    """章节结算器（v2.8.0 段二 W8）

    段二 W8 mock 模式：直接基于 state 提取字段
    段三/W10 升级：接真 LLM（make_llm_for_purpose("chapter_settle")）
    """

    def __init__(self, state, era_config: Optional[dict] = None, llm_callable=None):
        """
        Args:
            state: GameState
            era_config: era.json 配置（可选）
            llm_callable: LLM 调用函数（None=mock 模式）
        """
        self.state = state
        self.era_config = era_config or {}
        self._llm = llm_callable  # None → mock 模式

    def settle(self, closure_status: str = "SOFT_READY") -> dict:
        """生成章节结算记录

        Returns:
            dict: chapter_history 追加的记录
            {
                "chapter": int,
                "summary": str,  # 压缩版（200字内）
                "core_event": str,
                "key_choice": str,
                "build_summary": str,
                "path_summary": str,
                "rounds_in_chapter": int,
                "ended_at_round": int,
                "ended_at": str (ISO timestamp),
                "transition": str,
                "closure_status": str,
            }
        """
        cs = self.state.chapter_state
        if cs.current_chapter == 0:
            _LOG.warning("settle() called without active chapter")
            return {}

        # 1. 提取 4 必填项
        core_event = self._extract_core_event()
        key_choice = self._extract_key_choice()
        build_summary = self._extract_build_summary()
        path_summary = self._extract_path_summary()

        # 2. 压缩为 summary（200字内）
        if self._llm is not None:
            # 真 LLM 模式（段三/W10 启用）
            try:
                summary = self._llm(self._build_summarize_prompt(
                    core_event, key_choice, build_summary, path_summary
                ))
                summary = self._truncate_summary(summary)
            except Exception as e:
                _LOG.warning("LLM 摘要失败: %s，使用规则压缩", e)
                summary = self._build_summary_rule(core_event, key_choice, build_summary, path_summary)
        else:
            # Mock 模式（段二 W8）
            summary = self._build_summary_rule(core_event, key_choice, build_summary, path_summary)

        # 3. 收尾元信息
        rounds_in_chapter = max(0, self.state.round_number - cs.chapter_start_round + 1)
        transition = self._get_transition_hint()

        record = {
            "chapter": cs.current_chapter,
            "summary": summary,
            "core_event": core_event,
            "key_choice": key_choice,
            "build_summary": build_summary,
            "path_summary": path_summary,
            "rounds_in_chapter": rounds_in_chapter,
            "ended_at_round": self.state.round_number,
            "ended_at": datetime.now().isoformat(),
            "transition": transition,
            "closure_status": closure_status,
        }

        # 4. 校验 4 必填项
        errors = self._validate_required_fields(record)
        if errors:
            _LOG.warning("章节结算校验失败: %s", errors)

        _LOG.info(
            "章节结算: chapter=%d, status=%s, rounds=%d, summary=%d 字",
            cs.current_chapter, closure_status, rounds_in_chapter, len(summary),
        )
        return record

    # ============= 4 必填项提取 =============

    def _extract_core_event(self) -> str:
        """核心事件：从 event_log 取最后 1-3 条"""
        log = getattr(self.state, "event_log", []) or []
        if not log:
            return "无显著事件"
        # 取最近 1-3 条
        recent = log[-3:] if len(log) >= 3 else log
        events = [e.get("summary", e.get("description", "")) for e in recent]
        events = [e for e in events if e]  # 过滤空
        if not events:
            return "无显著事件"
        return "；".join(events)

    def _extract_key_choice(self) -> str:
        """关键选择：从 last_voice_options 提取"""
        last_voice = getattr(self.state, "last_voice_options", []) or []
        if not last_voice:
            return "无显著选择"
        # 取最近一个选项
        last = last_voice[0] if isinstance(last_voice[0], dict) else {}
        return last.get("text", "无显著选择")

    def _extract_build_summary(self) -> str:
        """Build 画像：从 value_dimensions 提取"""
        vd = getattr(self.state, "value_dimensions", {}) or {}
        notable = []
        for dim, val in vd.items():
            try:
                v = float(val)
                if abs(v) >= VALUE_DIMENSION_NOTABLE_THRESHOLD:
                    direction = "偏正" if v > 0 else "偏负"
                    notable.append(f"{dim}{direction}{v:+.1f}")
            except (TypeError, ValueError):
                continue
        if not notable:
            return "Build 画像不显著"
        return "，".join(notable)

    def _extract_path_summary(self) -> str:
        """当前路径：active_paths（段三才完整，段二空）"""
        ps = getattr(self.state, "path_state", None)
        if ps is None:
            return "无活跃路径"
        active = getattr(ps, "active_paths", []) or []
        if not active:
            return "无活跃路径"
        return "，".join(active)

    # ============= Summary 生成 =============

    def _build_summary_rule(
        self, core_event: str, key_choice: str, build_summary: str, path_summary: str,
    ) -> str:
        """规则压缩 4 必填项为一段摘要（< 200 字）"""
        parts = []
        if core_event and core_event != "无显著事件":
            parts.append(f"事件：{core_event[:40]}")
        if key_choice and key_choice != "无显著选择":
            parts.append(f"选择：{key_choice[:30]}")
        if build_summary and build_summary != "Build 画像不显著":
            parts.append(f"画像：{build_summary[:50]}")
        if path_summary and path_summary != "无活跃路径":
            parts.append(f"路径：{path_summary[:30]}")
        summary = "。".join(parts)
        return self._truncate_summary(summary) if summary else "本章无显著进展"

    def _build_summarize_prompt(
        self, core_event: str, key_choice: str, build_summary: str, path_summary: str,
    ) -> str:
        """构建喂给 LLM 的摘要 prompt（段三启用）"""
        return (
            f"请用 100-200 字总结本章：\n"
            f"- 核心事件：{core_event}\n"
            f"- 关键选择：{key_choice}\n"
            f"- 玩家画像：{build_summary}\n"
            f"- 当前路径：{path_summary}"
        )

    def _truncate_summary(self, summary: str) -> str:
        """截断到 MAX_SUMMARY_LENGTH 字"""
        if len(summary) <= MAX_SUMMARY_LENGTH:
            return summary
        return summary[:MAX_SUMMARY_LENGTH - 3] + "..."

    def _get_transition_hint(self) -> str:
        """从 blueprint 读 transition_hint"""
        cs = self.state.chapter_state
        blueprint = cs.blueprint or {}
        transition = blueprint.get("transition_hint", "season")
        try:
            return TransitionType.from_string(transition).value
        except Exception:
            return "season"

    # ============= 校验 =============

    def _validate_required_fields(self, record: dict) -> list[str]:
        """校验 4 必填项（缺一不通过）"""
        errors = []
        for field in REQUIRED_FIELDS:
            if not record.get(field):
                errors.append(f"必填项缺失: {field}")
        if len(record.get("summary", "")) > MAX_SUMMARY_LENGTH:
            errors.append(f"summary 超过 {MAX_SUMMARY_LENGTH} 字")
        return errors


def settle_chapter(state, era_config: Optional[dict] = None, closure_status: str = "SOFT_READY") -> dict:
    """便捷函数：单次结算"""
    return ChapterSettlement(state, era_config).settle(closure_status)
