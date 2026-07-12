"""v2.10.1 W52 P1-1 PR#2: dm_agent.prompts 模块单元测试

验证 7 个 prompt 构建函数的独立性。
"""
import io
import sys

from history_footnote.dm_agent.prompts import (
    build_prefetch_message,
    build_system_prompt,
    load_dm_persona,
    build_current_city_section,
    build_current_location_section,
    build_fate_used_section,
    build_recent_context_for_prompt,
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


# ============= build_prefetch_message =============

def test_build_prefetch_message_basic():
    """prefetched dict 应打包成 SystemMessage"""
    prefetched = {
        "state": {"cash": 10.0},
        "rules": {"triggers": []},
        "events": [],
        "knowledge": [],
        "narrative_snippets": [],
        "story_segments": [],
    }
    msg = build_prefetch_message(prefetched)
    assert msg.__class__.__name__ == "SystemMessage"
    assert "已预先查询" in msg.content
    assert "决策类工具" in msg.content


def test_build_prefetch_message_clips_knowledge():
    """knowledge 列表应裁剪到 3 条"""
    prefetched = {
        "knowledge": [
            {"title": f"条目{i}", "content": "x" * 500}
            for i in range(10)
        ],
    }
    msg = build_prefetch_message(prefetched)
    # 裁剪到 3 条
    assert msg.content.count('"title"') <= 3
    # 截断到 200 字
    assert "…" in msg.content


# ============= load_dm_persona =============

def test_load_dm_persona_no_era():
    """无 era_id 时应返回 None"""
    assert load_dm_persona({}) is None


def test_load_dm_persona_no_file():
    """era_id 存在但文件不存在 → None"""
    assert load_dm_persona({"era_id": "nonexistent_era_xyz"}) is None


# ============= build_current_city_section =============

def test_build_current_city_section_default():
    """无 current_city → 空字符串"""
    state = GameState()
    era_config = {"world": {"cities": {}}}
    out = build_current_city_section(era_config, state)
    assert out == ""


def test_build_current_city_section_unknown_city():
    """current_city 不在 cities → 空"""
    state = GameState()
    state.current_city = "atlantis"
    era_config = {"world": {"cities": {"shengze": {"name": "盛泽"}}}}
    out = build_current_city_section(era_config, state)
    assert out == ""


def test_build_current_city_section_known_city():
    """已知城市应输出 sensory 段"""
    state = GameState()
    state.current_city = "shengze"
    era_config = {
        "world": {
            "cities": {
                "shengze": {
                    "name": "盛泽镇",
                    "distance_from_shengze": "0",
                    "travel_cost": "0",
                    "narrative_arrival": "你回到了盛泽",
                    "sensory": {"sight": "织机林立", "sound": "咔嗒咔嗒", "smell": "桑叶味"},
                    "functions": ["织造", "卖丝"],
                    "danger_level": 1,
                    "opportunity_level": 2,
                }
            }
        }
    }
    out = build_current_city_section(era_config, state)
    assert "盛泽镇" in out
    assert "你回到了盛泽" in out
    assert "织机林立" in out
    assert "1/5" in out


# ============= build_fate_used_section =============

def test_build_fate_used_section_empty():
    """无手牌无 buff → 空"""
    state = GameState()
    out = build_fate_used_section(state)
    assert out == ""


def test_build_fate_used_section_used_cards():
    """已用卡应列入"已用卡"段"""
    state = GameState()
    state.fate_hand = [
        {"name": "天降横财", "icon": "💰", "description": "3 两银子", "used": True},
        {"name": "沈氏倾心", "icon": "💕", "description": "+30 好感", "used": False},
    ]
    out = build_fate_used_section(state)
    assert "💰" in out
    assert "天降横财" in out
    assert "沈氏倾心" not in out  # 未用,不显示


def test_build_fate_used_section_active_buffs():
    """active buff 应显示带特殊说明"""
    state = GameState()
    state.active_buffs = [
        {"name": "lucky", "rounds_left": 3, "params": {}},
        {"name": "shield", "rounds_left": 1, "params": {"failure_reduction": 0.5}},
    ]
    out = build_fate_used_section(state)
    assert "lucky" in out
    assert "+10%" in out
    assert "shield" in out
    assert "50%" in out


def test_build_fate_used_section_event_flags():
    """命运事件标记应翻译为中文"""
    state = GameState()
    state.fate_event_flags = ["zhou_secret", "shen_illness"]
    out = build_fate_used_section(state)
    assert "周大娘的秘密" in out
    assert "沈氏生病" in out


# ============= build_recent_context_for_prompt =============

def test_build_recent_context_empty():
    """无 recent 叙事 → 空"""
    state = GameState()
    out = build_recent_context_for_prompt(state)
    assert out == ""


def test_build_recent_context_with_narratives():
    """有 recent 叙事应输出上下文段"""
    state = GameState()
    state.narrative_recent = [
        {"round": 1, "summary": "你开始游戏", "narrative": "在盛泽镇开始"},
        {"round": 2, "summary": "你织了一匹布", "narrative": "咔嗒咔嗒"},
    ]
    out = build_recent_context_for_prompt(state)
    assert "最近剧情上下文" in out
    assert "第 1 回合" in out
    assert "你开始游戏" in out
    assert "第 2 回合" in out
    assert "你织了一匹布" in out


def test_build_recent_context_truncates_long_narrative():
    """长 narrative 应截到 400 字"""
    state = GameState()
    state.narrative_recent = [
        {"round": 1, "summary": "", "narrative": "x" * 1000},
    ]
    out = build_recent_context_for_prompt(state)
    # 应有 "…" 截断符
    assert "…" in out


def test_build_recent_context_includes_event_log():
    """event_log 中 player_action 应注入"""
    state = GameState()
    state.narrative_recent = [{"round": 1, "summary": "开始", "narrative": ""}]
    state.event_log = [{"round": 1, "player_action": "我走进织坊"}]
    out = build_recent_context_for_prompt(state)
    assert "我走进织坊" in out


# ============= build_current_location_section =============

def test_build_current_location_section_returns_string():
    """应返回 str(可能为空)"""
    state = GameState()
    era_config = {"era_id": "wanli1587"}
    out = build_current_location_section(era_config, state)
    assert isinstance(out, str)


# ============= build_system_prompt =============

def test_build_system_prompt_basic():
    """应返回非空 str"""
    state = GameState()
    era_config = {
        "era_id": "nonexistent_era_xyz",  # 无 persona.md
        "era_name": "万历十五年",
        "world": {
            "player_identities": {
                "default": {
                    "role": "小织工",
                    "social_class": "市民",
                    "action_boundaries": {
                        "can_access": ["home", "workshop"],
                        "cannot_access": ["palace"],
                    },
                }
            },
            "default_identity": "default",
            "timeline": {"description": "万历十五年"},
            "iron_laws": [],
            "plausibility_rules": [],
        },
    }
    out = build_system_prompt(era_config, state, "default")
    assert isinstance(out, str)
    assert len(out) > 100