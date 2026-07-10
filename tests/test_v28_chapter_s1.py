"""v2.8.0 段一 W1 单元测试

测试目标：
1. ChapterState 序列化往返一致（不破 v2.7 重放承诺）
2. ChapterBlueprint 从 JSON 加载正确
3. GameState.chapter_state 字段接入正确（旧存档无此字段不报错）
4. chapter1_blueprint.json 4 节点结构正确

约束：
- 不依赖 LLM
- 不修改 era.json
- 不影响现有 38 测试
"""
import json
import sys
from pathlib import Path

# 让 pytest 能 import src/history_footnote
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.types import (
    ChapterState,
    ChapterBlueprint,
    BlueprintNode,
    NodeRole,
    TransitionType,
    ClosureStatus,
    is_chapter_active,
    make_default_chapter_state,
)


# ============= 测试 1：ChapterState 序列化往返 =============

def test_V28_01_chapter_state_default():
    """默认 ChapterState 字段全部为初值"""
    cs = ChapterState()
    assert cs.current_chapter == 0
    assert cs.current_node == 1
    assert cs.chapter_start_round == 1
    assert cs.blueprint is None
    assert cs.last_closure_status == "INIT"
    assert cs.chapter_history == []
    return True


def test_V28_02_chapter_state_serialization_roundtrip():
    """ChapterState JSON 序列化往返一致（关键：v2.7 重放兼容）"""
    cs = ChapterState(
        current_chapter=2,
        current_node=3,
        chapter_start_round=10,
        blueprint={"chapter_id": 2, "title": "test"},
        last_closure_status="CONTINUE",
        chapter_history=[{"chapter": 1, "summary": "test"}],
    )

    # 序列化
    data = cs.to_dict()
    json_str = json.dumps(data, ensure_ascii=False)

    # 反序列化
    data2 = json.loads(json_str)
    cs2 = ChapterState.from_dict(data2)

    # 字段一致
    assert cs2.current_chapter == 2
    assert cs2.current_node == 3
    assert cs2.chapter_start_round == 10
    assert cs2.blueprint == {"chapter_id": 2, "title": "test"}
    assert cs2.last_closure_status == "CONTINUE"
    assert cs2.chapter_history == [{"chapter": 1, "summary": "test"}]
    return True


def test_V28_03_chapter_state_from_empty_dict():
    """空 dict 反序列化不报错（容错）"""
    cs = ChapterState.from_dict({})
    assert cs.current_chapter == 0
    assert cs.current_node == 1
    return True


def test_V28_04_chapter_state_from_none():
    """None 反序列化为默认对象（存档迁移用）"""
    cs = ChapterState.from_dict(None)
    assert cs.current_chapter == 0
    return True


# ============= 测试 2：ChapterBlueprint 加载 =============

def test_V28_05_chapter_blueprint_from_json():
    """从 JSON 加载第 1 章蓝图"""
    blueprint_path = Path(__file__).parent.parent / "eras" / "wanli1587" / "chapter1_blueprint.json"
    assert blueprint_path.exists(), f"蓝图文件不存在: {blueprint_path}"

    json_str = blueprint_path.read_text(encoding="utf-8")
    blueprint = ChapterBlueprint.from_json(json_str)

    assert blueprint.chapter_id == 1
    assert "春蚕" in blueprint.chapter_title
    assert len(blueprint.nodes) == 4  # 段一硬编码 4 节点
    assert blueprint.transition_hint == "season"
    return True


def test_V28_06_chapter_blueprint_nodes_order():
    """4 节点按角色顺序排列（introduction→...→resolution）"""
    blueprint_path = Path(__file__).parent.parent / "eras" / "wanli1587" / "chapter1_blueprint.json"
    blueprint = ChapterBlueprint.from_json(blueprint_path.read_text(encoding="utf-8"))

    expected_roles = ["introduction", "escalation", "climax", "resolution"]
    actual_roles = [n.role for n in blueprint.nodes]
    assert actual_roles == expected_roles, f"节点顺序错误: {actual_roles}"

    # 节点 index 连续 1-4
    for i, node in enumerate(blueprint.nodes, start=1):
        assert node.index == i, f"节点 {i} 的 index 字段错误: {node.index}"
    return True


def test_V28_07_chapter_blueprint_options_have_path_hint():
    """每个节点的选项都有 path_hint 字段（段三路径三态用）"""
    blueprint_path = Path(__file__).parent.parent / "eras" / "wanli1587" / "chapter1_blueprint.json"
    blueprint = ChapterBlueprint.from_json(blueprint_path.read_text(encoding="utf-8"))

    for node in blueprint.nodes:
        assert len(node.option_directions) >= 3, f"节点 {node.index} 选项少于 3 个"
        for opt in node.option_directions:
            assert "text" in opt, f"节点 {node.index} 选项缺 text 字段"
            assert "path_hint" in opt, f"节点 {node.index} 选项缺 path_hint 字段"
    return True


# ============= 测试 3：GameState 接入 =============

def test_V28_08_game_state_has_chapter_state():
    """GameState 有 chapter_state 字段"""
    from history_footnote.game_state import GameState
    gs = GameState()
    assert hasattr(gs, "chapter_state"), "GameState 缺 chapter_state 字段"
    assert isinstance(gs.chapter_state, ChapterState)
    return True


def test_V28_09_game_state_chapter_state_default():
    """GameState 默认 chapter_state 是空 ChapterState"""
    from history_footnote.game_state import GameState
    gs = GameState()
    assert gs.chapter_state.current_chapter == 0
    assert gs.chapter_state.current_node == 1
    return True


def test_V28_10_game_state_to_dict_includes_chapter_state():
    """GameState.to_dict() 包含 chapter_state 字段（存档兼容）"""
    from history_footnote.game_state import GameState
    gs = GameState()
    data = gs.to_dict()
    assert "chapter_state" in data, "to_dict 缺 chapter_state 字段"
    assert data["chapter_state"]["current_chapter"] == 0
    return True


def test_V28_11_game_state_old_save_compatible():
    """旧存档（无 chapter_state 字段）反序列化不报错

    验证方式：直接构造 GameState 不传 chapter_state，
    确认 default_factory 自动建空对象。
    """
    from history_footnote.game_state import GameState

    # 模拟旧存档场景：不传 chapter_state 参数构造
    gs = GameState()  # 全部默认值
    # 应该有默认 chapter_state
    assert gs.chapter_state is not None, "GameState() 缺默认 chapter_state"
    assert gs.chapter_state.current_chapter == 0
    assert gs.chapter_state.current_node == 1
    assert gs.chapter_state.last_closure_status == "INIT"
    return True


# ============= 测试 4：枚举容错 =============

def test_V28_12_node_role_from_string():
    """NodeRole.from_string 容错"""
    assert NodeRole.from_string("introduction") == NodeRole.INTRODUCTION
    assert NodeRole.from_string("invalid_role") == NodeRole.INTRODUCTION  # 回退
    return True


def test_V28_13_transition_type_from_string():
    """TransitionType.from_string 容错"""
    assert TransitionType.from_string("season") == TransitionType.SEASON
    assert TransitionType.from_string("xxx") == TransitionType.SEASON  # 回退
    return True


# ============= 测试 5：工具函数 =============

def test_V28_14_is_chapter_active():
    """is_chapter_active 工具函数"""
    cs = ChapterState()
    assert is_chapter_active(cs) is False  # current_chapter=0

    cs2 = ChapterState(current_chapter=1)
    assert is_chapter_active(cs2) is True
    return True


def test_V28_15_make_default_chapter_state():
    """工厂函数创建默认 ChapterState"""
    cs = make_default_chapter_state()
    assert isinstance(cs, ChapterState)
    assert cs.current_chapter == 0
    return True
