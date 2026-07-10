"""v2.8.0 段二 W6 Fallback（校验失败兑底）

设计目标：
- 校验失败时保留 LLM 写的节点内容（scene/npc/options）
- 结构换默认（4 节点 introduction→escalation→climax→resolution）
- 段一 W4 决策：内容不丢，结构兑底

兑底策略：
1. 默认 4 节点模板
2. LLM 节点数 > 4：取前 4 个 LLM 节点 + 默认结构
3. LLM 节点数 < 4：用 LLM 节点 + 默认节点补齐
4. completion_condition 一律用默认（避免 LLM 写奇怪条件）

约束：
- 0 LLM 调用
- 纯函数式
"""
from __future__ import annotations

import logging
from typing import Optional

from history_footnote.chapter.types import (
    ChapterBlueprint,
    ChapterMeta,
    BlueprintNode,
    NodeRole,
    TransitionType,
)

_LOG = logging.getLogger("history_footnote.chapter.fallback")

# 默认 4 节点模板（与 schema_converter 一致）
DEFAULT_NODE_TEMPLATE = [
    {"role": "introduction", "completion_condition": "round_4_reached"},
    {"role": "escalation", "completion_condition": "round_8_reached"},
    {"role": "climax", "completion_condition": "round_12_reached"},
    {"role": "resolution", "completion_condition": "round_16_reached"},
]


class ChapterFallback:
    """章节蓝图兑底器（v2.8.0 段二 W6）

    策略：内容保留 + 结构换默认
    - LLM 写的 scene / npc_ids / option_directions / knowledge_ids 保留
    - role / completion_condition 改用默认
    - 节点数裁剪到 4
    """

    @staticmethod
    def fallback(
        llm_output: dict,
        chapter_meta: ChapterMeta,
        errors: list[str] = None,
    ) -> ChapterBlueprint:
        """兑底：内容保留 + 结构换默认

        Args:
            llm_output: LLM 原始输出
            chapter_meta: 元属性（必填，用于 chapter_id 和 meta 字段）
            errors: 校验错误列表（用于日志）

        Returns:
            ChapterBlueprint 实例（兑底版本）
        """
        if errors:
            _LOG.warning("章节蓝图兑底: %d 个错误 → 内容保留+结构换默认", len(errors))

        chapter_id = chapter_meta.chapter_id
        title = llm_output.get("chapter_title", f"第 {chapter_id} 章") if isinstance(llm_output, dict) else f"第 {chapter_id} 章"
        transition = "season"
        if isinstance(llm_output, dict):
            transition = TransitionType.from_string(
                llm_output.get("transition_hint", "season")
            ).value

        # 提取 LLM 节点（仅取内容字段）
        llm_nodes_content = []
        if isinstance(llm_output, dict):
            raw_nodes = llm_output.get("nodes", [])
            if isinstance(raw_nodes, list):
                for n in raw_nodes:
                    if isinstance(n, dict):
                        llm_nodes_content.append(ChapterFallback._extract_node_content(n))

        # 用默认结构 + LLM 内容合并
        nodes = ChapterFallback._merge_with_default_structure(llm_nodes_content)

        blueprint = ChapterBlueprint(
            chapter_id=chapter_id,
            chapter_title=title,
            chapter_subtitle=chapter_meta.emotion_tone,
            nodes=nodes,
            transition_hint=transition,
            meta=chapter_meta,
        )
        _LOG.info(
            "Fallback: chapter=%d, title=%s, nodes=%d",
            chapter_id, title, len(nodes),
        )
        return blueprint

    @staticmethod
    def _extract_node_content(raw: dict) -> dict:
        """从 LLM 节点提取内容字段（不含 role/completion_condition）"""
        return {
            "scene": raw.get("scene", ""),
            "npc_ids": raw.get("npc_ids", []) or [],
            "option_directions": raw.get("option_directions", []) or [],
            "knowledge_ids": raw.get("knowledge_ids", []) or [],
        }

    @staticmethod
    def _merge_with_default_structure(llm_contents: list[dict]) -> list[BlueprintNode]:
        """合并：默认结构 + LLM 内容

        规则：
        - 默认 4 节点
        - LLM 内容按 index 对应到默认节点（i < len(llm_contents) → 用 LLM 内容）
        - 超出 LLM 节点数的 → 用纯默认
        """
        nodes = []
        for i, default_node in enumerate(DEFAULT_NODE_TEMPLATE):
            content = llm_contents[i] if i < len(llm_contents) else None
            if content:
                # 保留 LLM 内容 + 默认 role/condition
                node = BlueprintNode(
                    index=i + 1,
                    role=default_node["role"],
                    scene=content["scene"],
                    npc_ids=content["npc_ids"],
                    option_directions=content["option_directions"],
                    knowledge_ids=content["knowledge_ids"],
                    completion_condition=default_node["completion_condition"],
                )
            else:
                # 纯默认节点
                node = BlueprintNode(
                    index=i + 1,
                    role=default_node["role"],
                    scene="",
                    npc_ids=[],
                    option_directions=[],
                    knowledge_ids=[],
                    completion_condition=default_node["completion_condition"],
                )
            nodes.append(node)
        return nodes


def fallback_chapter_blueprint(
    llm_output: dict,
    chapter_meta: ChapterMeta,
    errors: list[str] = None,
) -> ChapterBlueprint:
    """便捷函数：单次兑底"""
    return ChapterFallback.fallback(llm_output, chapter_meta, errors)
