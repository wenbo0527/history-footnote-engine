"""v2.10.1 W52 P1-2 PR#2: game_loop_events 模块单元测试

验证 2 个事件逻辑函数的独立性。
"""
import pytest

from history_footnote.game_loop_events import (
    check_random_events,
    apply_event_effects,
)
from history_footnote.game_state import GameState


class FakeDice:
    """模拟 dice 工具（chance / weighted_choice / check）"""

    def __init__(self, always_trigger=False, weighted_choice_result=None):
        self.always_trigger = always_trigger
        self._weighted_choice_result = weighted_choice_result

    def chance(self, prob):
        return self.always_trigger or prob >= 1.0  # probability=1.0 必然触发

    def weighted_choice(self, outcomes):
        if self._weighted_choice_result is not None:
            return self._weighted_choice_result
        return outcomes[0]

    def check(self, dc, dice_expr, purpose=""):
        return {
            "success": True,
            "dc": dc,
            "result": type("Roll", (), {"is_critical_success": False, "is_critical_fail": False, "__str__": lambda self: "1d20=15"})(),
        }


def _make_state(round_num=1):
    state = GameState()
    state.round_number = round_num
    state.variables = {"cash": 0.0, "stress": 0.0}
    return state


# ============= check_random_events =============

def test_check_random_events_no_events():
    """无随机事件 → 返回空列表"""
    state = _make_state()
    result = check_random_events([], state, FakeDice(), "any_scene")
    assert result == []


def test_check_random_events_scene_mismatch():
    """事件要求 scene=foo,但当前 scene=bar → 不触发"""
    events = [
        {
            "id": "evt1",
            "trigger_condition": {"scene": "foo"},
            "probability": 1.0,
            "outcomes": [{"description": "test"}],
        }
    ]
    state = _make_state()
    result = check_random_events(events, state, FakeDice(always_trigger=True), "bar")
    assert result == []


def test_check_random_events_round_too_low():
    """当前 round < min_round → 不触发"""
    events = [
        {
            "id": "evt1",
            "trigger_condition": {"min_round": 10},
            "probability": 1.0,
            "outcomes": [{"description": "test"}],
        }
    ]
    state = _make_state(round_num=5)
    result = check_random_events(events, state, FakeDice(always_trigger=True), "any")
    assert result == []


def test_check_random_events_no_outcomes():
    """事件无 outcomes → 不触发"""
    events = [
        {
            "id": "evt1",
            "trigger_condition": {},
            "probability": 1.0,
            "outcomes": [],
        }
    ]
    state = _make_state()
    result = check_random_events(events, state, FakeDice(always_trigger=True), "any")
    assert result == []


def test_check_random_events_triggered():
    """满足条件应触发"""
    events = [
        {
            "id": "evt_rain",
            "trigger_condition": {},
            "probability": 1.0,
            "outcomes": [{"description": "下雨了", "effect": {"cash": -1.0}}],
        }
    ]
    state = _make_state()
    result = check_random_events(events, state, FakeDice(always_trigger=True), "any")
    assert len(result) == 1
    assert result[0]["event_id"] == "evt_rain"
    assert result[0]["outcome"]["description"] == "下雨了"


def test_check_random_events_with_dice():
    """带 requires_dice 的 outcome 应执行 dice 判定"""
    events = [
        {
            "id": "evt1",
            "trigger_condition": {},
            "probability": 1.0,
            "outcomes": [{
                "description": "判定",
                "requires_dice": True,
                "dice": "d20",
                "dc": 10,
                "success": "成功",
                "fail": "失败",
            }],
        }
    ]
    state = _make_state()
    result = check_random_events(events, state, FakeDice(always_trigger=True), "any")
    assert "dice_result" in result[0]["outcome"]
    assert result[0]["outcome"]["dice_result"]["dc"] == 10


# ============= apply_event_effects =============

def test_apply_event_effects_empty():
    """空事件 → 空消息"""
    state = _make_state()
    messages = apply_event_effects([], state)
    assert messages == []


def test_apply_event_effects_simple_delta():
    """简单数值 effect 应累加到 state.variables"""
    state = _make_state()
    triggered = [{"event_id": "e1", "outcome": {"effect": {"cash": 1.5}}}]
    messages = apply_event_effects(triggered, state)
    assert state.variables["cash"] == 1.5
    assert any("cash +1.5" in m for m in messages)


def test_apply_event_effects_string_delta():
    """字符串 delta "+0.5" / "-0.3" 应正确解析"""
    state = _make_state()
    triggered = [{"event_id": "e1", "outcome": {"effect": {"cash": "+2.0", "stress": "-0.5"}}}]
    messages = apply_event_effects(triggered, state)
    assert state.variables["cash"] == 2.0
    assert state.variables["stress"] == -0.5


def test_apply_event_effects_unknown_var_skipped():
    """effect 里有未定义的 var_key → 跳过,不影响 state"""
    state = _make_state()
    triggered = [{"event_id": "e1", "outcome": {"effect": {"unknown_var": 1.0, "cash": 0.5}}}]
    messages = apply_event_effects(triggered, state)
    assert state.variables["cash"] == 0.5
    assert "unknown_var" not in state.variables


def test_apply_event_effects_with_dice_result_success():
    """带 dice_result 成功 → 消息含'成功'"""
    state = _make_state()
    triggered = [{
        "event_id": "e1",
        "outcome": {
            "effect": {"cash": 0.5},
            "dice_result": {
                "success": True,
                "dc": 10,
                "result": type("Roll", (), {"is_critical_success": False, "is_critical_fail": False, "__str__": lambda self: "1d20=15"})(),
            },
            "success": "发财",
        },
    }]
    messages = apply_event_effects(triggered, state)
    assert any("成功" in m and "发财" in m for m in messages)


def test_apply_event_effects_with_dice_result_fail():
    """带 dice_result 失败 → 消息含'失败'"""
    state = _make_state()
    triggered = [{
        "event_id": "e1",
        "outcome": {
            "dice_result": {
                "success": False,
                "dc": 15,
                "result": type("Roll", (), {"is_critical_success": False, "is_critical_fail": False, "__str__": lambda self: "1d20=5"})(),
            },
            "fail": "倒霉",
        },
    }]
    messages = apply_event_effects(triggered, state)
    assert any("失败" in m and "倒霉" in m for m in messages)