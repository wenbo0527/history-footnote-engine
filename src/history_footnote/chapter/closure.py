"""v2.8.0 章节收束判定器（ChapterClosure）

设计原则：
1. 复用 DramaManager.player_model.emotion_state（不发明新概念）
2. 4 节点 × 4 回合 = 16 回合为标准章节长度
3. 软收束：节点 4 + 停留 ≥ 3 回合
4. 硬收束：12 回合还没到节点 4 → 强制收束
5. 复用 drama_manager 维度：distressed 状态提前收束

状态机：
    INIT → CONTINUE ⇄ SOFT_READY → 结算
                                 ↘ HARD_FORCED → 强制结算

约束：
- 不动 DramaManager 现有 evaluate() 方法
- 不修改 DramaManager.player_model
- 0 LLM 调用
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from history_footnote.chapter.types import ClosureStatus

if TYPE_CHECKING:
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager


_LOG = logging.getLogger("history_footnote.chapter.closure")


# 章节默认参数（段一硬编码，段二可配置化）
DEFAULT_NODES_PER_CHAPTER = 4        # 每章节点数
DEFAULT_ROUNDS_PER_NODE = 4          # 每节点建议回合数
SOFT_CLOSURE_MIN_ROUNDS = 3          # 节点 4 至少停留 3 回合才软收束
HARD_CLOSURE_MAX_ROUNDS = 16         # 16 回合强制收束（4 节点 × 4 回合）
DISTRESSED_EARLY_CLOSURE = 10        # distressed 状态 10 回合提前收束


class ChapterClosure:
    """章节收束判定器

    用法：
        closure = ChapterClosure(state, drama_manager)
        status = closure.check()  # 每回合结束调用
    """

    def __init__(
        self,
        state: "GameState",
        drama_manager: Optional["DramaManager"] = None,
        nodes_per_chapter: int = DEFAULT_NODES_PER_CHAPTER,
        rounds_per_node: int = DEFAULT_ROUNDS_PER_NODE,
    ):
        self.state = state
        self.drama = drama_manager
        self.nodes_per_chapter = nodes_per_chapter
        self.rounds_per_node = rounds_per_node

    def check(self) -> str:
        """每回合结束调用，返回当前收束状态

        Returns:
            "INIT" | "CONTINUE" | "SOFT_READY" | "HARD_FORCED"
        """
        cs = self.state.chapter_state
        if cs.current_chapter == 0:
            return ClosureStatus.INIT.value

        rounds_in_chapter = self._rounds_in_chapter()

        # 软收束：当前节点是最后一个 + 节点停留时间足够
        if self._is_at_last_node():
            rounds_in_node = self._rounds_in_current_node()
            if rounds_in_node >= SOFT_CLOSURE_MIN_ROUNDS:
                _LOG.debug(
                    "软收束: chapter=%d, node=%d/%d, rounds_in_node=%d",
                    cs.current_chapter, cs.current_node, self.nodes_per_chapter, rounds_in_node,
                )
                return ClosureStatus.SOFT_READY.value

        # 硬收束 1：达到最大回合数
        if rounds_in_chapter >= HARD_CLOSURE_MAX_ROUNDS:
            _LOG.info(
                "硬收束（超时）: chapter=%d, rounds=%d",
                cs.current_chapter, rounds_in_chapter,
            )
            return ClosureStatus.HARD_FORCED.value

        # 硬收束 2：drama_manager 判定 distressed 状态 + 章节过半
        if self.drama is not None and rounds_in_chapter >= DISTRESSED_EARLY_CLOSURE:
            emotion = self.drama.player_model.emotion_state
            if emotion == "distressed":
                _LOG.info(
                    "硬收束（distressed）: chapter=%d, emotion=%s",
                    cs.current_chapter, emotion,
                )
                return ClosureStatus.HARD_FORCED.value

        return ClosureStatus.CONTINUE.value

    def _rounds_in_chapter(self) -> int:
        """当前章节已进行的回合数"""
        cs = self.state.chapter_state
        return max(0, self.state.round_number - cs.chapter_start_round + 1)

    def _is_at_last_node(self) -> bool:
        """是否在最后一个节点（段二 W5 升级：优先读 ChapterMeta.suggested_node_count）"""
        cs = self.state.chapter_state
        blueprint = cs.blueprint or {}
        meta_data = blueprint.get("meta") if isinstance(blueprint, dict) else None
        if meta_data and isinstance(meta_data, dict):
            try:
                meta_count = int(meta_data.get("suggested_node_count", 0))
                if meta_count > 0:
                    return cs.current_node >= meta_count
            except (TypeError, ValueError):
                pass
        return cs.current_node >= self.nodes_per_chapter

    def _rounds_in_current_node(self) -> int:
        """当前节点已停留的回合数"""
        rounds_in_chapter = self._rounds_in_chapter()
        node_index = self.state.chapter_state.current_node - 1  # 0-based
        rounds_into_node = rounds_in_chapter - (node_index * self.rounds_per_node)
        return max(0, rounds_into_node)
