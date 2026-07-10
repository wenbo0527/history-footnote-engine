"""v2.8.0 段三 W11 路径系统（Paths）

设计目标：
- NarrativePath：一条有方向/终点/解锁条件的叙事线
- PathRegistry：从 era_config.narrative.paths 加载所有路径
- PathState：嵌套 dataclass 存运行时路径状态（active_paths / completed_paths / locked_paths / path_affinity）
- 3 种状态：locked / active / dormant

约束：
- 0 LLM 调用
- 纯数据建模
- 旧存档零回归（PathState 默认空）

数据结构（era.json.narrative.paths 字段）：
[
  {
    "id": "main_tax_resistance",
    "type": "main",                     # main / side / corridor
    "name": "赋税抗争",
    "unlock_condition": "always",       # 简单条件
    "closure_condition": "tribute_negotiated",  # 简单条件
    "build_affinity": {"尽责": 0.8, "身边": 0.7},
    "chapters_applicable": [2, 3, 4, 5, 6],
    "plate_dependency": "central_plains",
    "description": "赋税越来越重..."
  },
  ...
]
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

_LOG = logging.getLogger("history_footnote.chapter.paths")


# ============= 枚举 =============

class PathStatus(str, Enum):
    """路径三态"""
    LOCKED = "locked"        # 未解锁，玩家不知道
    ACTIVE = "active"        # 已解锁，正在推进
    DORMANT = "dormant"      # 已解锁但不在焦点

    @classmethod
    def from_string(cls, value: str) -> "PathStatus":
        try:
            return cls(value)
        except ValueError:
            return cls.LOCKED


class PathType(str, Enum):
    """路径类型"""
    MAIN = "main"            # 主路径
    SIDE = "side"            # 支线
    CORRIDOR = "corridor"    # 跨板块路径

    @classmethod
    def from_string(cls, value: str) -> "PathType":
        try:
            return cls(value)
        except ValueError:
            return cls.SIDE


# ============= NarrativePath（路径定义） =============

@dataclass
class NarrativePath:
    """路径定义——一条叙事线

    字段：
    - id：唯一 ID
    - type：main / side / corridor
    - name：显示名
    - unlock_condition：解锁条件（简化为字符串或 dict，段三简化）
    - closure_condition：收束条件
    - build_affinity：Build 亲和度
    - chapters_applicable：适用章节列表
    - plate_dependency：依赖的板块（段五才用）
    - description：描述
    """

    id: str
    type: str = "side"
    name: str = ""
    unlock_condition: str = "always"  # 段三简化
    closure_condition: str = ""       # 段三简化
    build_affinity: dict = field(default_factory=dict)
    chapters_applicable: list[int] = field(default_factory=list)
    plate_dependency: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "NarrativePath":
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "side"),
            name=data.get("name", ""),
            unlock_condition=data.get("unlock_condition", "always"),
            closure_condition=data.get("closure_condition", ""),
            build_affinity=data.get("build_affinity", {}) or {},
            chapters_applicable=data.get("chapters_applicable", []) or [],
            plate_dependency=data.get("plate_dependency", ""),
            description=data.get("description", ""),
        )

    def is_applicable_to_chapter(self, chapter_id: int) -> bool:
        """是否适用于指定章节"""
        if not self.chapters_applicable:
            return True
        return chapter_id in self.chapters_applicable


# ============= PathState（运行时状态） =============

@dataclass
class PathState:
    """路径运行时状态——嵌套在 GameState.path_state

    字段：
    - active_paths：当前活跃路径 ID 列表
    - completed_paths：已完成的路径 ID 列表
    - locked_paths：未解锁的路径 ID 列表
    - dormant_paths：已解锁但休眠的路径 ID 列表
    - path_affinity：各路径的亲和度（0-1）
    - main_path_focus：当前主路径焦点（active_paths 中第一条）
    """

    active_paths: list[str] = field(default_factory=list)
    completed_paths: list[str] = field(default_factory=list)
    locked_paths: list[str] = field(default_factory=list)
    dormant_paths: list[str] = field(default_factory=list)
    path_affinity: dict = field(default_factory=dict)
    main_path_focus: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PathState":
        if data is None:
            return cls()
        return cls(
            active_paths=data.get("active_paths", []) or [],
            completed_paths=data.get("completed_paths", []) or [],
            locked_paths=data.get("locked_paths", []) or [],
            dormant_paths=data.get("dormant_paths", []) or [],
            path_affinity=data.get("path_affinity", {}) or {},
            main_path_focus=data.get("main_path_focus", ""),
        )

    def get_status(self, path_id: str) -> str:
        """查询路径状态"""
        if path_id in self.completed_paths:
            return PathStatus.DORMANT.value  # completed 视为 dormant 变体
        if path_id in self.active_paths:
            return PathStatus.ACTIVE.value
        if path_id in self.dormant_paths:
            return PathStatus.DORMANT.value
        return PathStatus.LOCKED.value


# ============= PathRegistry（注册表） =============

class PathRegistry:
    """路径注册表——从 era_config 加载所有 NarrativePath

    用法：
        registry = PathRegistry(era_config)
        path = registry.get("main_tax_resistance")
        all_active = registry.get_active_in_chapter(5)
    """

    def __init__(self, era_config: dict):
        self.era_config = era_config
        self._paths: dict[str, NarrativePath] = {}
        self._load()

    def _load(self) -> None:
        """从 era_config.narrative.paths 加载路径"""
        narrative = self.era_config.get("narrative", {}) or {}
        paths = narrative.get("paths", []) or []
        for p in paths:
            if isinstance(p, dict) and p.get("id"):
                path = NarrativePath.from_dict(p)
                self._paths[path.id] = path
        _LOG.info("PathRegistry 加载 %d 条路径", len(self._paths))

    # ============= 查询 =============

    def get(self, path_id: str) -> Optional[NarrativePath]:
        """按 ID 查询"""
        return self._paths.get(path_id)

    def get_all(self) -> list[NarrativePath]:
        """所有路径"""
        return list(self._paths.values())

    def get_by_type(self, path_type: str) -> list[NarrativePath]:
        """按类型查询"""
        return [p for p in self._paths.values() if p.type == path_type]

    def get_applicable_to_chapter(self, chapter_id: int) -> list[NarrativePath]:
        """适用于指定章节的路径"""
        return [p for p in self._paths.values() if p.is_applicable_to_chapter(chapter_id)]

    def get_main_paths(self) -> list[NarrativePath]:
        """所有 main 类型路径"""
        return self.get_by_type("main")

    def get_side_paths(self) -> list[NarrativePath]:
        """所有 side 类型路径"""
        return self.get_by_type("side")

    def get_corridor_paths(self) -> list[NarrativePath]:
        """所有 corridor 类型路径"""
        return self.get_by_type("corridor")

    # ============= 工具 =============

    def __len__(self) -> int:
        return len(self._paths)

    def __contains__(self, path_id: str) -> bool:
        return path_id in self._paths


# ============= 工具函数 =============

def make_default_path_state() -> PathState:
    """创建默认 PathState（v2.8.0 初始化用）"""
    return PathState()
