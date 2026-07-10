"""v2.8.0 段五 W15 单元测试

测试目标：
1. Plate 序列化 + get_status
2. PlateStatus.from_tension 4 状态推断
3. Corridor / TransmissionRule 序列化
4. PlateState 序列化 + set_tension 自动更新 status
5. PlateRegistry 从 plates.json 加载
6. GameState.plate_state 字段

约束：
- 0 LLM 调用
- 不影响现有 182 测试
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.plates import (
    Plate,
    PlateState,
    PlateRegistry,
    PlateStatus,
    PlateType,
    Corridor,
    TransmissionRule,
)


def load_plates_json() -> dict:
    plates_path = Path(__file__).parent.parent / "eras" / "wanli1587" / "plates.json"
    return json.loads(plates_path.read_text(encoding="utf-8"))


# ============= 测试 1：Plate 序列化 + get_status =============

def test_V28_145_plate_serialization():
    """Plate dataclass 序列化"""
    plate = Plate(
        id="jiangnan",
        name="江南",
        type="core",
        neighbors=["central_plains", "hexi_corridor"],
        base_tension=0.4,
        description="丝绸与赋税之地",
    )
    data = plate.to_dict()
    plate2 = Plate.from_dict(data)
    assert plate2.id == "jiangnan"
    assert plate2.type == "core"
    assert plate2.neighbors == ["central_plains", "hexi_corridor"]
    assert plate2.base_tension == 0.4
    return True


def test_V28_146_plate_get_status_by_tension():
    """Plate.get_status 按当前张力推断 4 状态"""
    plate = Plate(id="test", base_tension=0.0)
    assert plate.get_status(0.1) == "stable"
    assert plate.get_status(0.5) == "tense"
    assert plate.get_status(0.8) == "shifting"
    assert plate.get_status(0.95) == "collapsed"
    return True


# ============= 测试 3：Corridor / TransmissionRule 序列化 =============

def test_V28_147_corridor_serialization():
    """Corridor 序列化"""
    corridor = Corridor(id="grand_canal", from_plate="central_plains", to_plate="jiangnan", type="trade")
    data = corridor.to_dict()
    c2 = Corridor.from_dict(data)
    assert c2.id == "grand_canal"
    assert c2.type == "trade"
    return True


def test_V28_148_transmission_rule_serialization():
    """TransmissionRule 序列化（支持 from/to 字段别名）"""
    rule = TransmissionRule(from_plate="central_plains", to_plate="jiangnan", factor=0.3, delay_rounds=2)
    data = rule.to_dict()
    # 反序列化用 "from" 字段
    data2 = {"from": "central_plains", "to": "jiangnan", "factor": 0.3, "delay_rounds": 2}
    rule2 = TransmissionRule.from_dict(data2)
    assert rule2.from_plate == "central_plains"
    assert rule2.to_plate == "jiangnan"
    assert rule2.factor == 0.3
    assert rule2.delay_rounds == 2
    return True


# ============= 测试 4：PlateState 序列化 + set_tension =============

def test_V28_149_plate_state_serialization():
    """PlateState 序列化"""
    ps = PlateState(
        tensions={"jiangnan": 0.5, "central_plains": 0.3},
        statuses={"jiangnan": "tense", "central_plains": "stable"},
        equilibrium_baseline={"jiangnan": 0.4, "central_plains": 0.3},
    )
    data = ps.to_dict()
    ps2 = PlateState.from_dict(data)
    assert ps2.tensions["jiangnan"] == 0.5
    assert ps2.statuses["jiangnan"] == "tense"
    return True


def test_V28_150_plate_state_set_tension():
    """PlateState.set_tension 自动更新 status + 截断 0-1"""
    ps = PlateState()
    ps.set_tension("central_plains", 0.8)  # → shifting
    assert ps.tensions["central_plains"] == 0.8
    assert ps.statuses["central_plains"] == "shifting"
    # 截断
    ps.set_tension("central_plains", 1.5)  # → 1.0
    assert ps.tensions["central_plains"] == 1.0
    assert ps.statuses["central_plains"] == "collapsed"
    # 负值截断
    ps.set_tension("central_plains", -0.5)  # → 0.0
    assert ps.tensions["central_plains"] == 0.0
    return True


def test_V28_151_plate_state_add_shift_event_limit():
    """PlateState.add_shift_event 保留最近 10 条"""
    ps = PlateState()
    for i in range(15):
        ps.add_shift_event({"round": i, "event": f"event_{i}"})
    assert len(ps.shift_events) == 10
    assert ps.shift_events[0]["round"] == 5  # 前 5 条被淘汰
    assert ps.shift_events[-1]["round"] == 14
    return True


# ============= 测试 5：PlateRegistry 从 plates.json 加载 =============

def test_V28_152_plate_registry_loads_from_json():
    """PlateRegistry 从 plates.json 加载"""
    era_config = {"plates": load_plates_json()}
    registry = PlateRegistry(era_config)
    assert len(registry) == 4, f"期望 4 板块，实际 {len(registry)}"
    assert "central_plains" in registry
    assert "jiangnan" in registry
    assert "hexi_corridor" in registry
    assert "northwest" in registry
    return True


def test_V28_153_plate_registry_query_by_type():
    """PlateRegistry.get_by_type 分类查询"""
    era_config = {"plates": load_plates_json()}
    registry = PlateRegistry(era_config)
    cores = registry.get_core_plates()
    peripherals = registry.get_peripheral_plates()
    corridors = registry.get_corridor_plates()
    assert len(cores) == 2  # central_plains + jiangnan
    assert len(peripherals) == 1  # northwest
    assert len(corridors) == 1  # hexi_corridor
    return True


def test_V28_154_plate_registry_initialize_state():
    """PlateRegistry.initialize_state 用 equilibrium_state 初始化"""
    era_config = {"plates": load_plates_json()}
    registry = PlateRegistry(era_config)
    state = registry.initialize_state()
    assert state.tensions["central_plains"] == 0.3
    assert state.tensions["jiangnan"] == 0.4
    assert state.tensions["hexi_corridor"] == 0.2
    assert state.tensions["northwest"] == 0.5
    # status 自动推断
    assert state.statuses["central_plains"] == "stable"
    assert state.statuses["northwest"] == "tense"  # 0.5 → tense
    # baseline
    assert state.equilibrium_baseline["central_plains"] == 0.3
    return True


def test_V28_155_plate_registry_transmission_rules():
    """PlateRegistry.get_transmission_rules_from"""
    era_config = {"plates": load_plates_json()}
    registry = PlateRegistry(era_config)
    rules = registry.get_transmission_rules()
    assert len(rules) == 3
    rules_from_cp = registry.get_transmission_rules_from("central_plains")
    assert len(rules_from_cp) == 2  # to jiangnan + to northwest
    return True


# ============= 测试 6：GameState.plate_state 字段 =============

def test_V28_156_game_state_has_plate_state():
    """GameState 有 plate_state 字段"""
    from history_footnote.game_state import GameState
    gs = GameState()
    assert hasattr(gs, "plate_state")
    assert isinstance(gs.plate_state, PlateState)
    assert gs.plate_state.tensions == {}
    return True


def test_V28_157_plate_status_enum_string_compatibility():
    """PlateStatus.from_string 容错"""
    assert PlateStatus.from_string("stable") == PlateStatus.STABLE
    assert PlateStatus.from_string("tense") == PlateStatus.TENSE
    assert PlateStatus.from_string("shifting") == PlateStatus.SHIFTING
    assert PlateStatus.from_string("collapsed") == PlateStatus.COLLAPSED
    assert PlateStatus.from_string("invalid") == PlateStatus.STABLE  # 回退

    assert PlateType.from_string("core") == PlateType.CORE
    assert PlateType.from_string("invalid") == PlateType.PERIPHERAL
    return True


def test_V28_158_real_plates_json_integration():
    """集成：真实 plates.json 加载 + 完整状态"""
    era_config = {"plates": load_plates_json()}
    registry = PlateRegistry(era_config)
    state = registry.initialize_state()

    # 模拟张江中央升高 → 传导到江南
    state.set_tension("central_plains", 0.7)  # → shifting
    assert state.get_status("central_plains") == "shifting"
    # pending_transmission 应记录（中→江，factor 0.3，delay 2）
    state.add_pending_transmission("central_plains", "jiangnan", 0.3, round_num=10)
    assert len(state.pending_transmissions) == 1
    return True
