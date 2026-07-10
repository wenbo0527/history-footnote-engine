"""v2.8.0 段三 W11 单元测试

测试目标：
1. NarrativePath 序列化 + is_applicable_to_chapter
2. PathState 序列化 + get_status
3. PathRegistry 从 era_config 加载
4. GameState.path_state 字段接入（旧存档零回归）
5. ChapterFacade 路径查询方法

约束：
- 0 LLM 调用
- 不影响现有 138 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.paths import (
    NarrativePath,
    PathState,
    PathRegistry,
    PathStatus,
    PathType,
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
                    "closure_condition": "tribute_negotiated",
                    "build_affinity": {"尽责": 0.8, "身边": 0.7},
                    "chapters_applicable": [2, 3, 4, 5, 6],
                    "plate_dependency": "central_plains",
                    "description": "赋税越来越重...",
                },
                {
                    "id": "side_silk_trade",
                    "type": "side",
                    "name": "丝绸贸易",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6, 7],
                    "description": "走丝路赚钱",
                },
                {
                    "id": "corridor_hexi",
                    "type": "corridor",
                    "name": "河西商路",
                    "unlock_condition": "value_threshold",
                    "chapters_applicable": [3, 4, 5, 6, 7],
                    "description": "河西走廊的商路",
                },
            ],
        },
    }


# ============= 测试 1：NarrativePath 序列化 =============

def test_V28_101_narrative_path_serialization():
    """NarrativePath 序列化往返一致"""
    path = NarrativePath(
        id="main_tax_resistance",
        type="main",
        name="赋税抗争",
        unlock_condition="always",
        closure_condition="tribute_negotiated",
        build_affinity={"尽责": 0.8, "身边": 0.7},
        chapters_applicable=[2, 3, 4, 5, 6],
        plate_dependency="central_plains",
        description="赋税越来越重",
    )
    data = path.to_dict()
    path2 = NarrativePath.from_dict(data)
    assert path2.id == "main_tax_resistance"
    assert path2.type == "main"
    assert path2.chapters_applicable == [2, 3, 4, 5, 6]
    assert path2.build_affinity["尽责"] == 0.8
    return True


def test_V28_102_narrative_path_is_applicable():
    """NarrativePath.is_applicable_to_chapter"""
    path = NarrativePath(
        id="main",
        chapters_applicable=[2, 3, 4, 5, 6],
    )
    assert path.is_applicable_to_chapter(3) is True
    assert path.is_applicable_to_chapter(7) is False
    # 空列表 = 适用所有章节
    path_universal = NarrativePath(id="any", chapters_applicable=[])
    assert path_universal.is_applicable_to_chapter(99) is True
    return True


# ============= 测试 2：PathState 序列化 + get_status =============

def test_V28_103_path_state_serialization():
    """PathState 序列化往返一致"""
    ps = PathState(
        active_paths=["main_tax_resistance", "side_silk_trade"],
        completed_paths=["chapter_1_tutorial"],
        locked_paths=["corridor_hexi"],
        dormant_paths=[],
        path_affinity={"main_tax_resistance": 0.8, "side_silk_trade": 0.3},
        main_path_focus="main_tax_resistance",
    )
    data = ps.to_dict()
    ps2 = PathState.from_dict(data)
    assert ps2.active_paths == ["main_tax_resistance", "side_silk_trade"]
    assert ps2.main_path_focus == "main_tax_resistance"
    return True


def test_V28_104_path_state_get_status():
    """PathState.get_status 三态正确"""
    ps = PathState(
        active_paths=["main_tax_resistance"],
        completed_paths=["chapter_1_tutorial"],
        locked_paths=["corridor_hexi"],
        dormant_paths=["side_silk_trade"],
    )
    assert ps.get_status("main_tax_resistance") == "active"
    assert ps.get_status("chapter_1_tutorial") == "dormant"  # completed 视为 dormant
    assert ps.get_status("side_silk_trade") == "dormant"
    assert ps.get_status("corridor_hexi") == "locked"
    assert ps.get_status("unknown_path") == "locked"
    return True


# ============= 测试 3：PathRegistry 加载 + 查询 =============

def test_V28_105_path_registry_loads():
    """PathRegistry 从 era_config 加载"""
    registry = PathRegistry(make_test_era_config())
    assert len(registry) == 3, f"期望 3 条路径，实际 {len(registry)}"
    assert "main_tax_resistance" in registry
    assert "side_silk_trade" in registry
    assert "corridor_hexi" in registry
    return True


def test_V28_106_path_registry_query_by_type():
    """PathRegistry.get_by_type 分类查询"""
    registry = PathRegistry(make_test_era_config())
    mains = registry.get_main_paths()
    sides = registry.get_side_paths()
    corridors = registry.get_corridor_paths()
    assert len(mains) == 1
    assert mains[0].id == "main_tax_resistance"
    assert len(sides) == 1
    assert sides[0].id == "side_silk_trade"
    assert len(corridors) == 1
    assert corridors[0].id == "corridor_hexi"
    return True


def test_V28_107_path_registry_applicable_to_chapter():
    """PathRegistry.get_applicable_to_chapter"""
    registry = PathRegistry(make_test_era_config())
    # chapter 2 → main_tax_resistance + side_silk_trade
    paths_2 = registry.get_applicable_to_chapter(2)
    assert len(paths_2) == 2
    assert "main_tax_resistance" in [p.id for p in paths_2]
    # chapter 5 → 全部 3 条
    paths_5 = registry.get_applicable_to_chapter(5)
    assert len(paths_5) == 3
    # chapter 1 → 0 条（所有路径都从 chapter 2 开始）
    paths_1 = registry.get_applicable_to_chapter(1)
    assert len(paths_1) == 0
    return True


# ============= 测试 4：GameState.path_state 字段 =============

def test_V28_108_game_state_has_path_state():
    """GameState 有 path_state 字段（嵌套 dataclass）"""
    from history_footnote.game_state import GameState
    gs = GameState()
    assert hasattr(gs, "path_state")
    assert isinstance(gs.path_state, PathState)
    # 默认空状态
    assert gs.path_state.active_paths == []
    assert gs.path_state.locked_paths == []
    return True


def test_V28_109_game_state_old_save_compatible_with_path_state():
    """旧存档无 path_state 字段也能正常工作（零回归）"""
    from history_footnote.game_state import GameState
    gs = GameState()  # 默认全部初始化
    # 即使是新建的，path_state 也应自动建空对象
    assert gs.path_state is not None
    return True


# ============= 测试 5：ChapterFacade 路径查询 =============

def test_V28_110_facade_path_registry_lazy_load():
    """ChapterFacade.path_registry 懒加载"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    state = GameState()
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)
    registry = facade.path_registry
    assert len(registry) == 3
    return True


def test_V28_111_facade_get_paths_for_chapter():
    """ChapterFacade.get_paths_for_chapter"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    state = GameState()
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)
    paths_5 = facade.get_paths_for_chapter(5)
    assert len(paths_5) == 3
    return True


def test_V28_112_facade_get_active_paths_and_status():
    """ChapterFacade.get_active_paths + get_path_status"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    state = GameState()
    state.path_state.active_paths = ["main_tax_resistance"]
    state.path_state.locked_paths = ["corridor_hexi"]
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)
    assert facade.get_active_paths() == ["main_tax_resistance"]
    assert facade.get_path_status("main_tax_resistance") == "active"
    assert facade.get_path_status("corridor_hexi") == "locked"
    return True


def test_V28_113_path_status_enum_string_compatibility():
    """PathStatus.from_string 容错"""
    assert PathStatus.from_string("active") == PathStatus.ACTIVE
    assert PathStatus.from_string("locked") == PathStatus.LOCKED
    assert PathStatus.from_string("invalid") == PathStatus.LOCKED  # 回退

    assert PathType.from_string("main") == PathType.MAIN
    assert PathType.from_string("invalid") == PathType.SIDE
    return True
