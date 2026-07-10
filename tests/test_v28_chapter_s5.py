"""v2.8.0 段二 W5 单元测试

测试目标：
1. ChapterMeta dataclass 序列化 + validate
2. ActType 枚举容错
3. ChapterMetaResolver 默认 5 个 act 解析正确
4. ChapterBlueprint 含 meta 字段的序列化往返
5. ChapterFacade.resolve_chapter_meta + get_or_resolve_meta
6. Closure 优先读 ChapterMeta.suggested_node_count

约束：
- 不依赖 LLM
- 不影响现有 79 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.types import (
    ChapterMeta,
    ChapterBlueprint,
    ActType,
    NodeRole,
)
from history_footnote.chapter.meta_resolver import (
    ChapterMetaResolver,
    DEFAULT_HERO_JOURNEY_ACTS,
)


# ============= 测试 1：ChapterMeta 序列化 + validate =============

def test_V28_42_chapter_meta_default():
    """ChapterMeta 默认值"""
    meta = ChapterMeta(chapter_id=1)
    assert meta.chapter_id == 1
    assert meta.act == "departure"
    assert meta.role == "ordinary"
    assert meta.emotion_tone == "neutral"
    assert meta.choice_type == "open_ended"
    assert meta.suggested_node_count == 4
    return True


def test_V28_43_chapter_meta_serialization_roundtrip():
    """ChapterMeta 序列化往返一致"""
    meta = ChapterMeta(
        chapter_id=5,
        act="initiation",
        role="trial",
        emotion_tone="tension→awakening",
        choice_type="how_to_face_challenge",
        suggested_node_count=5,
        suggested_template="discovery_investigation_confrontation_reveal",
    )
    data = meta.to_dict()
    meta2 = ChapterMeta.from_dict(data)
    assert meta2.chapter_id == 5
    assert meta2.act == "initiation"
    assert meta2.role == "trial"
    assert meta2.emotion_tone == "tension→awakening"
    assert meta2.suggested_node_count == 5
    return True


def test_V28_44_chapter_meta_validate():
    """ChapterMeta.validate 校验"""
    # 正常
    meta = ChapterMeta(chapter_id=1, act="departure", emotion_tone="unease→resolve")
    assert meta.validate() == []

    # act 非法
    meta_bad_act = ChapterMeta(chapter_id=1, act="invalid_act", emotion_tone="a→b")
    errors = meta_bad_act.validate()
    assert any("act 非法" in e for e in errors)

    # emotion_tone 缺箭头
    meta_bad_emotion = ChapterMeta(chapter_id=1, act="departure", emotion_tone="no_arrow")
    errors = meta_bad_emotion.validate()
    assert any("emotion_tone" in e for e in errors)

    # 节点数越界
    meta_bad_count = ChapterMeta(chapter_id=1, act="departure", suggested_node_count=100)
    errors = meta_bad_count.validate()
    assert any("suggested_node_count" in e for e in errors)
    return True


# ============= 测试 2：ActType 枚举容错 =============

def test_V28_45_act_type_from_string():
    """ActType.from_string 容错"""
    assert ActType.from_string("departure") == ActType.DEPARTURE
    assert ActType.from_string("initiation") == ActType.INITIATION
    assert ActType.from_string("return") == ActType.RETURN
    assert ActType.from_string("invalid") == ActType.DEPARTURE  # 回退
    return True


# ============= 测试 3：ChapterMetaResolver =============

def test_V28_46_resolver_default_acts():
    """ChapterMetaResolver 缺省配置时用兜底 3 幕"""
    resolver = ChapterMetaResolver(era_config={})
    summary = resolver.get_acts_summary()
    assert len(summary) == 3, f"期望 3 幕，实际 {len(summary)}"
    assert summary[0]["act"] == "departure"
    assert summary[1]["act"] == "initiation"
    assert summary[2]["act"] == "return"
    return True


def test_V28_47_resolver_resolve_chapter_1():
    """resolver.resolve(1) → departure/ordinary"""
    resolver = ChapterMetaResolver(era_config={})
    meta = resolver.resolve(chapter_id=1)
    assert meta.act == "departure"
    assert meta.role == "ordinary"
    assert meta.emotion_tone == "unease→resolve"
    return True


def test_V28_48_resolver_resolve_chapter_5():
    """resolver.resolve(5) → initiation/allies（chapters[4,5,6,7] 中第 2 个）"""
    resolver = ChapterMetaResolver(era_config={})
    meta = resolver.resolve(chapter_id=5)
    assert meta.act == "initiation"
    assert meta.role == "allies"  # chapters[1] = 5 → roles[1] = "allies"
    assert meta.emotion_tone == "tension→awakening"
    return True


def test_V28_49_resolver_resolve_chapter_8():
    """resolver.resolve(8) → return/return_path"""
    resolver = ChapterMetaResolver(era_config={})
    meta = resolver.resolve(chapter_id=8)
    assert meta.act == "return"
    assert meta.role == "return_path"
    assert meta.emotion_tone == "clarity→transcendence"
    return True


def test_V28_50_resolver_resolve_out_of_range():
    """resolver.resolve(99) → 兜底元属性"""
    resolver = ChapterMetaResolver(era_config={})
    meta = resolver.resolve(chapter_id=99)
    assert meta.chapter_id == 99
    assert meta.act == "departure"  # 兜底
    assert meta.role == "ordinary"
    return True


# ============= 测试 4：ChapterBlueprint 含 meta 序列化 =============

def test_V28_51_blueprint_with_meta_serialization():
    """ChapterBlueprint 含 meta 字段序列化往返"""
    from history_footnote.chapter.types import BlueprintNode
    meta = ChapterMeta(chapter_id=1, act="departure", role="ordinary", emotion_tone="unease→resolve")
    blueprint = ChapterBlueprint(
        chapter_id=1,
        chapter_title="且听下回分解 · 春蚕",
        chapter_subtitle="春风又绿江南岸",
        meta=meta,
        nodes=[
            BlueprintNode(index=1, role="introduction", scene="盛泽春市开张"),
        ],
        transition_hint="season",
    )
    data = blueprint.to_dict()
    assert "meta" in data
    assert data["meta"]["act"] == "departure"

    # 反序列化
    bp2 = ChapterBlueprint.from_dict(data)
    assert bp2.meta is not None
    assert bp2.meta.act == "departure"
    assert bp2.meta.emotion_tone == "unease→resolve"
    assert len(bp2.nodes) == 1
    return True


def test_V28_52_blueprint_load_with_meta():
    """ChapterBlueprint 从 chapter1_blueprint.json 加载含 meta"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
    )
    blueprint = facade.load_blueprint(1)
    assert blueprint.meta is not None, "chapter1_blueprint.json 应含 meta 字段"
    assert blueprint.meta.act == "departure"
    assert blueprint.meta.role == "ordinary"
    assert blueprint.meta.suggested_node_count == 4
    return True


# ============= 测试 5：ChapterFacade resolve_chapter_meta =============

def test_V28_53_facade_resolve_chapter_meta():
    """ChapterFacade.resolve_chapter_meta 不依赖蓝图"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
    )
    meta = facade.resolve_chapter_meta(5)
    assert meta.act == "initiation"
    assert meta.role == "allies"  # chapters[1] = 5
    return True


def test_V28_54_facade_get_or_resolve_meta_with_blueprint():
    """ChapterFacade.get_or_resolve_meta 优先用 blueprint.meta"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    from history_footnote.chapter.types import ChapterMeta, ChapterBlueprint

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
    )

    # 用 blueprint.meta（custom）
    custom_meta = ChapterMeta(chapter_id=1, act="initiation", role="trial", emotion_tone="a→b")
    blueprint = ChapterBlueprint(chapter_id=1, meta=custom_meta)
    result = facade.get_or_resolve_meta(1, blueprint)
    assert result is custom_meta, "应优先返回 blueprint.meta"

    # 无 blueprint → 用 resolver
    result2 = facade.get_or_resolve_meta(1)
    assert result2.act == "departure", f"应回退到 resolver，实际 {result2.act}"
    return True


# ============= 测试 6：Closure 优先读 meta.suggested_node_count =============

def test_V28_55_closure_uses_meta_node_count():
    """Closure 优先用 ChapterMeta.suggested_node_count 判定末节点"""
    from history_footnote.game_state import GameState
    from history_footnote.chapter.closure import ChapterClosure

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 3  # 第 3 节点
    state.chapter_state.chapter_start_round = 1
    state.round_number = 10
    # 注入 blueprint.meta.suggested_node_count=3
    state.chapter_state.blueprint = {
        "meta": {"suggested_node_count": 3, "act": "departure"},
        "nodes": [{"index": 1}, {"index": 2}, {"index": 3}],
    }

    closure = ChapterClosure(state, drama_manager=None)
    # node=3, suggested=3 → 在末节点
    assert closure._is_at_last_node() is True
    return True


def test_V28_56_closure_falls_back_to_default_node_count():
    """Closure blueprint 无 meta 时用默认 4"""
    from history_footnote.game_state import GameState
    from history_footnote.chapter.closure import ChapterClosure, DEFAULT_NODES_PER_CHAPTER

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 3
    state.chapter_state.blueprint = None  # 无 meta

    closure = ChapterClosure(state, drama_manager=None)
    # node=3 < 4 → 不是末节点
    assert closure._is_at_last_node() is False
    return True
