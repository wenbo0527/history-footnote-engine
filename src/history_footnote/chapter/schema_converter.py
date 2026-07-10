"""v2.8.0 段二 W6 SchemaConverter（LLM JSON → 引擎 Blueprint）

设计目标：
- 把 LLM 生成的章节蓝图 JSON 转换为 ChapterBlueprint dataclass
- 字符串→枚举转换（NodeRole）
- 节点数裁剪（>MAX_NODES 截断，<MIN_NODES 补默认）
- 校验失败 → 调 fallback.py 兑底

约束：
- 0 LLM 调用
- 不抛异常（除非输入完全非法）
- 纯函数式（输入 dict → 输出 ChapterBlueprint）
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from history_footnote.chapter.types import (
    ChapterBlueprint,
    ChapterMeta,
    BlueprintNode,
    NodeRole,
    TransitionType,
)

_LOG = logging.getLogger("history_footnote.chapter.schema_converter")

# 节点数边界（与 validator 一致）
MIN_NODES = 3
MAX_NODES = 6
DEFAULT_NODES = 4

# 4 节点模板的默认结构
DEFAULT_NODE_TEMPLATE = [
    {
        "role": "introduction",
        "completion_condition": "round_4_reached",
    },
    {
        "role": "escalation",
        "completion_condition": "round_8_reached",
    },
    {
        "role": "climax",
        "completion_condition": "round_12_reached",
    },
    {
        "role": "resolution",
        "completion_condition": "round_16_reached",
    },
]


class SchemaConverter:
    """LLM JSON → 引擎 ChapterBlueprint 转换器

    段二 W6 极简版：
    - 直接转换（不做 fallback，fallback 在 fallback.py 单独做）
    - 节点数裁剪
    - 字符串→枚举转换
    """

    def __init__(self, era_config: Optional[dict] = None):
        self.era_config = era_config or {}

    def convert(
        self,
        llm_output: dict,
        chapter_meta: ChapterMeta,
    ) -> ChapterBlueprint:
        """把 LLM 生成的 JSON 转换为 ChapterBlueprint

        Args:
            llm_output: LLM 生成的 dict（约定字段：chapter_title, nodes, transition_hint, meta）
            chapter_meta: 规则引擎产出的元属性（必填）

        Returns:
            ChapterBlueprint 实例

        异常：
            ValueError: 输入完全非法（如 llm_output 不是 dict）
        """
        if not isinstance(llm_output, dict):
            raise ValueError(f"LLM 输出必须是 dict，实际 {type(llm_output).__name__}")

        chapter_id = chapter_meta.chapter_id
        title = llm_output.get("chapter_title", f"第 {chapter_id} 章")
        subtitle = llm_output.get("chapter_subtitle", chapter_meta.emotion_tone)
        transition = TransitionType.from_string(
            llm_output.get("transition_hint", "season")
        ).value

        # 节点转换（含裁剪）
        raw_nodes = llm_output.get("nodes", [])
        nodes = self._convert_nodes(raw_nodes, chapter_id)

        blueprint = ChapterBlueprint(
            chapter_id=chapter_id,
            chapter_title=title,
            chapter_subtitle=subtitle,
            nodes=nodes,
            transition_hint=transition,
            meta=chapter_meta,
        )
        _LOG.info(
            "SchemaConverter: chapter=%d, title=%s, nodes=%d",
            chapter_id, title, len(nodes),
        )
        return blueprint

    def _convert_nodes(
        self, raw_nodes: list, chapter_id: int
    ) -> list[BlueprintNode]:
        """节点转换 + 裁剪"""
        if not isinstance(raw_nodes, list):
            raw_nodes = []

        # 节点数裁剪
        if len(raw_nodes) > MAX_NODES:
            _LOG.warning("LLM 生成 %d 节点，截断到 %d", len(raw_nodes), MAX_NODES)
            raw_nodes = raw_nodes[:MAX_NODES]
        elif len(raw_nodes) < MIN_NODES:
            _LOG.warning(
                "LLM 生成 %d 节点（<%d），用默认节点补齐",
                len(raw_nodes), MIN_NODES,
            )
            raw_nodes = self._pad_default_nodes(raw_nodes, chapter_id)

        nodes = []
        for i, raw in enumerate(raw_nodes):
            if not isinstance(raw, dict):
                continue
            node = self._convert_single_node(raw, i + 1)
            nodes.append(node)
        return nodes

    def _convert_single_node(self, raw: dict, index: int) -> BlueprintNode:
        """单个节点转换"""
        role_str = raw.get("role", "")
        role = NodeRole.from_string(role_str).value

        # option_directions 标准化
        options = raw.get("option_directions", []) or []
        normalized_options = []
        for opt in options:
            if isinstance(opt, dict):
                normalized_options.append({
                    "text": opt.get("text", ""),
                    "path": opt.get("path", opt.get("path_hint", "")),
                })
            elif isinstance(opt, str):
                normalized_options.append({"text": opt, "path": ""})

        return BlueprintNode(
            index=index,
            role=role,
            scene=raw.get("scene", ""),
            npc_ids=raw.get("npc_ids", []) or [],
            option_directions=normalized_options,
            knowledge_ids=raw.get("knowledge_ids", []) or [],
            completion_condition=raw.get("completion_condition", ""),
        )

    def _pad_default_nodes(self, existing: list, chapter_id: int) -> list[dict]:
        """补齐默认节点（用 DEFAULT_NODE_TEMPLATE 兜底）"""
        needed = MIN_NODES - len(existing)
        defaults = DEFAULT_NODE_TEMPLATE[:needed]
        return list(existing) + defaults


def convert_llm_to_blueprint(
    llm_output: dict,
    chapter_meta: ChapterMeta,
    era_config: Optional[dict] = None,
) -> ChapterBlueprint:
    """便捷函数：单次转换

    Args:
        llm_output: LLM 生成的 dict
        chapter_meta: 元属性（必填）
        era_config: era.json 配置（可选）

    Returns:
        ChapterBlueprint 实例
    """
    return SchemaConverter(era_config).convert(llm_output, chapter_meta)
