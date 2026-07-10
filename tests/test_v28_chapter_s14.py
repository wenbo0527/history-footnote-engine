"""v2.8.0 段四 W14 单元测试

测试目标：
1. SchemaConverter.apply_build_differentiation 覆盖 scene 和 options
2. 不同 Build 看到不同场景（守乡人 vs 外望人）
3. chapter1_blueprint.json differentiation 字段
4. ChapterFacade.convert_llm_to_blueprint + player_build
5. 端到端：同 seed 不同 Build 体验不同

约束：
- 0 LLM 调用
- 不影响现有 172 测试
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.types import ChapterMeta, ChapterBlueprint, BlueprintNode
from history_footnote.chapter.schema_converter import (
    SchemaConverter,
    apply_build_differentiation,
)


# ============= 测试 1：SchemaConverter apply_build_differentiation =============

def test_V28_135_schema_converter_applies_build_differentiation():
    """SchemaConverter.apply_build_differentiation 覆盖 scene"""
    blueprint = ChapterBlueprint(
        chapter_id=1,
        chapter_title="test",
        nodes=[
            BlueprintNode(index=1, role="introduction", scene="原 scene 1", option_directions=[
                {"text": "原选项 A", "path": "p1"},
            ]),
            BlueprintNode(index=2, role="escalation", scene="原 scene 2"),
        ],
    )
    llm_output = {
        "differentiation": {
            "守乡人": {
                "node_1_scene": "守乡人看到的 scene 1",
                "node_1_options": [{"text": "守乡人选项 A", "path": "p1"}],
            }
        }
    }
    converter = SchemaConverter()
    converter.apply_build_differentiation(blueprint, llm_output, "守乡人")
    assert blueprint.nodes[0].scene == "守乡人看到的 scene 1"
    assert blueprint.nodes[0].option_directions[0]["text"] == "守乡人选项 A"
    # 未覆盖的节点保持默认
    assert blueprint.nodes[1].scene == "原 scene 2"
    return True


def test_V28_136_schema_converter_no_differentiation_keeps_default():
    """无 differentiation 数据 → 保持默认 scene/options"""
    blueprint = ChapterBlueprint(
        chapter_id=1,
        nodes=[BlueprintNode(index=1, role="introduction", scene="原 scene", option_directions=[{"text": "原选项"}])],
    )
    llm_output = {}  # 无 differentiation
    converter = SchemaConverter()
    converter.apply_build_differentiation(blueprint, llm_output, "守乡人")
    assert blueprint.nodes[0].scene == "原 scene"
    assert blueprint.nodes[0].option_directions[0]["text"] == "原选项"
    return True


def test_V28_137_schema_converter_unknown_build_keeps_default():
    """unknown build → 保持默认"""
    blueprint = ChapterBlueprint(
        chapter_id=1,
        nodes=[BlueprintNode(index=1, role="introduction", scene="原 scene")],
    )
    llm_output = {
        "differentiation": {
            "守乡人": {"node_1_scene": "守乡人 scene"}
            # 没有"外望人"
        }
    }
    converter = SchemaConverter()
    converter.apply_build_differentiation(blueprint, llm_output, "外望人")
    assert blueprint.nodes[0].scene == "原 scene"  # 未覆盖
    return True


# ============= 测试 2：chapter1_blueprint.json differentiation 加载 =============

def test_V28_138_chapter1_blueprint_has_differentiation():
    """chapter1_blueprint.json 含 differentiation 字段"""
    blueprint_path = Path(__file__).parent.parent / "eras" / "wanli1587" / "chapter1_blueprint.json"
    data = json.loads(blueprint_path.read_text(encoding="utf-8"))
    assert "differentiation" in data
    assert "守乡人" in data["differentiation"]
    assert "外望人" in data["differentiation"]
    # 守乡人有 node_3_scene
    assert "node_3_scene" in data["differentiation"]["守乡人"]
    # 外望人有 node_1_scene 和 node_2_scene
    assert "node_1_scene" in data["differentiation"]["外望人"]
    assert "node_2_scene" in data["differentiation"]["外望人"]
    return True


def test_V28_139_facade_loads_chapter1_differentiation():
    """ChapterFacade 加载 chapter1 含 differentiation"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    blueprint = facade.load_blueprint(1)
    assert blueprint is not None
    # blueprint 本身没存 differentiation（只存 nodes）
    # 但通过 facade.convert_llm_to_blueprint + player_build 可触发分化
    return True


# ============= 测试 3：ChapterFacade.convert_llm_to_blueprint + player_build =============

def test_V28_140_facade_convert_with_build_differentiation():
    """ChapterFacade.convert_llm_to_blueprint 应用 Build 分化"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.player_build = "守乡人"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    llm_output = {
        "nodes": [
            {"role": "introduction", "scene": "默认 scene 1", "npc_ids": ["fm_wife"]},
            {"role": "escalation", "scene": "默认 scene 2"},
            {"role": "climax", "scene": "默认 scene 3", "npc_ids": ["npc_zhao_lizhang"]},
            {"role": "resolution", "scene": "默认 scene 4"},
        ],
        "differentiation": {
            "守乡人": {
                "node_3_scene": "守乡人 node 3 scene"
            }
        }
    }
    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=1)
    # node 1/2/4 不变
    assert blueprint.nodes[0].scene == "默认 scene 1"
    assert blueprint.nodes[1].scene == "默认 scene 2"
    # node 3 被覆盖
    assert blueprint.nodes[2].scene == "守乡人 node 3 scene"
    assert blueprint.nodes[3].scene == "默认 scene 4"
    return True


def test_V28_141_facade_convert_explicit_player_build_overrides_state():
    """ChapterFacade 显式 player_build 覆盖 state"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.player_build = "守乡人"  # state 是守乡人
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    llm_output = {
        "nodes": [
            {"role": "introduction", "scene": "默认 scene"},
        ],
        "differentiation": {
            "守乡人": {"node_1_scene": "守乡人 scene"},
            "外望人": {"node_1_scene": "外望人 scene"},
        }
    }
    # 显式传 player_build="外望人" 覆盖 state
    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=1, player_build="外望人")
    assert blueprint.nodes[0].scene == "外望人 scene"
    return True


# ============= 测试 4：同 seed 不同 Build 体验不同 =============

def test_V28_142_same_seed_different_build_different_experience():
    """同 seed 不同 Build 看到不同 node.scene"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    # 共享的 LLM 输出（模拟同 seed）
    shared_llm_output = {
        "nodes": [
            {"role": "introduction", "scene": "默认 intro"},
            {"role": "escalation", "scene": "默认 esc"},
            {"role": "climax", "scene": "默认 climax"},
            {"role": "resolution", "scene": "默认 res"},
        ],
        "differentiation": {
            "守乡人": {
                "node_1_scene": "守乡人在盛泽镇的家门口",
                "node_3_scene": "守乡人面对赵里长催税，攥紧拳头",
            },
            "外望人": {
                "node_1_scene": "外望人站在盛泽镇最高处，远眺江南",
                "node_2_scene": "外望人听到河西商路消息，心潮起伏",
            }
        }
    }

    # 守乡人 玩
    state_守乡人 = GameState()
    state_守乡人.player_build = "守乡人"
    facade_守乡人 = ChapterFacade(state=state_守乡人, era_config={}, root_dir=Path(__file__).parent.parent)
    bp_守乡人 = facade_守乡人.convert_llm_to_blueprint(shared_llm_output, chapter_id=1)

    # 外望人 玩
    state_外望人 = GameState()
    state_外望人.player_build = "外望人"
    facade_外望人 = ChapterFacade(state=state_外望人, era_config={}, root_dir=Path(__file__).parent.parent)
    bp_外望人 = facade_外望人.convert_llm_to_blueprint(shared_llm_output, chapter_id=1)

    # 验证体验不同
    assert bp_守乡人.nodes[0].scene == "守乡人在盛泽镇的家门口"
    assert bp_外望人.nodes[0].scene == "外望人站在盛泽镇最高处，远眺江南"
    assert bp_守乡人.nodes[1].scene == "默认 esc"  # 守乡人无 node_2 分化
    assert bp_外望人.nodes[1].scene == "外望人听到河西商路消息，心潮起伏"
    assert bp_守乡人.nodes[2].scene == "守乡人面对赵里长催税，攥紧拳头"
    assert bp_外望人.nodes[2].scene == "默认 climax"  # 外望人无 node_3 分化
    return True


# ============= 测试 5：端到端（用真实 chapter1_blueprint.json） =============

def test_V28_143_real_blueprint_with_build_differentiation():
    """真实 chapter1_blueprint.json + 守乡人 build"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.player_build = "守乡人"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    # 模拟 LLM 输出（用真实蓝图内容 + differentiation）
    blueprint_json = json.loads(
        (Path(__file__).parent.parent / "eras" / "wanli1587" / "chapter1_blueprint.json").read_text(encoding="utf-8")
    )
    # 真实 differentiation 已在 JSON 里
    blueprint = facade.convert_llm_to_blueprint(blueprint_json, chapter_id=1)

    # 守乡人 node 3 应被覆盖（特定场景）
    node_3 = blueprint.nodes[2]
    assert "父亲留下的家训" in node_3.scene
    assert "把织机抵出去" in str(node_3.option_directions)
    return True


def test_V28_144_real_blueprint_with_外望人_differentiation():
    """真实 chapter1_blueprint.json + 外望人 build"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.player_build = "外望人"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    blueprint_json = json.loads(
        (Path(__file__).parent.parent / "eras" / "wanli1587" / "chapter1_blueprint.json").read_text(encoding="utf-8")
    )
    blueprint = facade.convert_llm_to_blueprint(blueprint_json, chapter_id=1)

    # 外望人 node 1 应被覆盖（远眺/春市最高处）
    node_1 = blueprint.nodes[0]
    assert "春市最高处" in node_1.scene  # 外望人分化标识
    assert "河西走廊" in node_1.scene
    # 外望人 node 2 应被覆盖（苏州府请愿）
    node_2 = blueprint.nodes[1]
    assert "苏州府" in node_2.scene
    return True
