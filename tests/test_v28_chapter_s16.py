"""v2.8.0 段五 W16 单元测试

测试目标：
1. PlateEngine.tick 推进一回合（衰减 + 传导 + 检测）
2. _process_pending_transmissions 到期传导
3. _detect_shift_events 阈值检测
4. _decay_to_baseline 自然衰减
5. boost_tension 手动修改张力

约束：
- 0 LLM 调用
- 不影响现有 196 测试
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.plates import PlateRegistry, PlateStatus
from history_footnote.chapter.plate_engine import PlateEngine, PlateShiftEvent, SHIFT_THRESHOLD


def make_engine():
    from history_footnote.game_state import GameState
    plates_path = Path(__file__).parent.parent / "eras" / "wanli1587" / "plates.json"
    era_config = {"plates": json.loads(plates_path.read_text(encoding="utf-8"))}
    state = GameState()
    state.era_id = "wanli1587"
    registry = PlateRegistry(era_config)
    state.plate_state = registry.initialize_state()
    return state, registry, PlateEngine(state, registry)


# ============= 测试 1：tick 推进一回合 =============

def test_V28_159_engine_tick_returns_list():
    """PlateEngine.tick 返回 PlateShiftEvent 列表"""
    state, registry, engine = make_engine()
    events = engine.tick(current_round=1)
    assert isinstance(events, list)
    # 初始状态无 shift 事件
    assert len(events) == 0
    return True


def test_V28_160_engine_tick_decays_to_baseline():
    """PlateEngine.tick 自然衰减（向 baseline 回归）"""
    state, registry, engine = make_engine()
    # 手动设置 jiangnan tension = 0.6（高于 baseline 0.4）
    state.plate_state.set_tension("jiangnan", 0.6)
    assert state.plate_state.get_tension("jiangnan") == 0.6
    # 推进 1 回合
    engine.tick(current_round=1)
    # 张力应下降 0.01
    new_tension = state.plate_state.get_tension("jiangnan")
    assert new_tension < 0.6, f"期望衰减，实际 {new_tension}"
    return True


# ============= 测试 2：process_pending_transmissions =============

def test_V28_161_engine_processes_due_transmissions():
    """PlateEngine 处理到期的待传导事件"""
    state, registry, engine = make_engine()
    # 登记传导：round 1 时登记，delay=2 → round 3 生效
    engine.add_transmission("central_plains", "jiangnan", current_round=1)
    # 当前 round=2：不应处理
    events = engine._process_pending_transmissions(current_round=2)
    assert len(events) == 0
    # 当前 round=3：应处理
    events = engine._process_pending_transmissions(current_round=3)
    assert len(events) == 1
    # jiangnan 张力应增加：factor 0.3 * cp_tension 0.3 = 0.09
    cp_tension = state.plate_state.get_tension("central_plains")
    jn_tension_before = 0.4  # baseline
    jn_tension_after = state.plate_state.get_tension("jiangnan")
    expected = jn_tension_before + cp_tension * 0.3
    assert abs(jn_tension_after - expected) < 0.01, f"期望 {expected}，实际 {jn_tension_after}"
    return True


def test_V28_162_engine_clears_processed_transmissions():
    """PlateEngine 处理后清空 pending_transmissions"""
    state, registry, engine = make_engine()
    engine.add_transmission("central_plains", "jiangnan", current_round=1)
    assert len(state.plate_state.pending_transmissions) == 1
    engine._process_pending_transmissions(current_round=10)
    assert len(state.plate_state.pending_transmissions) == 0
    return True


# ============= 测试 3：detect_shift_events =============

def test_V28_163_engine_detects_shift_on_boost():
    """PlateEngine 检测张力突破阈值（boost）"""
    state, registry, engine = make_engine()
    # 手动 boost northwest 0.6 → 0.95（> 0.9 collapse）
    event = engine.boost_tension("northwest", 0.5, current_round=5)
    assert event is not None
    assert event.plate_id == "northwest"
    assert event.new_status == "collapsed"
    return True


def test_V28_164_engine_detects_shift_event_recorded():
    """PlateEngine boost 触发后 shift_events 应记录"""
    state, registry, engine = make_engine()
    engine.boost_tension("northwest", 0.5, current_round=5)
    assert len(state.plate_state.shift_events) == 1
    assert state.plate_state.shift_events[0]["type"] == "collapse"
    return True


# ============= 测试 4：get_shifting_plates =============

def test_V28_165_engine_get_shifting_plates():
    """PlateEngine.get_shifting_plates 返回 shifting/collapsed 板块"""
    state, registry, engine = make_engine()
    # 初始：northwest=0.5（tense），其他=stable
    assert "northwest" not in engine.get_shifting_plates()
    # boost northwest 到 0.85
    engine.boost_tension("northwest", 0.35, current_round=5)
    # 现在 northwest=0.85，shifting
    assert "northwest" in engine.get_shifting_plates()
    return True


# ============= 测试 5：reduce_tension =============

def test_V28_166_engine_reduce_tension():
    """PlateEngine.reduce_tension 减少张力"""
    state, registry, engine = make_engine()
    state.plate_state.set_tension("jiangnan", 0.8)
    engine.reduce_tension("jiangnan", 0.3)
    assert abs(state.plate_state.get_tension("jiangnan") - 0.5) < 0.01
    return True


def test_V28_167_engine_get_current_statuses():
    """PlateEngine.get_current_statuses 返回所有板块状态"""
    state, registry, engine = make_engine()
    statuses = engine.get_current_statuses()
    assert "central_plains" in statuses
    assert statuses["central_plains"] == "stable"
    assert statuses["northwest"] == "tense"  # 0.5 → tense
    return True


# ============= 测试 6：add_transmission 按 transmission_rules 查 factor + delay =============

def test_V28_168_engine_add_transmission_uses_registry_rules():
    """PlateEngine.add_transmission 查 transmission_rules"""
    state, registry, engine = make_engine()
    # central_plains → northwest：factor 0.4, delay 1
    engine.add_transmission("central_plains", "northwest", current_round=10)
    # 应登记 1 个待传导
    assert len(state.plate_state.pending_transmissions) == 1
    pending = state.plate_state.pending_transmissions[0]
    assert pending["from"] == "central_plains"
    assert pending["to"] == "northwest"
    assert pending["factor"] == 0.4
    assert pending["round"] == 11  # 10 + delay 1
    return True


def test_V28_169_engine_add_transmission_no_rule():
    """PlateEngine.add_transmission 无规则时跳过"""
    state, registry, engine = make_engine()
    # jiangnan → northwest：transmission_rules 中无此规则
    engine.add_transmission("jiangnan", "northwest", current_round=10)
    assert len(state.plate_state.pending_transmissions) == 0
    return True
