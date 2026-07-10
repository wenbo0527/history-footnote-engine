"""v2.8.0 段二 W6 Validator（后校验器）

设计目标：
- 校验 LLM 生成的章节蓝图 JSON
- 校验项：节点数 / 角色顺序 / NPC 存在性 / 知识条目存在性
- 返回 errors 列表（空=通过）
- 校验失败时由 fallback.py 处理（节点内容保留+结构换默认）

约束：
- 0 LLM 调用
- 不抛异常（除非硬错误）
- 纯函数式（输入 dict + era_config → 输出 errors）
"""
from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger("history_footnote.chapter.validator")


# 节点数边界
MIN_NODES = 3
MAX_NODES = 6
DEFAULT_NODES = 4

# 节点角色顺序（introduction→...→resolution）
EXPECTED_NODE_ROLES = ["introduction", "escalation", "climax", "resolution"]


class ChapterValidator:
    """章节蓝图校验器（v2.8.0 段二 W6）

    用法：
        validator = ChapterValidator(era_config)
        errors = validator.validate(llm_output)  # 4 步校验
        if errors:
            # → fallback 兑底
    """

    def __init__(self, era_config: dict):
        self.era_config = era_config
        self._npcs = self._load_npcs()
        self._knowledge = self._load_knowledge()
        self._paths = self._load_paths()

    def _load_npcs(self) -> set:
        """从 era_config 加载 NPC 集合"""
        return set((self.era_config.get("npcs", {}) or {}).keys())

    def _load_knowledge(self) -> set:
        """从 era_config 加载知识条目 ID 集合"""
        knowledge = self.era_config.get("knowledge", {}) or {}
        entries = knowledge.get("entries", []) or []
        return {e.get("id", "") for e in entries if isinstance(e, dict)}

    def _load_paths(self) -> set:
        """从 era_config.narrative.paths 加载路径 ID 集合"""
        narrative = self.era_config.get("narrative", {}) or {}
        paths = narrative.get("paths", []) or []
        return {p.get("id", "") for p in paths if isinstance(p, dict)}

    def validate(self, llm_output: dict) -> list[str]:
        """完整 4 步校验，返回错误列表（空列表=通过）

        4 步：
        1. 节点数约束（3-6）
        2. 节点角色顺序校验
        3. NPC 存在性
        4. 知识条目 + 路径存在性
        """
        errors: list[str] = []
        if not isinstance(llm_output, dict):
            return [f"LLM 输出不是 dict: {type(llm_output).__name__}"]

        nodes = llm_output.get("nodes", [])
        if not isinstance(nodes, list):
            return [f"nodes 不是 list: {type(nodes).__name__}"]

        errors.extend(self._validate_node_count(nodes))
        errors.extend(self._validate_node_roles(nodes))
        errors.extend(self._validate_npcs(nodes))
        errors.extend(self._validate_knowledge_and_paths(nodes))

        if errors:
            _LOG.warning("章节蓝图校验失败: %d 个错误", len(errors))
        return errors

    # ============= 步骤 1：节点数 =============

    def _validate_node_count(self, nodes: list) -> list[str]:
        """节点数 3-6"""
        n = len(nodes)
        if n < MIN_NODES:
            return [f"节点数过少 ({n} < {MIN_NODES})"]
        if n > MAX_NODES:
            return [f"节点数过多 ({n} > {MAX_NODES})"]
        return []

    # ============= 步骤 2：角色顺序 =============

    def _validate_node_roles(self, nodes: list) -> list[str]:
        """节点角色必须按 introduction→...→resolution 顺序

        容忍度：3-5 节点可以省略中间（如 3 节点 = intro/climax/resolution）
        """
        actual_roles = [n.get("role", "") for n in nodes if isinstance(n, dict)]
        if len(actual_roles) < 2:
            return ["节点数过少，无法校验角色顺序"]

        # 关键位置：第一个必须是 introduction，最后一个必须是 resolution
        if actual_roles[0] != "introduction":
            return [f"第 1 节点角色必须是 introduction，实际 {actual_roles[0]}"]
        if actual_roles[-1] != "resolution":
            return [f"最后节点角色必须是 resolution，实际 {actual_roles[-1]}"]

        # 中间节点角色必须在允许集合内
        allowed_middle = set(EXPECTED_NODE_ROLES) - {"introduction", "resolution"}
        for i, role in enumerate(actual_roles[1:-1], start=1):
            if role not in allowed_middle:
                return [f"节点 {i+1} 角色非法: {role}（允许: {allowed_middle}）"]
        return []

    # ============= 步骤 3：NPC 存在性 =============

    def _validate_npcs(self, nodes: list) -> list[str]:
        """节点里的 NPC 必须存在于 era.json.npcs"""
        if not self._npcs:
            return []  # 无 NPC 配置跳过
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            for npc_id in node.get("npc_ids", []):
                if npc_id and npc_id not in self._npcs:
                    return [f"节点 {i+1} 的 NPC 不存在: {npc_id}"]
        return []

    # ============= 步骤 4：知识 + 路径 =============

    def _validate_knowledge_and_paths(self, nodes: list) -> list[str]:
        """节点的 knowledge_ids + option path_hint 必须存在"""
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            # 知识条目
            for kid in node.get("knowledge_ids", []):
                if self._knowledge and kid and kid not in self._knowledge:
                    return [f"节点 {i+1} 的知识条目不存在: {kid}"]
            # 路径 hint
            for opt in node.get("option_directions", []):
                if not isinstance(opt, dict):
                    continue
                path_hint = opt.get("path", "") or opt.get("path_hint", "")
                if self._paths and path_hint and path_hint not in self._paths:
                    # 路径不存在不致命（段三才需要），仅警告
                    # 但返回错误让 fallback 换默认
                    return [f"节点 {i+1} 的路径不存在: {path_hint}"]
        return []


def validate_chapter_output(era_config: dict, llm_output: dict) -> list[str]:
    """便捷函数：单次校验

    Args:
        era_config: era.json 完整 dict
        llm_output: LLM 生成的章节蓝图 dict

    Returns:
        errors 列表（空=通过）
    """
    return ChapterValidator(era_config).validate(llm_output)
