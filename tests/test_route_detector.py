"""v2.10.1 W85 · RouteDetector 单元测试（Phase 1 纯规则版）

依据 spec：docs/design/v2.10.1-W85-涌现式章节设计.md §2.7
6 个用例：
1. 关键词 rising_conflict
2. 关键词 crisis
3. 历史铁轨强制 convergence
4. 价值偏移阈值
5. 日常行为无变化
6. 价值偏移低于阈值
"""
import pytest

from history_footnote.chapter.route_detector import (
    RouteDetector,
    VALUE_SHIFT_THRESHOLD,
)
from history_footnote.chapter.types import ChapterBlueprint


def _make_bp(position: str = "opening", chapter_id: int = 1, title: str = "且听下回分解") -> ChapterBlueprint:
    """构造测试用 ChapterBlueprint"""
    return ChapterBlueprint(chapter_id=chapter_id, chapter_title=title, narrative_position=position)


# ============= 测试 1：关键词 rising_conflict =============

def test_keyword_rising_conflict():
    """关键词"抗税"应触发 rising_conflict 路线"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect("我要抗税", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"
    assert "抗税" in result["trigger"]
    assert result["confidence"] == 0.85
    assert "[rising_conflict]" in result["dm_instruction"]


# ============= 测试 2：关键词 crisis =============

def test_keyword_crisis():
    """关键词"倭寇"应触发 crisis 路线"""
    detector = RouteDetector()
    bp = _make_bp("rising_conflict", chapter_id=2)
    result = detector.detect("倭寇来了！", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "crisis"
    assert "倭寇" in result["trigger"]


# ============= 测试 3：历史铁轨强制 convergence =============

def test_historical_anchor_force_convergence():
    """历史铁轨触发应强制 convergence（即使当前是 crisis）"""
    detector = RouteDetector()
    bp = _make_bp("crisis", chapter_id=3)
    result = detector.detect("我去苏州", {}, bp, historical_anchors_triggered=["hai_rui_death"])
    assert result["route_change"] is True
    assert result["suggested_template"] == "convergence"
    assert result["confidence"] == 1.0
    assert "hai_rui_death" in result["trigger"]
    assert "必须在此刻汇合" in result["dm_instruction"]


# ============= 测试 4：价值偏移超过阈值 =============

def test_value_shift_threshold():
    """信任值跌至 -0.8 应触发 rising_conflict"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect("我去看看", {"trust": -0.8}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"
    assert result["trigger"].startswith("value_shift:trust=")
    assert result["confidence"] == 0.7


# ============= 测试 5：日常行为无变化 =============

def test_no_change_for_daily_actions():
    """日常行为 + 小幅价值变化 → 不应触发路线变更"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect("我去茶馆坐坐", {"trust": 0.1}, bp)
    assert result["route_change"] is False
    assert result["suggested_template"] == "opening"  # 保持当前
    assert result["trigger"] is None
    assert result["confidence"] == 0.0


# ============= 测试 6：价值偏移低于阈值 =============

def test_value_shift_below_threshold():
    """价值偏移 0.3（小于阈值 0.7）不应触发"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect("我去看看", {"trust": 0.3}, bp)
    assert result["route_change"] is False


# ============= 额外稳健性测试（Phase 1 边界）=============

def test_empty_player_input_no_change():
    """空输入不触发"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect("", {"trust": -0.8}, bp)
    # 关键词不匹配,但价值偏移会触发
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


def test_dict_current_chapter_compatible():
    """current_chapter 传 dict 也应能工作（向后兼容 blueprint dict 形式）"""
    detector = RouteDetector()
    bp_dict = {
        "chapter_id": 1,
        "chapter_title": "测试",
        "narrative_position": "opening",
    }
    result = detector.detect("我要抗税", {}, bp_dict)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


def test_threshold_constant_exposed():
    """VALUE_SHIFT_THRESHOLD 应为 0.7"""
    assert VALUE_SHIFT_THRESHOLD == 0.7


def test_custom_keywords_overrides_default():
    """自定义关键词表应覆盖默认"""
    custom = {"rising_conflict": ["逃跑"]}
    detector = RouteDetector(route_keywords=custom)
    bp = _make_bp("opening")

    # 默认关键词应不再触发
    result = detector.detect("我要抗税", {}, bp)
    assert result["route_change"] is False

    # 自定义关键词触发
    result = detector.detect("我准备逃跑", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


def test_value_shift_positive_triggers():
    """正向大幅偏移也应触发（绝对值检测）"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect("我去看看", {"trust": 0.9}, bp)
    assert result["route_change"] is True
    assert result["trigger"].startswith("value_shift:trust=+0.90")


def test_historical_anchor_priority_over_keyword():
    """历史铁轨优先级应高于关键词"""
    detector = RouteDetector()
    bp = _make_bp("opening")
    result = detector.detect(
        "我要抗税",  # 关键词应触发 rising_conflict
        {},
        bp,
        historical_anchors_triggered=["hai_rui_death"],  # 但铁轨优先级更高
    )
    assert result["suggested_template"] == "convergence"
    assert result["confidence"] == 1.0