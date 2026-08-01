"""🆕 v2.10.24 — 章节加载器

统一管理所有章节 (chapter_01/02/03), 提供:
- 单例缓存
- 显式刷新
- 章节元信息查询
"""
from __future__ import annotations

import logging
from typing import Optional

from history_footnote.story_mode.constants import CHAPTER_INFO
from history_footnote.story_mode.types import ScriptedChapter

logger = logging.getLogger(__name__)


# 全局单例缓存
_chapter_cache: dict[int, ScriptedChapter] = {}


def get_chapter(chapter_id: int) -> ScriptedChapter:
    """获取章节 (单例缓存)

    chapter_id:
    - 1 = 家贫
    - 2 = 织染
    - 3 = 丝绢案
    - 其他 = 兜底到 ch1
    """
    if chapter_id in _chapter_cache:
        return _chapter_cache[chapter_id]

    # 懒加载 (避免循环导入)
    if chapter_id == 1:
        from history_footnote.story_mode.chapter_01 import get_chapter_01
        chapter = get_chapter_01()
    elif chapter_id == 2:
        from history_footnote.story_mode.chapter_02 import get_chapter_02
        chapter = get_chapter_02()
    elif chapter_id == 3:
        from history_footnote.story_mode.chapter_03 import get_chapter_03
        chapter = get_chapter_03()
    else:
        logger.warning(f"unknown chapter_id={chapter_id}, falling back to ch1")
        from history_footnote.story_mode.chapter_01 import get_chapter_01
        chapter = get_chapter_01()

    _chapter_cache[chapter_id] = chapter
    return chapter


def clear_cache() -> None:
    """清空章节缓存 (用于测试或热加载)"""
    _chapter_cache.clear()


def list_chapters() -> list[dict]:
    """列出所有章节的元信息 (前端用)

    返回 list[{id, title, subtitle, description, theme, ...}]
    """
    from history_footnote.story_mode.types import ScriptedChapter

    result = []
    for ch_id, info in sorted(CHAPTER_INFO.items()):
        try:
            ch = get_chapter(ch_id)
            result.append({
                "id": ch_id,
                **info,
                "nodes": len(ch.nodes),
                "options": sum(len(n.voice_options) for n in ch.nodes.values()),
                "endings": len(ch.end_node_ids),
                "encounters": len(ch.random_encounters or []),
            })
        except Exception as e:
            logger.warning(f"failed to load chapter {ch_id}: {e}")
            result.append({"id": ch_id, **info, "error": str(e)})
    return result


def get_chapter_info(chapter_id: int) -> Optional[dict]:
    """获取单个章节的元信息"""
    info = CHAPTER_INFO.get(chapter_id)
    if not info:
        return None
    try:
        ch = get_chapter(chapter_id)
        return {
            "id": chapter_id,
            **info,
            "nodes": len(ch.nodes),
            "options": sum(len(n.voice_options) for n in ch.nodes.values()),
            "endings": len(ch.end_node_ids),
            "encounters": len(ch.random_encounters or []),
        }
    except Exception as e:
        return {"id": chapter_id, **info, "error": str(e)}