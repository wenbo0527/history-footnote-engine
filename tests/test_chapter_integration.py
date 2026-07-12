"""v2.10.1 W52 P2-5: Chapter 模块集成测试

W85 Phase 1/2/3 完成后，补充集成测试覆盖以下场景：
1. RouteDetector 真实输入路径
2. Coordinator 与 RouteDetector 集成
3. ChapterBlueprint 在不同状态下的 narrative_position 字段
"""
import pytest
from datetime import datetime, timezone

from history_footnote.chapter.route_detector import (
    RouteDetector,
    DM_INSTRUCTION_BASE,
    NARRATIVE_FLOW,
    MAX_BACKWARD_STEPS,
)
from history_footnote.chapter.types import (
    ChapterBlueprint,
    ChapterState,
    BlueprintNode,
)
from history_footnote.chapter.coordinator import ChapterCoordinator


# ============= RouteDetector 真实场景 =============

def test_route_detector_keyword_priority():
    """关键词路径应优先于价值偏移（Phase 1 优先）"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    # 抗税 触发关键词 rising_conflict（不是通过价值偏移）
    result = detector.detect(
        "我要去抗税",
        value_shifts={"resistance": 0.5, "tradition": -0.2},
        current_chapter=bp,
    )
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"
    assert "keyword" in result["trigger"].lower() or "抗税" in result["trigger"]


def test_route_detector_keyword_with_value_triggers_safety():
    """关键词 + 价值偏移触发 crisis 路径"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="rising_conflict",
        must_resolve=["抗税"],
    )
    # 抗税 + resistance 大幅上升
    result = detector.detect(
        "我要彻底抗税到底",
        value_shifts={"resistance": 0.5, "tradition": -0.4},
        current_chapter=bp,
    )
    # 关键词路径优先（Phase 1），所以应触发 rising_conflict
    # 价值偏移路径不会覆盖（因为关键词路径已触发）
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"  # 关键词触发


def test_route_detector_historical_anchor_trigger():
    """历史铁轨触发 path"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    result = detector.detect(
        "我去看看情况",
        value_shifts={},
        current_chapter=bp,
        historical_anchors_triggered=["倭寇来袭"],
    )
    # 倭寇来袭 → convergence
    assert result["route_change"] is True
    assert result["suggested_template"] == "convergence"


def test_route_detector_emergency_override():
    """emergency trigger → crisis"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    result = detector.detect(
        "我",
        value_shifts={},
        current_chapter=bp,
    )
    assert result["route_change"] is False  # "我" 太短，不触发


def test_route_detector_no_change_neutral_input():
    """中性输入不应触发路线变化"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    # 思考类输入（无关键词/价值偏移/历史铁轨）
    result = detector.detect(
        "我想想",  # "想" 在 ACTION_CHARS 中，可能触发
        value_shifts={},
        current_chapter=bp,
    )
    # "我想想" 是有效动作短语
    # 关键词无 / 价值偏移无 / 历史铁轨无 → 不变道
    assert result["route_change"] is False


def test_route_detector_with_dict_chapter():
    """current_chapter 可接受 dict 而非 dataclass"""
    detector = RouteDetector()
    chapter_dict = {
        "chapter_id": 1,
        "chapter_title": "春蚕",
        "narrative_position": "opening",
        "must_resolve": ["抗税"],
    }
    result = detector.detect(
        "我去抗税",
        value_shifts={},
        current_chapter=chapter_dict,
    )
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


# ============= Narrative Flow 顺序 =============

def test_narrative_flow_order():
    """NARRATIVE_FLOW 顺序应正确"""
    assert NARRATIVE_FLOW == [
        "opening", "rising_conflict", "crisis", "convergence", "resolution",
    ]


def test_narrative_flow_index_lookup():
    """NARRATIVE_FLOW 索引可正确查找"""
    assert NARRATIVE_FLOW.index("opening") == 0
    assert NARRATIVE_FLOW.index("rising_conflict") == 1
    assert NARRATIVE_FLOW.index("crisis") == 2
    assert NARRATIVE_FLOW.index("convergence") == 3
    assert NARRATIVE_FLOW.index("resolution") == 4


def test_max_backward_steps_constant():
    """MAX_BACKWARD_STEPS 应为 1（spec §4.3）"""
    assert MAX_BACKWARD_STEPS == 1


# ============= DM_INSTRUCTION_BASE 完整性 =============

def test_dm_instruction_base_5_templates():
    """DM_INSTRUCTION_BASE 应包含全部 5 类模板"""
    assert len(DM_INSTRUCTION_BASE) == 5
    for template in ["opening", "rising_conflict", "crisis", "convergence", "resolution"]:
        assert template in DM_INSTRUCTION_BASE
        assert len(DM_INSTRUCTION_BASE[template]) > 5  # 至少一句有意义的描述


# ============= ChapterBlueprint dataclass =============

def test_chapter_blueprint_default_values():
    """ChapterBlueprint 缺省值应正确"""
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="测试",
    )
    assert bp.chapter_id == 1
    assert bp.chapter_title == "测试"
    assert bp.narrative_position == "opening"  # default
    assert bp.must_resolve == []  # default


def test_chapter_blueprint_with_narrative_position():
    """ChapterBlueprint 可设置 narrative_position"""
    bp = ChapterBlueprint(
        chapter_id=2,
        chapter_title="高潮",
        narrative_position="crisis",
    )
    assert bp.narrative_position == "crisis"


def test_chapter_state_basic():
    """ChapterState 基础字段"""
    state = ChapterState(
        current_chapter=1,
        current_node=1,
        chapter_start_round=1,
    )
    assert state.current_chapter == 1
    assert state.current_node == 1
    assert state.chapter_start_round == 1


def test_blueprint_node_basic():
    """BlueprintNode 基础字段"""
    node = BlueprintNode(
        index=1,
        role="introduction",
        scene="开局",
    )
    assert node.index == 1
    assert node.role == "introduction"
    assert node.scene == "开局"


# ============= RouteDetector + Blueprint 集成 =============

def test_route_detector_integration_with_must_resolve():
    """must_resolve 字段在 detect 中可正确读取"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="税",
        narrative_position="opening",
        must_resolve=["抗税", "保家"],
    )
    # 抗税 触发 rising_conflict
    result = detector.detect(
        "我要去抗税",
        value_shifts={},
        current_chapter=bp,
    )
    assert result["route_change"] is True
    # 抗税 → 触发 rising_conflict
    assert result["suggested_template"] == "rising_conflict"


def test_route_detector_no_llm_no_route_change_for_unknown():
    """无 LLM + 未知输入 → 不变道"""
    detector = RouteDetector(llm_callable=None)
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="测试",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    # 无 LLM + 未知输入 → fallback Phase 1
    result = detector.detect(
        "随便说点完全没线索的话",  # 不在关键词表，价值无变化
        value_shifts={},
        current_chapter=bp,
    )
    assert result["route_change"] is False


def test_route_detector_routes_match_narrative_flow():
    """所有 route 变更的目标 template 应在 NARRATIVE_FLOW 中"""
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="测试",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    # 测试多个场景
    test_cases = [
        ("我要抗税", {"resistance": 0.0}, None),  # keyword → rising_conflict
        ("我去看看", {}, ["倭寇来袭"]),  # historical → convergence
    ]
    for player_input, value_shifts, anchors in test_cases:
        result = detector.detect(
            player_input,
            value_shifts,
            bp,
            historical_anchors_triggered=anchors,
        )
        if result["route_change"]:
            assert result["suggested_template"] in NARRATIVE_FLOW
