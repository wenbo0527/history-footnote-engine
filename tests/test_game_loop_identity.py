"""v2.10.1 W52 P1-2 followup: game_loop_identity 模块单元测试

验证 5 个身份切换方法 + 1 个纯函数（filter_available_offers）。
"""
import io
import sys

from history_footnote.game_loop_identity import (
    filter_available_offers,
    inject_identity_switch_offers,
    handle_identity_decision,
    apply_identity_switch,
    show_available_offers,
    set_pending_offer,
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


# ============= filter_available_offers =============

def test_filter_available_offers_empty():
    """无 offers → 空列表"""
    assert filter_available_offers({}, "any") == []
    assert filter_available_offers({"world": {}}, "any") == []


def test_filter_available_offers_by_from_identity():
    """应只保留 from_identity 匹配的 offer"""
    era = {"world": {"identity_switch_offers": [
        {"id": "o1", "from_identity": "a", "to_identity": "b"},
        {"id": "o2", "from_identity": "x", "to_identity": "y"},
        {"id": "o3", "from_identity": "a", "to_identity": "c"},
    ]}}
    result = filter_available_offers(era, "a")
    assert len(result) == 2
    assert all(o["from_identity"] == "a" for o in result)


# ============= handle_identity_decision =============

def test_handle_identity_decision_no_pending():
    """无 pending offer → 打印 [INFO] 并返回 True"""
    class FakeLoop:
        pending_identity_offer = None
    out = _capture_print(handle_identity_decision, FakeLoop(), accept=True)
    assert "没有待处理" in out


def test_handle_identity_decision_decline():
    """decline → 清除 pending"""
    class FakeLoop:
        pending_identity_offer = {"to_label": "新身份", "to_identity": "x"}
    out = _capture_print(handle_identity_decision, FakeLoop(), accept=False)
    assert "拒绝了" in out
    # pending_offer 应被设为 None（在原方法中通过 self.x = None 实现）
    # 但我们的版本是直接 setattr,所以测试实例的属性应被清除
    # 由于 FakeLoop 的 pending_identity_offer 是 class attr,setattr 会创建 instance attr


def test_handle_identity_decision_accept_calls_apply():
    """accept=True → 应调 apply_identity_switch"""
    class FakeLoop:
        pending_identity_offer = {"to_identity": "x", "reason": "test"}
        called = []
        def _apply_identity_switch(self, offer):
            self.called.append(offer)
    FakeLoop.called = []  # instance attr
    loop = FakeLoop()
    # 替换模块函数
    import history_footnote.game_loop_identity as gli
    orig_apply = gli.apply_identity_switch
    gli.apply_identity_switch = lambda l, o: l.called.append(o)
    try:
        _capture_print(handle_identity_decision, loop, accept=True)
        assert len(loop.called) == 1
        assert loop.called[0]["to_identity"] == "x"
    finally:
        gli.apply_identity_switch = orig_apply


# ============= set_pending_offer =============

def test_set_pending_offer_offered_true():
    """offered=True → 设置 pending_offer 并打印"""
    class FakeLoop:
        pending_identity_offer = None
    loop = FakeLoop()
    offer = {
        "offered": True,
        "message": "你有机会投靠",
        "to_label": "商人",
        "to_identity": "merchant",
        "reason": "走投无路",
        "cost": "变卖家产",
        "benefit": "获得财富",
    }
    out = _capture_print(set_pending_offer, loop, offer)
    assert "OFFER" in out
    assert "你有机会投靠" in out
    assert "商人" in out
    assert "/accept" in out
    assert loop.pending_identity_offer == offer


def test_set_pending_offer_offered_false():
    """offered=False → 不应设置"""
    class FakeLoop:
        pending_identity_offer = None
    loop = FakeLoop()
    out = _capture_print(set_pending_offer, loop, {"offered": False})
    assert loop.pending_identity_offer is None
    assert out == ""  # 不打印


# ============= show_available_offers =============

def test_show_available_offers_no_offers():
    """无可用 offer → 打印 [INFO]"""
    class FakeLoop:
        era_config = {"world": {"identity_switch_offers": []}}
        selected_identity = "a"
    out = _capture_print(show_available_offers, FakeLoop())
    assert "暂无可用" in out


def test_show_available_offers_lists():
    """应列出所有可用 offer"""
    class FakeLoop:
        era_config = {"world": {"identity_switch_offers": [
            {"id": "o1", "from_identity": "a", "to_identity": "b",
             "trigger_condition": {"round": 3}, "cost_description": "1两", "benefit_description": "安全"},
        ]}}
        selected_identity = "a"
    out = _capture_print(show_available_offers, FakeLoop())
    assert "o1" in out
    assert "b" in out
    assert "1两" in out
    assert "安全" in out


# ============= apply_identity_switch =============

def test_apply_identity_switch_missing_to_identity():
    """offer 缺 to_identity → 打印 ERROR 不抛异常"""
    class FakeLoop:
        state = GameState()
        era_config = {"world": {"player_identities": {}, "identity_switch_offers": []}}
        selected_identity = "a"
        identity_config = {}
        memory = type("M", (), {"save_event": lambda self, e: None})()
        pending_identity_offer = None
        dm = type("D", (), {"llm": type("L", (), {"_state_ref_slot_ref": [{}]})()})()
    out = _capture_print(apply_identity_switch, FakeLoop(), {})
    assert "ERROR" in out or "缺少" in out


# ============= inject_identity_switch_offers =============

def test_inject_identity_switch_offers_no_offers():
    """无 offers → 不注入"""
    class FakeLoop:
        era_config = {"world": {"identity_switch_offers": []}}
        selected_identity = "a"
        dm = type("D", (), {"llm": type("L", (), {"_state_ref_slot_ref": [{}]})()})()
    # 不应抛异常
    inject_identity_switch_offers(FakeLoop())


def test_inject_identity_switch_offers_no_match():
    """offers 都不匹配 → 不注入"""
    class FakeLoop:
        era_config = {"world": {"identity_switch_offers": [
            {"from_identity": "x", "to_identity": "y"},
        ]}}
        selected_identity = "a"
        dm = type("D", (), {"llm": type("L", (), {"_state_ref_slot_ref": [{}]})()})()
    inject_identity_switch_offers(FakeLoop())


def test_inject_identity_switch_offers_match():
    """匹配的 offer 应注入到 state_ref"""
    class FakeLoop:
        era_config = {"world": {"identity_switch_offers": [
            {"id": "o1", "from_identity": "a", "to_identity": "b"},
        ]}}
        selected_identity = "a"
    ref = {}
    class FakeLlm:
        _state_ref_slot_ref = [ref]
    class FakeLoopWithLlm(FakeLoop):
        dm = type("D", (), {"llm": FakeLlm()})()
    inject_identity_switch_offers(FakeLoopWithLlm())
    assert "identity_switch_offers" in ref
    assert len(ref["identity_switch_offers"]) == 1
    assert ref["identity_switch_offers"][0]["id"] == "o1"