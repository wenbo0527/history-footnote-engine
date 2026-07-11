"""🆕 v2.8.x W34: chapter 子系统公共 API

提供章节制叙事体系的 25 个核心组件的统一入口：

使用：
    from history_footnote.chapter import (
        ChapterCoordinator,
        fill_chapter_blueprint_via_llm,
        extract_json_from_text,
    )
"""
from history_footnote.chapter.types import (
    ActType,
    NodeRole,
    TransitionType,
    ClosureStatus,
    ChapterState,
    BlueprintNode,
    ChapterBlueprint,
    ChapterMeta,
)
from history_footnote.chapter.paths import PathStatus, PathState
from history_footnote.chapter.plates import PlateStatus, PlateState
from history_footnote.chapter.coordinator import ChapterCoordinator
from history_footnote.chapter.meta_resolver import ChapterMetaResolver, DEFAULT_HERO_JOURNEY_ACTS
from history_footnote.chapter.plates import PlateRegistry, Plate, Corridor, PlateType, TransmissionRule
from history_footnote.chapter.plate_engine import PlateEngine
from history_footnote.chapter.path_switcher import PathSwitcher
from history_footnote.chapter.settlement import settle_chapter
from history_footnote.chapter.fallback import fallback_chapter_blueprint
from history_footnote.chapter.validator import validate_chapter_output
from history_footnote.chapter.schema_converter import (
    convert_llm_to_blueprint,
    apply_build_differentiation,
)
from history_footnote.chapter.prompt_builder import build_chapter_prompt_context
from history_footnote.chapter.dm_tool import (
    fill_chapter_blueprint_via_llm,
    fill_chapter_summary_via_llm,
)

# 🆕 W34: LangChain Tool 包装（langchain_core 可用时才有）
try:
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    _HAS_LC_TOOLS = True
except ImportError:
    _HAS_LC_TOOLS = False
    make_chapter_dm_tools = None  # type: ignore

# 🆕 W34: narrative_sanitizer 公共导出
from history_footnote.narrative_sanitizer import (
    extract_json_from_text,
    _strip_markdown_bold_in_json,
    _strip_control_chars,
    _fix_truncated_json_brackets,
)

__all__ = [
    # 类型 (types.py)
    "ActType",
    "NodeRole",
    "TransitionType",
    "ClosureStatus",
    "ChapterState",
    "BlueprintNode",
    "ChapterBlueprint",
    "ChapterMeta",
    # 路径 (paths.py)
    "PathStatus",
    "PathState",
    # 板块 (plates.py)
    "PlateStatus",
    "PlateState",
    "PlateRegistry",
    "Plate",
    "Corridor",
    "PlateType",
    "TransmissionRule",
    # 引擎
    "ChapterCoordinator",
    "ChapterMetaResolver",
    "DEFAULT_HERO_JOURNEY_ACTS",
    # 🆕 W36: 自适应 API 在 ChapterMetaResolver 实例上（total_chapters/is_last_chapter/remaining_chapters）
    "PlateEngine",
    "PathSwitcher",
    # 检查
    "settle_chapter",
    # 容错
    "fallback_chapter_blueprint",
    # 验证
    "validate_chapter_output",
    # Schema
    "convert_llm_to_blueprint",
    "apply_build_differentiation",
    # Prompt
    "build_chapter_prompt_context",
    # LLM
    "fill_chapter_blueprint_via_llm",
    "fill_chapter_summary_via_llm",
    # Tool 包装
    "make_chapter_dm_tools",
    "_HAS_LC_TOOLS",
    # Sanitizer
    "extract_json_from_text",
    "_strip_markdown_bold_in_json",
    "_strip_control_chars",
    "_fix_truncated_json_brackets",
]

__version__ = "2.8.x"
