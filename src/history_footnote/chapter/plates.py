"""v2.8.0 段五 W15 板块系统（Plates）

设计目标：
- Plate：一个宏观政治经济板块（如江南/中央/河西）
- PlateState：嵌套 dataclass 存运行时板块状态
- PlateRegistry：从 era_config.plates 加载所有板块
- 4 状态：stable / tense / shifting / collapsed

约束：
- 0 LLM 调用
- 纯数据建模
- 旧存档零回归

数据结构（era.json.plates 字段）：
{
  "plate_definitions": [
    {
      "id": "central_plains",
      "name": "中原",
      "type": "core",                   # core / peripheral / corridor
      "neighbors": ["jiangnan", "hexi_corridor"],
      "base_tension": 0.3,              # 0-1
      "description": "..."
    }
  ],
  "corridors": [
    {
      "id": "grand_canal",
      "from_plate": "central_plains",
      "to_plate": "jiangnan",
      "type": "trade"
    }
  ],
  "equilibrium_state": {
    "central_plains": 0.3,
    "jiangnan": 0.5,
    "hexi_corridor": 0.2
  },
  "transmission_rules": [
    {
      "from": "central_plains",
      "to": "jiangnan",
      "factor": 0.3,                    # 张力传导系数
      "delay_rounds": 2
    }
  ]
}
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

_LOG = logging.getLogger("history_footnote.chapter.plates")


# ============= 枚举 =============

class PlateStatus(str, Enum):
    """板块 4 状态"""
    STABLE = "stable"          # 张力 < 0.4
    TENSE = "tense"            # 0.4 ≤ 张力 < 0.7
    SHIFTING = "shifting"      # 0.7 ≤ 张力 < 0.9（板块格局变动中）
    COLLAPSED = "collapsed"    # 张力 ≥ 0.9（板块瓦解）

    @classmethod
    def from_tension(cls, tension: float) -> "PlateStatus":
        """从张力值推断状态"""
        if tension < 0.4:
            return cls.STABLE
        if tension < 0.7:
            return cls.TENSE
        if tension < 0.9:
            return cls.SHIFTING
        return cls.COLLAPSED

    @classmethod
    def from_string(cls, value: str) -> "PlateStatus":
        try:
            return cls(value)
        except ValueError:
            return cls.STABLE


class PlateType(str, Enum):
    """板块类型"""
    CORE = "core"              # 核心板块
    PERIPHERAL = "peripheral"  # 边缘板块
    CORRIDOR = "corridor"      # 走廊板块

    @classmethod
    def from_string(cls, value: str) -> "PlateType":
        try:
            return cls(value)
        except ValueError:
            return cls.PERIPHERAL


# ============= Plate（板块定义） =============

@dataclass
class Plate:
    """板块定义——一个宏观政治经济板块"""

    id: str
    name: str = ""
    type: str = "peripheral"  # core / peripheral / corridor
    neighbors: list[str] = field(default_factory=list)
    base_tension: float = 0.3  # 基础张力（0-1）
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Plate":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", "peripheral"),
            neighbors=data.get("neighbors", []) or [],
            base_tension=float(data.get("base_tension", 0.3)),
            description=data.get("description", ""),
        )

    def get_status(self, tension: float) -> str:
        """从当前张力推断状态"""
        return PlateStatus.from_tension(tension).value


# ============= Corridor（走廊） =============

@dataclass
class Corridor:
    """走廊定义——两个板块之间的连接"""

    id: str
    from_plate: str
    to_plate: str
    type: str = "trade"  # trade / military / cultural

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Corridor":
        return cls(
            id=data.get("id", ""),
            from_plate=data.get("from_plate", ""),
            to_plate=data.get("to_plate", ""),
            type=data.get("type", "trade"),
        )


# ============= TransmissionRule（传导规则） =============

@dataclass
class TransmissionRule:
    """张力传导规则"""

    from_plate: str
    to_plate: str
    factor: float = 0.3  # 传导系数 0-1
    delay_rounds: int = 2  # 延迟回合数

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TransmissionRule":
        return cls(
            from_plate=data.get("from", data.get("from_plate", "")),
            to_plate=data.get("to", data.get("to_plate", "")),
            factor=float(data.get("factor", 0.3)),
            delay_rounds=int(data.get("delay_rounds", 2)),
        )


# ============= PlateState（运行时状态） =============

@dataclass
class PlateState:
    """板块运行时状态——嵌套在 GameState.plate_state

    字段：
    - tensions：各板块当前张力 {plate_id: tension_float}
    - statuses：各板块当前状态 {plate_id: status_string}
    - equilibrium_baseline：均衡基线 {plate_id: tension_float}
    - shift_events：板块格局变动事件历史（最近 10 条）
    - pending_transmissions：待传导的张力事件 [(from, to, factor, round)]
    """

    tensions: dict = field(default_factory=dict)
    statuses: dict = field(default_factory=dict)
    equilibrium_baseline: dict = field(default_factory=dict)
    shift_events: list[dict] = field(default_factory=list)
    pending_transmissions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PlateState":
        if data is None:
            return cls()
        return cls(
            tensions=data.get("tensions", {}) or {},
            statuses=data.get("statuses", {}) or {},
            equilibrium_baseline=data.get("equilibrium_baseline", {}) or {},
            shift_events=data.get("shift_events", []) or [],
            pending_transmissions=data.get("pending_transmissions", []) or [],
        )

    def get_tension(self, plate_id: str) -> float:
        """查询某板块当前张力"""
        return float(self.tensions.get(plate_id, 0.0))

    def get_status(self, plate_id: str) -> str:
        """查询某板块当前状态"""
        if plate_id in self.statuses:
            return self.statuses[plate_id]
        # 未记录：按张力推断
        return PlateStatus.from_tension(self.get_tension(plate_id)).value

    def set_tension(self, plate_id: str, tension: float) -> None:
        """设置某板块张力（自动更新 status）"""
        tension = max(0.0, min(1.0, tension))  # 截断 0-1
        self.tensions[plate_id] = tension
        self.statuses[plate_id] = PlateStatus.from_tension(tension).value

    def add_shift_event(self, event: dict) -> None:
        """添加板块变动事件（保留最近 10 条）"""
        self.shift_events.append(event)
        if len(self.shift_events) > 10:
            self.shift_events = self.shift_events[-10:]

    def add_pending_transmission(self, from_p: str, to_p: str, factor: float, round_num: int) -> None:
        """添加待传导事件"""
        self.pending_transmissions.append({
            "from": from_p,
            "to": to_p,
            "factor": factor,
            "round": round_num,
        })


# ============= PlateRegistry（注册表） =============

class PlateRegistry:
    """板块注册表——从 era_config 加载所有 Plate/Corridor/TransmissionRule

    用法：
        registry = PlateRegistry(era_config)
        plate = registry.get_plate("jiangnan")
        all_cores = registry.get_by_type("core")
    """

    def __init__(self, era_config: dict):
        self.era_config = era_config
        self._plates: dict[str, Plate] = {}
        self._corridors: dict[str, Corridor] = {}
        self._transmission_rules: list[TransmissionRule] = []
        self._load()

    def _load(self) -> None:
        """从 era_config.plates 加载"""
        plates = self.era_config.get("plates", {}) or {}
        # 板块定义
        for p in plates.get("plate_definitions", []) or []:
            if isinstance(p, dict) and p.get("id"):
                plate = Plate.from_dict(p)
                self._plates[plate.id] = plate
        # 走廊
        for c in plates.get("corridors", []) or []:
            if isinstance(c, dict) and c.get("id"):
                corridor = Corridor.from_dict(c)
                self._corridors[corridor.id] = corridor
        # 传导规则
        for r in plates.get("transmission_rules", []) or []:
            if isinstance(r, dict):
                rule = TransmissionRule.from_dict(r)
                self._transmission_rules.append(rule)
        _LOG.info(
            "PlateRegistry 加载 %d 板块 + %d 走廊 + %d 传导规则",
            len(self._plates), len(self._corridors), len(self._transmission_rules),
        )

    # ============= 查询 =============

    def get_plate(self, plate_id: str) -> Optional[Plate]:
        return self._plates.get(plate_id)

    def get_all_plates(self) -> list[Plate]:
        return list(self._plates.values())

    def get_by_type(self, plate_type: str) -> list[Plate]:
        return [p for p in self._plates.values() if p.type == plate_type]

    def get_core_plates(self) -> list[Plate]:
        return self.get_by_type("core")

    def get_peripheral_plates(self) -> list[Plate]:
        return self.get_by_type("peripheral")

    def get_corridor_plates(self) -> list[Plate]:
        return self.get_by_type("corridor")

    def get_corridor(self, corridor_id: str) -> Optional[Corridor]:
        return self._corridors.get(corridor_id)

    def get_transmission_rules(self) -> list[TransmissionRule]:
        return list(self._transmission_rules)

    def get_transmission_rules_from(self, from_plate: str) -> list[TransmissionRule]:
        return [r for r in self._transmission_rules if r.from_plate == from_plate]

    # ============= 初始化 =============

    def initialize_state(self) -> PlateState:
        """用 equilibrium_state 初始化 PlateState"""
        eq = (self.era_config.get("plates", {}) or {}).get("equilibrium_state", {}) or {}
        tensions = {pid: float(v) for pid, v in eq.items()}
        statuses = {pid: PlateStatus.from_tension(v).value for pid, v in tensions.items()}
        return PlateState(
            tensions=tensions,
            statuses=statuses,
            equilibrium_baseline=tensions.copy(),
        )

    # ============= 工具 =============

    def __len__(self) -> int:
        return len(self._plates)

    def __contains__(self, plate_id: str) -> bool:
        return plate_id in self._plates


# ============= 工具函数 =============

def make_default_plate_state() -> PlateState:
    return PlateState()
