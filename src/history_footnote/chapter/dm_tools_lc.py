"""🆕 v2.8.x W30: chapter_dm_tools — LangChain Tool 包装

把 dm_tool.py 的 fill_chapter_blueprint_via_llm + fill_chapter_summary_via_llm
包装为 LangChain @tool，让 dm_agent LangGraph 节点能自动调用：

  1. fill_chapter_blueprint (round 1)  → 生成章节蓝图
  2. fill_chapter_summary  (收束时)  → 生成章节摘要

约束：
- 必须传入 state（注入 facade 上下文）
- 容错：Tool 失败时返回 dict 不抛异常（dm_agent 容错用）
"""
import logging
from typing import Optional

_LOG = logging.getLogger("chapter.dm_tools_lc")


def make_chapter_dm_tools(state, facade, llm_callable, era_config):
    """构造章节制 2 个 LangChain Tool

    Args:
        state: GameState 实例
        facade: ChapterFacade 实例
        llm_callable: 章节 LLM（ChatAnthropic 等）
        era_config: era 配置

    Returns:
        list of LangChain tool objects（2 个）
    """
    try:
        from langchain_core.tools import tool
    except ImportError:
        _LOG.warning("langchain_core 不可用，跳过 Tool 包装")
        return []

    from history_footnote.chapter.dm_tool import (
        fill_chapter_blueprint_via_llm,
        fill_chapter_summary_via_llm,
    )

    # 闭合 state/facade/llm 引用
    _state = state
    _facade = facade
    _llm = llm_callable
    _era = era_config

    @tool
    def fill_chapter_blueprint(chapter: int) -> dict:
        """为指定章节生成 LLM 蓝图

        在章节第 1 回合前调用，生成 3-5 节点的章节蓝图（节点 scene +
        option_directions + npc_ids）。

        Args:
            chapter: 章节编号（1, 2, 3, ...）

        Returns:
            {
              "blueprint": {
                "chapter_id": int,
                "chapter_title": str,
                "chapter_subtitle": str,
                "nodes": [{"index", "role", "scene", "npc_ids", "option_directions"}],
                "meta": {"act", "role", "emotion_tone"}
              } | None,
              "fallback": bool  # 是否走了硬编码
            }
        """
        try:
            bp = fill_chapter_blueprint_via_llm(
                state=_state,
                facade=_facade,
                llm=_llm,
                era_config=_era,
                chapter=chapter,
            )
            return {
                "blueprint": bp,
                "fallback": bp is None or bp.get("via") == "fallback",
            }
        except Exception as e:
            _LOG.error("fill_chapter_blueprint Tool 失败: %s", e)
            return {"blueprint": None, "fallback": True, "error": str(e)}

    @tool
    def fill_chapter_summary(chapter: int) -> dict:
        """为指定章节生成 LLM 摘要

        在章节收束时调用，根据前章 history + 当前 chapter_state 生成
        100-200 字古白话章节摘要（用于章节历史展示 + 下章 prompt 注入）。

        Args:
            chapter: 章节编号（1, 2, 3, ...）

        Returns:
            {
              "summary": str,    # 100-200 字古白话
              "summary_len": int,
              "core_event": str,
              "key_choice": str,
              "build_summary": str,
              "path_summary": str
            } | {"error": str}  # 失败时
        """
        try:
            result = fill_chapter_summary_via_llm(
                state=_state,
                facade=_facade,
                llm=_llm,
                era_config=_era,
                chapter=chapter,
            )
            return result
        except Exception as e:
            _LOG.error("fill_chapter_summary Tool 失败: %s", e)
            return {"error": str(e), "summary": ""}

    return [fill_chapter_blueprint, fill_chapter_summary]
