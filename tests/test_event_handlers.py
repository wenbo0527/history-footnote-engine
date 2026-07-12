"""v2.10.1 W52 P1-1 followup: event_handlers 模块单元测试

验证 8 个 _apply_xxx 处理器拆出后:
1. 模块独立可 import
2. _HANDLERS dict 仍正确注册全部 8 个 domain
3. apply_event 通过新模块仍工作
"""
import pytest

from history_footnote.event_parser import (
    apply_event,
    parse_events,
    process_llm_output,
    fuzzy_match_events,
    FIN_EVENTS,
    CITY_IDS,
    FAM_STATUSES,
    _log,
)
from history_footnote.event_handlers import (
    _HANDLERS,
    _apply_fin_event,
    _apply_city_event,
    _apply_fam_event,
    _apply_gen_event,
    _apply_prop_event,
    _apply_inv_event,
    _apply_discover_event,
    _apply_evt_event,
)


# ============= 模块可独立 import =============

def test_event_handlers_module_imports():
    """event_handlers 应可独立 import"""
    assert callable(_apply_fin_event)
    assert callable(_apply_city_event)
    assert callable(_apply_fam_event)
    assert callable(_apply_gen_event)
    assert callable(_apply_prop_event)
    assert callable(_apply_inv_event)
    assert callable(_apply_discover_event)
    assert callable(_apply_evt_event)


def test_event_handlers_exports_8_domains():
    """_HANDLERS dict 应包含全部 8 个 domain"""
    expected_domains = {"fin", "city", "fam", "gen", "prop", "inv", "discover", "evt"}
    actual_domains = set(_HANDLERS.keys())
    assert actual_domains == expected_domains, f"missing: {expected_domains - actual_domains}"


def test_event_handlers_constants_reexported():
    """FIN_EVENTS / CITY_IDS / FAM_STATUSES 应可通过两个模块拿到"""
    assert FIN_EVENTS == {"sell_silk", "buy_thread", "pay_tax", "borrow", "repay",
                          "deposit_interest", "debt_interest", "workshop_rent",
                          "monthly_burn", "gift_in", "gift_out"}
    assert "shengze" in CITY_IDS
    assert "healthy" in FAM_STATUSES


# ============= apply_event 通过新模块工作 =============

def test_apply_event_unknown_domain():
    """unknown domain → False + log"""
    class FakeLog:
        def warning(self, msg): pass
    log = FakeLog()
    result = apply_event(type("S", (), {})(), {"id": "unknown.test"}, logger=log)
    assert result is False


def test_apply_event_fin_unknown_kind():
    """fin domain 未知子类型 → False"""
    result = apply_event(type("S", (), {})(), {"id": "fin.unknown", "amount": "1.0"})
    assert result is False


def test_apply_event_no_id():
    """无 id → False"""
    result = apply_event(type("S", (), {})(), {})
    assert result is False


# ============= parse_events =============

def test_parse_events_basic():
    """解析 <events> 块"""
    output = '<events><event id="fin.sell_silk" amount="5.0" note="卖绸" /></events>'
    events = parse_events(output)
    assert len(events) == 1
    assert events[0]["id"] == "fin.sell_silk"
    assert events[0]["amount"] == "5.0"
    assert events[0]["note"] == "卖绸"


def test_parse_events_multiple():
    """解析多个事件"""
    output = '''
    <events>
      <event id="fin.pay_tax" amount="1.0" />
      <event id="city.move" to="suzhou" />
    </events>
    '''
    events = parse_events(output)
    assert len(events) == 2
    assert events[0]["id"] == "fin.pay_tax"
    assert events[1]["id"] == "city.move"


def test_parse_events_empty():
    """无 events 块 → 空列表"""
    assert parse_events("no events here") == []
    assert parse_events("") == []


# ============= _HANDLERS 集成 =============

def test_handlers_dict_consistency():
    """_HANDLERS dict 中每个 handler 必须是 callable"""
    for domain, handler in _HANDLERS.items():
        assert callable(handler), f"{domain} handler not callable"


def test_apply_event_dispatches_via_new_handlers():
    """apply_event 应通过新模块 _HANDLERS 找到 handler（用 unknown kind 走 handler 路径）"""
    class MockState:
        pass
    state = MockState()
    # fin.sell_silk 是合法 kind，会进入 _apply_fin_event 主体
    # 用 unknown kind 走 handler 内部判断路径，验证 dispatch 工作
    result = apply_event(state, {"id": "fin.unknown_kind", "amount": "1.0"})
    # unknown kind 应返回 False（不抛异常）
    assert result is False


def test_apply_event_handlers_dict_contains_all():
    """_HANDLERS 字典完整性"""
    assert _HANDLERS["fin"] is _apply_fin_event
    assert _HANDLERS["city"] is _apply_city_event
    assert _HANDLERS["fam"] is _apply_fam_event
    assert _HANDLERS["gen"] is _apply_gen_event
    assert _HANDLERS["prop"] is _apply_prop_event
    assert _HANDLERS["inv"] is _apply_inv_event
    assert _HANDLERS["discover"] is _apply_discover_event
    assert _HANDLERS["evt"] is _apply_evt_event


# ============= 路径一致性 =============

def test_log_function_works():
    """_log 函数应工作"""
    class FakeLog:
        def __init__(self):
            self.warned = []
        def warning(self, msg):
            self.warned.append(msg)
    log = FakeLog()
    _log(log, "test warning")
    assert log.warned == ["test warning"]


def test_log_function_no_logger():
    """_log 无 logger 应静默"""
    _log(None, "no logger")  # 不应抛
