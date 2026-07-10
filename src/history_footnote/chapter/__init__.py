"""🆕 v2.8.0 章节制叙事体系（Chapter System）

四层叙事体系中的 L2 章节层：
- L0 数据层：era.json + GameState（已有）
- L1 游玩层：回合内循环（已有）
- L2 章节层：章节制 LOOP（本包）
- L3 叙事层：英雄之旅元结构（段二/段三）

本包提供：
- types: ChapterState / ChapterBlueprint / BlueprintNode / 枚举
- closure: ChapterClosure（收束判定器）
- coordinator: ChapterCoordinator（协调器，给 game_loop 用）
- chapter_facade: ChapterFacade（v1.7.40 模式接入 game_engine_facade）

段一交付物（4 周）：
- types.py：嵌套 dataclass，不影响现有 200+ 字段
- chapter1_blueprint.json：硬编码第 1 章蓝图
- closure.py：复用 drama_manager 4 维度
- coordinator.py：game_loop 接入（pre_step/post_step/maybe_settle 3 钩子）
- chapter_facade.py：通过 GameEngineFacade.sub_facades["chapter"] 暴露

约束：
- 不改 game_loop._step_once 内部
- 不改 era.json（段一阶段）
- 不动 dm_agent / llm_wrapper / 现有 38 测试
"""
from history_footnote.chapter.types import (
    ChapterState,
    ChapterBlueprint,
    BlueprintNode,
    NodeRole,
    TransitionType,
    ClosureStatus,
)

__all__ = [
    "ChapterState",
    "ChapterBlueprint",
    "BlueprintNode",
    "NodeRole",
    "TransitionType",
    "ClosureStatus",
]
