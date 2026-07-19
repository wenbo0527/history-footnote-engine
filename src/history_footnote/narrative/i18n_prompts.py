"""🆕 v2.10.x W57: 多语言 LLM prompt 模板

支持中/英双语 DM prompt 模板
- chapter_blueprint 章节蓝图
- chapter_settlement 章节结算
- narrative_continuation 叙事续写
"""
from __future__ import annotations
from typing import Literal

Locale = Literal["zh-CN", "en-US"]

CHAPTER_BLUEPRINT_PROMPTS = {
    "zh-CN": """# 章节蓝图（v1）

你是章节制叙事 DM。请基于 era 配置生成第 {chapter} 章蓝图。

要求：
- 4 节点结构（start → middle → end）
- 每个节点 1 句 scene 描述 + 2-3 个 option
- 古白话风格
- 章节长度 {total_chapters} 章
- 当前 era: {era_id}
- 玩家身份: {identity}

输出 JSON：
{{
  "chapter": {chapter},
  "title": "...",
  "nodes": [
    {{"role": "start", "scene": "...", "options": ["...", "..."]}},
    {{"role": "middle", "scene": "...", "options": ["...", "..."]}},
    {{"role": "end", "scene": "...", "options": ["..."]}}
  ]
}}
""",
    "en-US": """# Chapter Blueprint (v1)

You are a chapter-based narrative DM. Generate Chapter {chapter} blueprint based on era config.

Requirements:
- 4-node structure (start → middle → end)
- Each node: 1-sentence scene + 2-3 options
- Classical Chinese vernacular style (translated)
- Total chapter length: {total_chapters}
- Current era: {era_id}
- Player identity: {identity}

Output JSON:
{{
  "chapter": {chapter},
  "title": "...",
  "nodes": [
    {{"role": "start", "scene": "...", "options": ["...", "..."]}},
    {{"role": "middle", "scene": "...", "options": ["...", "..."]}},
    {{"role": "end", "scene": "...", "options": ["..."]}}
  ]
}}
""",
}

CHAPTER_SETTLEMENT_PROMPTS = {
    "zh-CN": """# 章节结算（第 {chapter} 章）

请基于本章节叙事生成结算记录。

要求：
- 200字内 summary
- 1 句 core_event
- 1 句 key_choice
- 1 句 build_summary
- 1 句 path_summary
- transition: 下一章过渡提示

输出 JSON：
{{
  "chapter": {chapter},
  "summary": "...",
  "core_event": "...",
  "key_choice": "...",
  "build_summary": "...",
  "path_summary": "...",
  "transition": "..."
}}
""",
    "en-US": """# Chapter Settlement (Chapter {chapter})

Generate settlement record based on chapter narrative.

Requirements:
- 200-word summary
- 1-sentence core_event
- 1-sentence key_choice
- 1-sentence build_summary
- 1-sentence path_summary
- transition: hint for next chapter

Output JSON:
{{
  "chapter": {chapter},
  "summary": "...",
  "core_event": "...",
  "key_choice": "...",
  "build_summary": "...",
  "path_summary": "...",
  "transition": "..."
}}
""",
}

NARRATIVE_CONTINUATION_PROMPTS = {
    "zh-CN": """# 叙事续写

继续玩家选择后的剧情。

玩家行动：{action}
当前场景：{scene}
角色状态：{status}

请生成 100-200 字续写，保留古白话风格。
""",
    "en-US": """# Narrative Continuation

Continue the story after player choice.

Player action: {action}
Current scene: {scene}
Character status: {status}

Generate 100-200 word continuation, preserving classical Chinese vernacular style (translated).
""",
}


def get_chapter_blueprint_prompt(locale: Locale, **vars) -> str:
    """获取章节蓝图 prompt"""
    template = CHAPTER_BLUEPRINT_PROMPTS[locale]
    return template.format(**vars)


def get_chapter_settlement_prompt(locale: Locale, **vars) -> str:
    """获取章节结算 prompt"""
    template = CHAPTER_SETTLEMENT_PROMPTS[locale]
    return template.format(**vars)


def get_narrative_continuation_prompt(locale: Locale, **vars) -> str:
    """获取叙事续写 prompt"""
    template = NARRATIVE_CONTINUATION_PROMPTS[locale]
    return template.format(**vars)


SUPPORTED_LOCALES: list[Locale] = ["zh-CN", "en-US"]
