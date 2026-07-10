"""v2.8.0 段三 W12 单元测试

测试目标：
1. PathEvent dataclass
2. 触发器 1（选项触发）：连续 3 次同选项 → SWITCH_MAIN
3. 触发器 2（解锁条件）：value_threshold / always / chapter_reached
4. 触发器 4（章节转化）：just_initialized 时重排
5. apply_events：5 种事件类型
6. ChapterFacade.check_path_events / record_path_choice

约束：
- 0 LLM 调用
- 不影响现有 151 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.paths import (
    NarrativePath,
    PathRegistry,
    PathState,
)
from history_footnote.chapter.path_switcher import (
    PathSwitcher,
    PathEvent,
    OPTION_CONSECUTIVE_THRESHOLD,
)


def make_test_era_config() -> dict:
    return {
        "narrative": {
            "paths": [
                {
                    "id": "main_tax_resistance",
                    "type": "main",
                    "name": "赋税抗争",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6],
                },
                {
                    "id": "side_silk_trade",
                    "type": "side",
                    "name": "丝绸贸易",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6, 7],
                },
                {
                    "id": "corridor_hexi",
                    "type": "corridor",
                    "name": "河西商路",
                    "unlock_condition": "value_threshold",
                    "chapters_applicable": [3, 4, 5, 6, 7],
                },
                {
                    "id": "locked_path",
                    "type": "side",
                    "name": "隐藏路径",
                    "unlock_condition": "chapter_reached:5",
                    "chapters_applicable": [6, 7],
                },
            ],
        },
    }


# ============= 测试 1：PathEvent dataclass =============

def test_V28_114_path_event_dataclass():
    """PathEvent dataclass 创建正确"""
    event = PathEvent(
        type="SWITCH_MAIN",
        path_id="main_tax_resistance",
        priority=80,
        reason="test",
    )
    assert event.type == "SWITCH_MAIN"
    assert event.path_id == "main_tax_resistance"
    assert event.priority == 80
    assert event.payload == {}
    return True


# ============= 测试 2：触发器 1（选项触发） =============

def test_V28_115_trigger_option_consecutive_3():
    """连续 3 次同选项 → SWITCH_MAIN 事件"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.main_path_focus = "main_tax_resistance"
    state.recent_path_choices = ["side_silk_trade"] * 3

    registry = PathRegistry(make_test_era_config())
    switcher = PathSwitcher(state, registry)
    events = switcher.check()
    assert len(events) >= 1
    switch_events = [e for e in events if e.type == "SWITCH_MAIN"]
    assert len(switch_events) == 1
    assert switch_events[0].path_id == "side_silk_trade"
    return True


def test_V28_116_trigger_option_different_choices():
    """最近 3 次选择不全是同一路径 → 不触发"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.main_path_focus = "main_tax_resistance"
    state.recent_path_choices = ["side_silk_trade", "main_tax_resistance", "side_silk_trade"]

    registry = PathRegistry(make_test_era_config())
    switcher = PathSwitcher(state, registry)
    events = switcher.check()
    switch_events = [e for e in events if e.type == "SWITCH_MAIN"]
    assert len(switch_events) == 0
    return True


# ============= 测试 3：触发器 2（解锁条件） =============

def test_V28_117_trigger_unlock_value_threshold():
    """价值维度超阈值 → UNLOCK"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.locked_paths = ["corridor_hexi"]
    state.value_dimensions = {"趋新": 0.7}  # 超 0.5 阈值

    registry = PathRegistry(make_test_era_config())
    switcher = PathSwitcher(state, registry)
    events = switcher.check()
    unlock_events = [e for e in events if e.type == "UNLOCK" and e.path_id == "corridor_hexi"]
    assert len(unlock_events) == 1
    return True


def test_V28_118_trigger_unlock_chapter_reached():
    """chapter_reached:5 → UNLOCK（第 5 章完成后）"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.locked_paths = ["locked_path"]
    state.chapter_state.chapter_history = [{"chapter": 5, "summary": "x"}]

    registry = PathRegistry(make_test_era_config())
    switcher = PathSwitcher(state, registry)
    events = switcher.check()
    unlock_events = [e for e in events if e.type == "UNLOCK" and e.path_id == "locked_path"]
    assert len(unlock_events) == 1
    return True


def test_V28_119_trigger_unlock_not_yet():
    """chapter_reached:5 但第 3 章 → 不 UNLOCK"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.locked_paths = ["locked_path"]
    state.chapter_state.chapter_history = [{"chapter": 3, "summary": "x"}]

    registry = PathRegistry(make_test_era_config())
    switcher = PathSwitcher(state, registry)
    events = switcher.check()
    unlock_events = [e for e in events if e.type == "UNLOCK" and e.path_id == "locked_path"]
    assert len(unlock_events) == 0
    return True


# ============= 测试 4：触发器 4（章节转化） =============

def test_V28_120_trigger_chapter_transition_reorder():
    """章节初始化时重排：dormant → active，incompatible → dormant"""
    from history_footnote.game_state import GameState
    state = GameState()
    # chapter 5 适用 main + side + corridor
    state.chapter_state.current_chapter = 5
    state.chapter_state.just_initialized = True
    # main 在 active，side 在 dormant，corridor 在 active（不需要 unlock 因为已激活）
    state.path_state.active_paths = ["main_tax_resistance", "corridor_hexi"]
    state.path_state.locked_paths = ["side_silk_trade"]  # side 仍 locked

    registry = PathRegistry(make_test_era_config())
    switcher = PathSwitcher(state, registry)
    events = switcher.check()
    reorder_events = [e for e in events if e.type == "REORDER"]
    # 应该至少 1 个 REORDER（至少 side_silk_trade 应当激活）
    assert any(e.path_id == "side_silk_trade" for e in reorder_events)
    return True


# ============= 测试 5：apply_events 5 种类型 =============

def test_V28_121_apply_events_switch_main():
    """apply_events SWITCH_MAIN 修改 main_path_focus"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.main_path_focus = "main_tax_resistance"

    event = PathEvent(type="SWITCH_MAIN", path_id="side_silk_trade", priority=80, reason="test")
    PathSwitcher.apply_events(state, [event])
    assert state.path_state.main_path_focus == "side_silk_trade"
    return True


def test_V28_122_apply_events_unlock():
    """apply_events UNLOCK：locked → active"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.locked_paths = ["corridor_hexi"]

    event = PathEvent(type="UNLOCK", path_id="corridor_hexi", priority=70, reason="test")
    PathSwitcher.apply_events(state, [event])
    assert "corridor_hexi" not in state.path_state.locked_paths
    assert "corridor_hexi" in state.path_state.active_paths
    assert state.path_state.path_affinity["corridor_hexi"] == 0.5  # 默认
    return True


def test_V28_123_apply_events_complete():
    """apply_events COMPLETE：active → completed"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.active_paths = ["main_tax_resistance"]

    event = PathEvent(type="COMPLETE", path_id="main_tax_resistance", priority=60, reason="test")
    PathSwitcher.apply_events(state, [event])
    assert "main_tax_resistance" not in state.path_state.active_paths
    assert "main_tax_resistance" in state.path_state.completed_paths
    return True


# ============= 测试 6：ChapterFacade 路径切换方法 =============

def test_V28_124_facade_check_path_events():
    """ChapterFacade.check_path_events 返回事件列表"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.path_state.main_path_focus = "main_tax_resistance"
    state.recent_path_choices = ["side_silk_trade"] * 3

    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)
    events = facade.check_path_events()
    assert any(e.type == "SWITCH_MAIN" and e.path_id == "side_silk_trade" for e in events)
    return True


def test_V28_125_facade_record_path_choice():
    """ChapterFacade.record_path_choice 记录到 state.recent_path_choices"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    facade.record_path_choice("path_a")
    facade.record_path_choice("path_b")
    facade.record_path_choice("path_c")
    assert state.recent_path_choices == ["path_a", "path_b", "path_c"]

    # 超过 5 个应只保留最近 5 个
    for i in range(10):
        facade.record_path_choice(f"path_{i}")
    assert len(state.recent_path_choices) == 5
    return True


def test_V28_126_facade_apply_path_events():
    """ChapterFacade.apply_path_events 修改 state.path_state"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.path_state.locked_paths = ["test_path"]
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    event = PathEvent(type="UNLOCK", path_id="test_path", priority=70, reason="test")
    facade.apply_path_events([event])
    assert "test_path" in state.path_state.active_paths
    return True
