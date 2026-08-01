"""🆕 v2.10.16 Phase 10 — 故事模式（无 LLM 依赖）

公共 API:
- ScriptedStoryEngine: 主引擎
- get_engine(): 单例获取
- ScriptedChapter, ScriptedNode, ScriptedVoiceOption: 数据模型
"""
from history_footnote.story_mode.engine import ScriptedStoryEngine, get_engine
from history_footnote.story_mode.types import (
    ScriptedChapter,
    ScriptedNode,
    ScriptedVoiceOption,
)

__all__ = [
    "ScriptedStoryEngine",
    "get_engine",
    "ScriptedChapter",
    "ScriptedNode",
    "ScriptedVoiceOption",
]