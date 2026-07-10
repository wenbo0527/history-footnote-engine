"""v2.8.0 段二 W6 单元测试

测试目标：
1. SchemaConverter 节点转换 + 裁剪
2. Validator 4 步校验
3. Fallback 内容保留 + 结构换默认
4. ChapterFacade.convert_llm_to_blueprint 端到端
5. 端到端集成（模拟 LLM 输出 → 引擎 Blueprint）

约束：
- 0 LLM 调用
- 不影响现有 94 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.types import (
    ChapterMeta,
    ChapterBlueprint,
    NodeRole,
    BlueprintNode,
)
from history_footnote.chapter.schema_converter import (
    SchemaConverter,
    MIN_NODES,
    MAX_NODES,
)
from history_footnote.chapter.validator import (
    ChapterValidator,
    validate_chapter_output,
)
from history_footnote.chapter.fallback import (
    ChapterFallback,
    fallback_chapter_blueprint,
)


# 模拟 era_config（含 NPC 和知识条目）
def make_test_era_config() -> dict:
    return {
        "npcs": {
            "npc_zhao_lizhang": {"name": "赵里长"},
            "npc_wang_sao": {"name": "王二嫂"},
            "fm_wife": {"name": "沈氏"},
        },
        "knowledge": {
            "entries": [
                {"id": "kn_silk_price_1587_spring"},
                {"id": "kn_tax_pressure_wanli"},
            ],
        },
        "narrative": {
            "paths": [
                {"id": "main_tax_resistance"},
                {"id": "side_silk_trade"},
            ],
        },
    }


def make_chapter_meta(chapter_id: int = 1) -> ChapterMeta:
    return ChapterMeta(
        chapter_id=chapter_id,
        act="departure",
        role="ordinary",
        emotion_tone="unease→resolve",
        choice_type="whether_to_step_out",
    )


# ============= 测试 1：SchemaConverter =============

def test_V28_57_converter_basic_4_nodes():
    """SchemaConverter 转换 4 节点（正常路径）"""
    llm_output = {
        "chapter_title": "且听下回分解 · 春蚕",
        "chapter_subtitle": "春风又绿江南岸",
        "transition_hint": "season",
        "nodes": [
            {
                "index": 1,
                "role": "introduction",
                "scene": "盛泽镇春市开张",
                "npc_ids": ["fm_wife"],
                "option_directions": [{"text": "赶集", "path": "main_tax_resistance"}],
                "knowledge_ids": ["kn_silk_price_1587_spring"],
                "completion_condition": "round_4_reached",
            },
            {"index": 2, "role": "escalation", "scene": "春税下来", "npc_ids": ["npc_zhao_lizhang"]},
            {"index": 3, "role": "climax", "scene": "赵里长催税"},
            {"index": 4, "role": "resolution", "scene": "春蚕上簇"},
        ],
    }
    converter = SchemaConverter(make_test_era_config())
    meta = make_chapter_meta()
    blueprint = converter.convert(llm_output, meta)

    assert blueprint.chapter_id == 1
    assert "春蚕" in blueprint.chapter_title
    assert blueprint.meta is not None
    assert len(blueprint.nodes) == 4
    assert blueprint.nodes[0].role == "introduction"
    assert blueprint.nodes[0].scene == "盛泽镇春市开张"
    return True


def test_V28_58_converter_truncates_excess_nodes():
    """SchemaConverter 节点过多时截断到 MAX_NODES"""
    llm_output = {
        "nodes": [{"index": i, "role": "introduction", "scene": f"node {i}"} for i in range(1, 10)]
    }
    converter = SchemaConverter({})
    blueprint = converter.convert(llm_output, make_chapter_meta())
    assert len(blueprint.nodes) == MAX_NODES
    return True


def test_V28_59_converter_pads_insufficient_nodes():
    """SchemaConverter 节点过少时补齐到 MIN_NODES"""
    llm_output = {
        "nodes": [
            {"index": 1, "role": "introduction", "scene": "only one node"},
        ]
    }
    converter = SchemaConverter({})
    blueprint = converter.convert(llm_output, make_chapter_meta())
    assert len(blueprint.nodes) >= MIN_NODES
    return True


def test_V28_60_converter_role_string_to_enum():
    """SchemaConverter 把 role 字符串归一化"""
    llm_output = {
        "nodes": [
            {"index": 1, "role": "INTRO"},  # 大写
            {"index": 2, "role": "Escalation"},
            {"index": 3, "role": "climax"},
            {"index": 4, "role": "resolution"},
        ]
    }
    converter = SchemaConverter({})
    blueprint = converter.convert(llm_output, make_chapter_meta())
    # 容错后应都是合法角色
    for n in blueprint.nodes:
        assert n.role in ("introduction", "escalation", "climax", "resolution")
    return True


# ============= 测试 2：Validator =============

def test_V28_61_validator_pass_valid_output():
    """Validator 通过合法 LLM 输出"""
    llm_output = {
        "nodes": [
            {"role": "introduction", "npc_ids": ["npc_zhao_lizhang"], "knowledge_ids": ["kn_silk_price_1587_spring"], "option_directions": [{"text": "x", "path": "main_tax_resistance"}]},
            {"role": "escalation"},
            {"role": "climax"},
            {"role": "resolution"},
        ]
    }
    validator = ChapterValidator(make_test_era_config())
    errors = validator.validate(llm_output)
    assert errors == [], f"期望通过，实际错误: {errors}"
    return True


def test_V28_62_validator_fail_invalid_npc():
    """Validator 失败：NPC 不存在"""
    llm_output = {
        "nodes": [
            {"role": "introduction", "npc_ids": ["npc_nonexistent"]},
            {"role": "escalation"},
            {"role": "climax"},
            {"role": "resolution"},
        ]
    }
    validator = ChapterValidator(make_test_era_config())
    errors = validator.validate(llm_output)
    assert len(errors) > 0
    assert any("NPC 不存在" in e for e in errors)
    return True


def test_V28_63_validator_fail_node_count():
    """Validator 失败：节点数过多"""
    llm_output = {
        "nodes": [{"role": "introduction"} for _ in range(8)]
    }
    validator = ChapterValidator({})
    errors = validator.validate(llm_output)
    assert any("节点数" in e for e in errors)
    return True


def test_V28_64_validator_fail_node_role_order():
    """Validator 失败：节点角色顺序错乱"""
    llm_output = {
        "nodes": [
            {"role": "climax"},  # 第一个就是 climax
            {"role": "introduction"},
            {"role": "resolution"},
        ]
    }
    validator = ChapterValidator({})
    errors = validator.validate(llm_output)
    assert any("introduction" in e for e in errors)
    return True


# ============= 测试 3：Fallback =============

def test_V28_65_fallback_preserves_content():
    """Fallback 保留 LLM 节点内容（scene/npc/options）"""
    llm_output = {
        "chapter_title": "LLM 写的好标题",
        "nodes": [
            {
                "index": 1,
                "role": "wrong_role",  # 故意错的 role
                "scene": "LLM 写的独特场景",
                "npc_ids": ["npc_zhao_lizhang"],
                "option_directions": [{"text": "选项 A", "path": "main_tax_resistance"}],
                "knowledge_ids": ["kn_silk_price_1587_spring"],
                "completion_condition": "wrong_condition",  # 故意错的 condition
            },
        ]
    }
    meta = make_chapter_meta()
    blueprint = ChapterFallback.fallback(llm_output, meta, errors=["测试错误"])

    assert "LLM 写的好标题" in blueprint.chapter_title  # 保留
    assert len(blueprint.nodes) == 4  # 默认 4 节点
    # 内容保留：第 1 节点的 scene 是 LLM 写的
    assert blueprint.nodes[0].scene == "LLM 写的独特场景"
    assert blueprint.nodes[0].npc_ids == ["npc_zhao_lizhang"]
    # 结构换默认：role 是 introduction（不是 LLM 写的 wrong_role）
    assert blueprint.nodes[0].role == "introduction"
    # completion_condition 用默认
    assert blueprint.nodes[0].completion_condition == "round_4_reached"
    return True


def test_V28_66_fallback_handles_empty_input():
    """Fallback 处理空输入（不抛异常）"""
    meta = make_chapter_meta()
    blueprint = ChapterFallback.fallback({}, meta, errors=[])
    assert len(blueprint.nodes) == 4
    assert blueprint.chapter_id == 1
    return True


# ============= 测试 4：ChapterFacade.convert_llm_to_blueprint =============

def test_V28_67_facade_convert_valid():
    """ChapterFacade.convert_llm_to_blueprint 通过合法输出"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )
    llm_output = {
        "nodes": [
            {"role": "introduction", "npc_ids": ["fm_wife"], "option_directions": [{"text": "x", "path": "main_tax_resistance"}]},
            {"role": "escalation", "npc_ids": ["npc_zhao_lizhang"]},
            {"role": "climax"},
            {"role": "resolution"},
        ]
    }
    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=1)
    assert blueprint.chapter_id == 1
    assert blueprint.meta.act == "departure"
    assert len(blueprint.nodes) == 4
    return True


def test_V28_68_facade_convert_with_fallback():
    """ChapterFacade.convert_llm_to_blueprint 校验失败触发兑底"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )
    # LLM 输出有 5 节点（最后 2 个 role 重复 resolution）→ 触发 validator 失败
    llm_output = {
        "chapter_title": "5 节点测试",
        "nodes": [
            {"role": "introduction", "scene": "scene 1", "npc_ids": ["fm_wife"]},
            {"role": "escalation", "scene": "scene 2", "npc_ids": ["npc_zhao_lizhang"]},
            {"role": "climax", "scene": "scene 3", "npc_ids": ["npc_wang_sao"]},
            {"role": "resolution", "scene": "scene 4", "npc_ids": ["fm_wife"]},
            {"role": "resolution", "scene": "scene 5", "npc_ids": ["npc_zhao_lizhang"]},
        ]
    }
    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=1)
    # 校验失败（最后节点非 resolution 在中间... 实际是 5 节点最后是 resolution 但中间有 resolution）
    # 触发 fallback → 默认 4 节点
    assert len(blueprint.nodes) == 4
    return True


def test_V28_69_facade_convert_invalid_npc_triggers_fallback():
    """ChapterFacade 非法 NPC 触发 fallback（内容保留）"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )
    llm_output = {
        "chapter_title": "非法 NPC 测试",
        "nodes": [
            {"role": "introduction", "scene": "valid scene", "npc_ids": ["npc_nonexistent"]},  # 非法
            {"role": "escalation"},
            {"role": "climax"},
            {"role": "resolution"},
        ]
    }
    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=1)
    # 校验失败 → fallback → 内容保留（scene）+ 结构换默认
    assert blueprint.chapter_title == "非法 NPC 测试"
    assert blueprint.nodes[0].scene == "valid scene"  # LLM 写的场景保留
    assert blueprint.nodes[0].role == "introduction"  # 默认 role
    return True


# ============= 测试 5：端到端集成 =============

def test_V28_70_end_to_end_simulate_llm_output():
    """端到端：模拟 LLM 完整输出 → 引擎 Blueprint"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    # 用含 hero_journey_acts 的 era_config
    era_config = make_test_era_config()
    era_config["narrative"]["hero_journey_acts"] = [
        {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
        {"act": "initiation", "chapters": [4, 5, 6, 7], "chapter_roles": ["trial", "allies", "abyss_approach", "abyss"], "emotion_tone": "tension→awakening", "choice_type": "how_to_face_challenge"},
    ]
    facade = ChapterFacade(
        state=state,
        era_config=era_config,
        root_dir=Path(__file__).parent.parent,
    )

    # 模拟 LLM 完整输出
    llm_output = {
        "chapter_title": "且听下回分解 · 夏税",
        "chapter_subtitle": "烈日当空",
        "transition_hint": "season",
        "nodes": [
            {
                "index": 1,
                "role": "introduction",
                "scene": "六月盛夏，知了在桑林里叫得人发慌",
                "npc_ids": ["fm_wife", "fm_wife"],
                "option_directions": [
                    {"text": "去苏州卖丝", "path": "side_silk_trade"},
                    {"text": "继续在家织布", "path": "main_tax_resistance"},
                ],
                "knowledge_ids": ["kn_silk_price_1587_spring"],
                "completion_condition": "round_4_reached",
            },
            {
                "index": 2,
                "role": "escalation",
                "scene": "夏税预单又来了",
                "npc_ids": ["npc_zhao_lizhang"],
                "option_directions": [
                    {"text": "硬抗", "path": "main_tax_resistance"},
                ],
                "completion_condition": "round_8_reached",
            },
            {
                "index": 3,
                "role": "climax",
                "scene": "衙役登门",
                "completion_condition": "round_12_reached",
            },
            {
                "index": 4,
                "role": "resolution",
                "scene": "全家动员夜织",
                "completion_condition": "round_16_reached",
            },
        ],
    }

    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=2)

    # 验证元属性（chapter 2 → departure/call，departure 段第 2 个）
    assert blueprint.meta.act == "departure"
    assert blueprint.meta.role == "call"

    # 验证节点内容保留
    assert "知了" in blueprint.nodes[0].scene
    assert "夏税" in blueprint.nodes[1].scene
    assert blueprint.nodes[0].npc_ids == ["fm_wife", "fm_wife"]

    # 验证结构默认
    assert len(blueprint.nodes) == 4
    assert blueprint.nodes[0].role == "introduction"
    assert blueprint.nodes[3].role == "resolution"
    return True
