"""v2.10.1 W52 P1-2 PR#1: game_loop_display 模块单元测试

验证 7 个纯显示函数的独立性（不依赖 GameLoop 实例）。
"""
import io
import sys

from history_footnote.game_loop_display import (
    print_opening,
    display_narrative,
    display_state,
    display_full_state,
    help_text,
    has_persona_opening,
    get_persona_opening,
)
from history_footnote.game_state import GameState


def _capture_print(fn, *args, **kwargs) -> str:
    """调 fn 并捕获 print 输出"""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        fn(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old


# ============= display_narrative =============

def test_display_narrative_prints_story():
    """display_narrative 应打印【DM叙事】前缀"""
    out = _capture_print(display_narrative, "我去看看丝价")
    assert "【DM叙事】" in out
    assert "我去看看丝价" in out


def test_display_narrative_empty_string():
    """空字符串也能打印"""
    out = _capture_print(display_narrative, "")
    assert "【DM叙事】" in out


# ============= display_state =============

def test_display_state_with_default_state():
    """display_state 应打印回合 / 日期 / 行动点"""
    state = GameState()
    out = _capture_print(display_state, state)
    assert "[状态]" in out
    assert "行动点" in out


def test_display_state_includes_round():
    """应含回合号"""
    state = GameState()
    state.round_number = 5
    out = _capture_print(display_state, state)
    assert "回合5" in out


# ============= display_full_state =============

def test_display_full_state_minimal():
    """display_full_state 需 session + state + memory"""
    state = GameState()

    class FakeSession:
        session_id = "test-session"
        slots = {}

    class FakeMemory:
        def count(self):
            return 0

    out = _capture_print(display_full_state, FakeSession(), state, FakeMemory())
    assert "test-session" in out
    assert "变量" in out
    assert "已触发事件" in out


def test_display_full_state_with_events():
    """state 有事件时应正确显示"""
    state = GameState()
    state.triggered_events = ["evt1", "evt2", "evt3"]

    class FakeSession:
        session_id = "s1"
        slots = {}

    class FakeMemory:
        def count(self):
            return 5

    out = _capture_print(display_full_state, FakeSession(), state, FakeMemory())
    assert "已触发事件: 3" in out
    assert "事件日志: 5" in out


# ============= print_opening =============

def test_print_opening_default_identity():
    """非默认身份,无 cc,无 persona.md → 走 identity_config 分支"""
    state = GameState()
    state.current_date = "万历十五年·三月"
    era_config = {"era_name": "万历十五年", "world": {"default_identity": "silk_merchant"}}
    identity_config = {
        "label": "小商人",
        "role": "苏州织工",
        "description": "你是一个小商人",
    }
    # 用不存在的 era,确保 has_persona_opening 返回 False
    out = _capture_print(
        print_opening,
        state, era_config, identity_config, "nonexistent_era", "silk_merchant"
    )
    assert "万历十五年" in out
    assert "小商人" in out


def test_print_opening_with_custom_character():
    """有 cc 且有 opening_paragraph 时优先用 cc"""
    state = GameState()
    state.current_date = "万历十五年"
    state.custom_character = {
        "name": "沈万三",
        "hometown": "苏州",
        "opening_paragraph": "我是沈万三,世代经商",
        "background": "江南丝绸世家",
    }
    era_config = {"era_name": "万历", "world": {}}
    identity_config = {}
    out = _capture_print(
        print_opening,
        state, era_config, identity_config, "wanli1587", "default"
    )
    assert "沈万三" in out
    assert "世代经商" in out
    assert "江南丝绸世家" in out


def test_print_opening_cc_without_narrative():
    """cc 只有 name 等非叙事字段,不走 cc 分支"""
    state = GameState()
    state.current_date = "万历"
    state.custom_character = {"name": "张三", "age": 30}  # 无 opening_paragraph
    era_config = {"era_name": "万历", "world": {"default_identity": "default"}}
    identity_config = {"label": "默认", "role": "默认角色", "description": "默认描述"}
    out = _capture_print(
        print_opening,
        state, era_config, identity_config, "nonexistent_era", "default"
    )
    # 应走 identity 分支,打印"你选择成为：默认"
    assert "默认" in out


# ============= help_text =============

def test_help_text_has_commands():
    """help_text 应含所有元指令"""
    text = help_text()
    for cmd in ["/state", "/save", "/load", "/quit", "/help"]:
        assert cmd in text, f"missing {cmd}"


def test_help_text_returns_string():
    """help_text 返回 str"""
    text = help_text()
    assert isinstance(text, str)
    assert len(text) > 100


# ============= has_persona_opening / get_persona_opening =============

def test_has_persona_opening_no_era():
    """era 不存在时返回 False"""
    result = has_persona_opening("nonexistent_era")
    assert result is False


def test_get_persona_opening_no_era():
    """era 不存在时返回 None"""
    result = get_persona_opening("nonexistent_era")
    assert result is None