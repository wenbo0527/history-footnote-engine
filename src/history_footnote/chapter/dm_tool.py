"""v2.8.0 段六 W18 章节制 LLM Tool（dm_tool）

设计目标：
- 把 ChapterFacade 的章节 LLM 功能包装为 LangChain Tool
- 让 dm_agent 在 round 中能调用 fill_chapter_blueprint
- 接 make_llm_for_purpose(purpose="chapter_init") 走温度 0
- 输出序列化 Blueprint → 引擎可识别

约束：
- 0 测试时打真 LLM（用 mock LLM）
- 兼容 v2.7 KV 缓存（共享同一 cache_control 块）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from history_footnote.chapter.types import ChapterBlueprint

_LOG = logging.getLogger("history_footnote.chapter.dm_tool")


def build_chapter_tool_prompt(
    state,
    chapter_id: int,
    era_config: dict,
) -> str:
    """构建喂给章节 LLM 的 prompt 字符串

    段六 W18：把 prompt_builder 的 dict 转成 LangChain Tool 输入的字符串
    """
    from history_footnote.chapter.prompt_builder import ChapterPromptBuilder
    from history_footnote.chapter.meta_resolver import ChapterMetaResolver

    # 元属性
    resolver = ChapterMetaResolver(era_config or {})
    meta = resolver.resolve(chapter_id)

    # 完整上下文
    builder = ChapterPromptBuilder(state, era_config or {})
    ctx = builder.build(meta)

    # 序列化为人类可读 prompt
    # 🆕 W32: 加 4 条 prompt 硬约束（避免 LLM markdown + 重复 + 标题不一致）
    prompt = (
        "你是历史注脚引擎的章节蓝图生成助手。请按以下约束生成第 {chapter_id} 章的蓝图 JSON。\n\n"
        "## 🆕 W32 硬约束（不可违反）\n"
        "- **禁用 markdown 标记**：所有 JSON 字符串值内**不得**出现 `**`、`*`、`#`、反引号、链接语法\n"
        "- **章节标题不得重复**：本章节 chapter_title 必须与上一章不同（防重复）\n"
        "- **chapter_subtitle 不得为空**：必须 4-12 字文言短语\n"
        "- **transition_hint 必填**：必为 season/relationship/identity 之一\n\n"
        "## 硬约束（不可改）\n"
        "- act: {act}\n"
        "- role: {role}\n"
        "- emotion_tone: {emotion_tone}\n"
        "- choice_type: {choice_type}\n"
        "- 节点数: 3-5 个（建议 4 个）\n"
        "- 节点角色顺序: 第 1 个 introduction, 最后 1 个 resolution, 中间是 escalation/climax\n\n"
        "## 历史摘要（全部）\n{history}\n\n"
        "## 增量规则（focus_points）\n{focus}\n\n"
        "## 玩家画像\n- build: {build}\n- value_dimensions: {vd}\n- active_paths: {paths}\n\n"
        "## 可用资源\n- NPCs: {npcs}\n- 知识条目: {knowledge}\n\n"
        "## 输出格式（严格 JSON，无任何 markdown 污染）\n"
        "{{\n"
        '  "chapter_title": "古白话标题（4-8字，独特）",\n'
        '  "chapter_subtitle": "副标题（4-12字文言）",\n'
        '  "transition_hint": "season",\n'
        '  "nodes": [\n'
        '    {{"index": 1, "role": "introduction", "scene": "纯古白话场景", "npc_ids": [...], "option_directions": [...], "completion_condition": "..."}},\n'
        "    ...\n"
        "  ]\n"
        "}}\n"
    ).format(
        chapter_id=chapter_id,
        act=ctx["chapter_meta"]["act"],
        role=ctx["chapter_meta"]["role"],
        emotion_tone=ctx["chapter_meta"]["emotion_tone"],
        choice_type=ctx["chapter_meta"]["choice_type"],
        history=json.dumps(ctx["chapter_history"], ensure_ascii=False, indent=2),
        focus="\n".join(f"- {f}" for f in ctx["focus_points"]),
        build=ctx["player"].get("build", ""),
        vd=json.dumps(ctx["player"].get("value_dimensions", {}), ensure_ascii=False),
        paths=ctx["player"].get("active_paths", []),
        npcs=", ".join(ctx["available_npcs"][:10]),
        knowledge=", ".join(ctx["available_knowledge"][:15]),
    )
    return prompt


def fill_chapter_blueprint_via_llm(
    state,
    chapter_id: int,
    era_config: dict,
    llm_callable,
    chapter_facade,
) -> Optional[ChapterBlueprint]:
    """通过真 LLM 生成章节蓝图（段六 W18 主入口）

    流程：
    1. build_chapter_tool_prompt 构建 prompt
    2. llm_callable(prompt) 调用真 LLM（temperature=0）
    3. 解析 LLM 输出（提取 JSON）
    4. chapter_facade.convert_llm_to_blueprint(llm_output) 校验+兑底+Build分化
    5. 返回 ChapterBlueprint

    Args:
        state: GameState
        chapter_id: 章节序号
        era_config: era.json 配置
        llm_callable: LangChain LLM 实例（已温度 0）
        chapter_facade: ChapterFacade 实例

    Returns:
        ChapterBlueprint 或 None（失败）
    """
    try:
        # 1. 构建 prompt
        prompt = build_chapter_tool_prompt(state, chapter_id, era_config)

        # 2. 调 LLM
        from langchain_core.messages import HumanMessage
        response = llm_callable.invoke([HumanMessage(content=prompt)])
        raw_text = response.content if hasattr(response, "content") else str(response)

        # 3. 提取 JSON（extract_json_from_text 返回字符串，需 json.loads）
        from history_footnote.narrative_sanitizer import extract_json_from_text
        json_str = extract_json_from_text(raw_text)
        if json_str is None:
            _LOG.error("LLM 输出无法提取 JSON: %s", raw_text[:100])
            return chapter_facade.init_chapter(chapter_id)
        try:
            llm_output = json.loads(json_str)
        except json.JSONDecodeError as e:
            _LOG.error("LLM JSON 解析失败: %s", e)
            return chapter_facade.init_chapter(chapter_id)
        if not isinstance(llm_output, dict):
            _LOG.error("LLM 输出不是 dict: %s", type(llm_output).__name__)
            return chapter_facade.init_chapter(chapter_id)

        # 4. 校验+兑底+Build分化
        blueprint = chapter_facade.convert_llm_to_blueprint(
            llm_output, chapter_id=chapter_id,
        )
        _LOG.info(
            "fill_chapter_blueprint_via_llm: chapter=%d, nodes=%d",
            chapter_id, len(blueprint.nodes),
        )
        return blueprint

    except Exception as e:
        _LOG.error("fill_chapter_blueprint_via_llm 失败: %s，回退硬编码", e)
        return chapter_facade.init_chapter(chapter_id)


# ============= 🆕 v2.8.0 段六+ W20 章节摘要 LLM =============

def build_chapter_summary_prompt(
    chapter_id: int,
    core_event: str,
    key_choice: str,
    build_summary: str,
    path_summary: str,
    era_config: Optional[dict] = None,
) -> str:
    """构建喂给章节摘要 LLM 的 prompt

    Args:
        chapter_id: 章节序号
        core_event: 核心事件（来自 Settlement._extract_core_event）
        key_choice: 关键选择（来自 Settlement._extract_key_choice）
        build_summary: Build 画像（来自 Settlement._extract_build_summary）
        path_summary: 当前路径（来自 Settlement._extract_path_summary）
        era_config: era.json 配置（可选，提供时代背景）

    Returns:
        str: 喂给 LLM 的 prompt
    """
    era_bg = ""
    if era_config:
        era_name = era_config.get("era_name", "万历十五年")
        era_location = era_config.get("primary_location", "江南")
        era_bg = f"\n## 时代背景\n- 时代: {era_name}\n- 主场景: {era_location}\n"

    return (
        f"你是历史注脚引擎的章节摘要生成助手。请用 100-200 字总结第 {chapter_id} 章。\n\n"
        f"## 必填内容（必须覆盖）\n"
        f"1. **核心事件**: {core_event}\n"
        f"2. **关键选择**: {key_choice}\n"
        f"3. **玩家画像**: {build_summary}\n"
        f"4. **当前路径**: {path_summary}\n"
        f"{era_bg}\n"
        f"## 输出要求\n"
        f"- 100-200 字\n"
        f"- 用古典白话语调（不要现代口语）\n"
        f"- 自然融入 4 必填项，不要列表\n"
        f"- 输出纯文本摘要（不要 JSON）\n\n"
        f"## 章节摘要（100-200 字）\n"
    )


def fill_chapter_summary_via_llm(
    state,
    chapter_id: int,
    core_event: str,
    key_choice: str,
    build_summary: str,
    path_summary: str,
    era_config: Optional[dict],
    llm_callable,
    max_words: int = 200,
) -> str:
    """通过真 LLM 生成章节摘要（v2.8.0 段六+ W20）

    Args:
        state: GameState
        chapter_id: 章节序号
        core_event / key_choice / build_summary / path_summary: 4 必填项
        era_config: era.json 配置
        llm_callable: LangChain LLM 实例
        max_words: 摘要最大字数（默认 200）

    Returns:
        str: 章节摘要（< max_words 字）

    Raises:
        Exception: LLM 调用失败时（让外层 fallback 到规则压缩）
    """
    # 1. 构建 prompt
    prompt = build_chapter_summary_prompt(
        chapter_id=chapter_id,
        core_event=core_event,
        key_choice=key_choice,
        build_summary=build_summary,
        path_summary=path_summary,
        era_config=era_config,
    )

    # 2. 调 LLM
    from langchain_core.messages import HumanMessage
    response = llm_callable.invoke([HumanMessage(content=prompt)])
    raw_text = response.content if hasattr(response, "content") else str(response)

    # 3. 截断到 max_words
    summary = raw_text.strip()
    if len(summary) > max_words:
        summary = summary[:max_words - 3] + "..."

    _LOG.info(
        "fill_chapter_summary_via_llm: chapter=%d, summary=%d 字",
        chapter_id, len(summary),
    )
    return summary
