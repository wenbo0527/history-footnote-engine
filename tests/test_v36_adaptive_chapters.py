"""🆕 v2.9.x W36: 章节长度自适应（5-15）API 测试

测试目标：
1. era_config.narrative.chapter_count 显式指定优先级最高
2. 缺失时从 hero_journey_acts 推断
3. 兜底默认 10 章
4. 边界 5-15（防失控）
5. is_last_chapter / remaining_chapters 正确
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W36_001_explicit_chapter_count_5():
    """显式 chapter_count=5"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 5}})
    assert resolver.total_chapters == 5
    return True


def test_W36_002_explicit_chapter_count_12():
    """显式 chapter_count=12"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 12}})
    assert resolver.total_chapters == 12
    return True


def test_W36_003_explicit_chapter_count_15():
    """显式 chapter_count=15（上限）"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 15}})
    assert resolver.total_chapters == 15
    return True


def test_W36_004_explicit_too_low_clamped_to_5():
    """chapter_count=3 应被限制到下限 5"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 3}})
    assert resolver.total_chapters == 5
    return True


def test_W36_005_explicit_too_high_clamped_to_15():
    """chapter_count=20 应被限制到上限 15"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 20}})
    assert resolver.total_chapters == 15
    return True


def test_W36_006_infer_from_acts_default_10():
    """hero_journey_acts 推 10 章（默认 DEFAULT_HERO_JOURNEY_ACTS）"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({})  # 无 chapter_count
    # DEFAULT_HERO_JOURNEY_ACTS chapters = [1,2,3,4,5,6,7,8,9,10]
    assert resolver.total_chapters == 10
    return True


def test_W36_007_infer_from_acts_custom_7():
    """自定义 hero_journey_acts 推 7 章"""
    from history_footnote.chapter import ChapterMetaResolver
    custom_acts = [
        {"act": "a", "chapters": [1, 2, 3]},
        {"act": "b", "chapters": [4, 5, 6, 7]},
    ]
    resolver = ChapterMetaResolver({"narrative": {"hero_journey_acts": custom_acts}})
    assert resolver.total_chapters == 7
    return True


def test_W36_008_no_acts_no_count_defaults_10():
    """无 chapter_count 无 hero_journey_acts → 兜底 10"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({})
    assert resolver.total_chapters == 10
    return True


def test_W36_009_is_last_chapter_true():
    """is_last_chapter(chapter_id == total) 应 True"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 10}})
    assert resolver.is_last_chapter(10) is True
    return True


def test_W36_010_is_last_chapter_false():
    """is_last_chapter(chapter_id < total) 应 False"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 10}})
    assert resolver.is_last_chapter(9) is False
    assert resolver.is_last_chapter(1) is False
    return True


def test_W36_011_remaining_chapters():
    """remaining_chapters 正确"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 10}})
    assert resolver.remaining_chapters(1) == 9
    assert resolver.remaining_chapters(5) == 5
    assert resolver.remaining_chapters(10) == 0
    assert resolver.remaining_chapters(15) == 0  # over → 0
    return True


def test_W36_012_chapter_count_with_invalid_value_falls_back():
    """chapter_count 非法值（str/float/None）走兜底"""
    from history_footnote.chapter import ChapterMetaResolver
    for invalid in [None, "10", 3.5, "abc"]:
        resolver = ChapterMetaResolver({"narrative": {"chapter_count": invalid}})
        # 非 int 走推断 → DEFAULT_HERO_JOURNEY_ACTS = 10 章
        assert resolver.total_chapters == 10, f"invalid={invalid} 应走兜底 10"
    return True


def test_W36_013_chapter_count_0_clamped_to_5():
    """chapter_count=0 → 夹紧到 5（min 边界）"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 0}})
    assert resolver.total_chapters == 5
    return True


def test_W36_014_chapter_count_minus_clamped_to_5():
    """chapter_count=-1 → 夹紧到 5"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": -1}})
    assert resolver.total_chapters == 5
    return True


def test_W36_015_chapter_count_16_clamped_to_15():
    """chapter_count=16 → 夹紧到 15（max 边界）"""
    from history_footnote.chapter import ChapterMetaResolver
    resolver = ChapterMetaResolver({"narrative": {"chapter_count": 16}})
    assert resolver.total_chapters == 15
    return True
