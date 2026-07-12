"""v2.10.1 W52 P1-2 PR#3: game_loop_save 模块单元测试

验证 3 个存档/读档函数的独立性。
"""
import io
import sys

from history_footnote.game_loop_save import (
    save_to_slot,
    load_from_slot,
    auto_save,
)
from history_footnote.game_state import GameState


def _capture_print(fn, *args, **kwargs) -> str:
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = fn(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old


class FakeSlotInfo:
    def __init__(self, round_number, current_date):
        self.round_number = round_number
        self.current_date = current_date


class FakeSaveManager:
    """模拟 save_manager（save_state / load_state）"""

    def __init__(self, slots=None, load_result=None):
        self.slots = slots or {}
        self.load_result = load_result
        self.saved_calls = []
        self.loaded_calls = []

    def save_state(self, session, slot, state_data, summary=""):
        self.saved_calls.append((slot, state_data, summary))
        return FakeSlotInfo(
            round_number=state_data.get("round_number", 0),
            current_date=state_data.get("current_date", ""),
        )

    def load_state(self, session, slot):
        self.loaded_calls.append(slot)
        return self.load_result


class FakeMemory:
    def __init__(self):
        self.events = []


class FakeSession:
    def __init__(self, session_id="s1", slots=None):
        self.session_id = session_id
        self.slots = slots or {}


def _make_state(round_num=1, date="万历"):
    state = GameState()
    state.round_number = round_num
    state.current_date = date
    return state


# ============= save_to_slot =============

def test_save_to_slot_default():
    """'default' → slot1"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    save_to_slot("default", session, sm, state, FakeMemory())
    assert sm.saved_calls[0][0] == "slot1"


def test_save_to_slot_1():
    """'1' → slot1"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    save_to_slot("1", session, sm, state, FakeMemory())
    assert sm.saved_calls[0][0] == "slot1"


def test_save_to_slot_slot1():
    """'slot1' → slot1"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    save_to_slot("slot1", session, sm, state, FakeMemory())
    assert sm.saved_calls[0][0] == "slot1"


def test_save_to_slot_slot2():
    """'slot2' → slot2"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    save_to_slot("slot2", session, sm, state, FakeMemory())
    assert sm.saved_calls[0][0] == "slot2"


def test_save_to_slot_slot3():
    """'slot3' → slot3"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    save_to_slot("slot3", session, sm, state, FakeMemory())
    assert sm.saved_calls[0][0] == "slot3"


def test_save_to_slot_auto():
    """'auto' → auto"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    save_to_slot("auto", session, sm, state, FakeMemory())
    assert sm.saved_calls[0][0] == "auto"


def test_save_to_slot_invalid():
    """非法 slot 应打印 ERROR,不调 save_state"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    out = _capture_print(save_to_slot, "invalid_slot", session, sm, state, FakeMemory())
    assert "非法slot名" in out
    assert len(sm.saved_calls) == 0


def test_save_to_slot_event_log_synced():
    """应把 memory.events 同步到 state_data['event_log']"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()

    memory = FakeMemory()
    fake_event = type("E", (), {"to_dict": lambda self: {"summary": "test"}})()
    memory.events = [fake_event]

    save_to_slot("slot1", session, sm, state, memory)
    assert sm.saved_calls[0][1]["event_log"] == [{"summary": "test"}]


# ============= load_from_slot =============

def test_load_from_slot_success():
    """load_state 返回有效 dict → True"""
    state = _make_state()
    session = FakeSession(slots={"slot1": "anything"})
    sm = FakeSaveManager(load_result={"round_number": 5, "current_date": "万历"})
    out = _capture_print(load_from_slot, "1", session, sm)
    assert sm.loaded_calls == ["slot1"]
    assert out.count("读档成功") == 1


def test_load_from_slot_slot_not_exist():
    """session.slots 中无该 slot → False"""
    state = _make_state()
    session = FakeSession(slots={})  # 空
    sm = FakeSaveManager()
    out = _capture_print(load_from_slot, "1", session, sm)
    assert "没有存档" in out
    assert len(sm.loaded_calls) == 0


def test_load_from_slot_load_failed():
    """load_state 返回 None → False"""
    state = _make_state()
    session = FakeSession(slots={"slot1": "anything"})
    sm = FakeSaveManager(load_result=None)
    out = _capture_print(load_from_slot, "1", session, sm)
    assert "读取" in out and "失败" in out


def test_load_from_slot_auto():
    """'auto' / 'default' → auto"""
    state = _make_state()
    session = FakeSession(slots={"auto": "anything"})
    sm = FakeSaveManager(load_result={"round_number": 1})
    _capture_print(load_from_slot, "auto", session, sm)
    assert sm.loaded_calls == ["auto"]
    _capture_print(load_from_slot, "default", session, sm)
    assert sm.loaded_calls == ["auto", "auto"]


def test_load_from_slot_invalid():
    """非法 slot → False"""
    state = _make_state()
    session = FakeSession(slots={})
    sm = FakeSaveManager()
    out = _capture_print(load_from_slot, "garbage", session, sm)
    assert "非法slot名" in out


# ============= auto_save =============

def test_auto_save_calls_save_with_auto_slot():
    """auto_save 应调 save_manager.save_state(..., 'auto', ...)"""
    state = _make_state()
    session = FakeSession()
    sm = FakeSaveManager()
    auto_save(session, sm, state, FakeMemory())
    assert len(sm.saved_calls) == 1
    assert sm.saved_calls[0][0] == "auto"


def test_auto_save_summary_contains_round():
    """摘要应含回合号"""
    state = _make_state(round_num=7)
    session = FakeSession()
    sm = FakeSaveManager()
    auto_save(session, sm, state, FakeMemory())
    assert "回合7" in sm.saved_calls[0][2]


def test_auto_save_event_log_synced():
    """应同步 memory.events 到 state_data"""
    state = _make_state()
    session = FakeSession()
    sm = FakeSaveManager()
    memory = FakeMemory()
    memory.events = [type("E", (), {"to_dict": lambda self: {"summary": "auto"}})()]
    auto_save(session, sm, state, memory)
    assert sm.saved_calls[0][1]["event_log"] == [{"summary": "auto"}]