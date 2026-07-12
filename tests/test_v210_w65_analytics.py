"""🆕 v2.10.x W65: 数据看板测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W65_001_track():
    from history_footnote.analytics import analytics_track_event, analytics_summary, analytics_clear
    analytics_clear()
    analytics_track_event("session_created", {"era_id": "wanli1587"})
    analytics_track_event("chapter_completed", {"era_id": "wanli1587", "chapter": 1})
    s = analytics_summary()
    assert s["sessions_created"] == 1
    assert s["chapters_completed"] == 1
    assert s["completion_rate"] == 1.0


def test_W65_002_tokens():
    from history_footnote.analytics import analytics_track_event, analytics_summary, analytics_clear
    analytics_clear()
    analytics_track_event("llm_call", {"prompt_tokens": 100, "completion_tokens": 50})
    assert analytics_summary()["total_llm_tokens"] == 150


def test_W65_003_by_era():
    from history_footnote.analytics import analytics_track_event, analytics_by_era, analytics_clear
    analytics_clear()
    analytics_track_event("session_created", {"era_id": "wanli1587"})
    analytics_track_event("session_created", {"era_id": "hongwu1399"})
    by = analytics_by_era()
    assert by["wanli1587"]["sessions"] == 1
    assert by["hongwu1399"]["sessions"] == 1


def test_W65_004_recent():
    from history_footnote.analytics import analytics_track_event, analytics_recent_events, analytics_clear
    analytics_clear()
    for i in range(5):
        analytics_track_event(f"e-{i}")
    assert len(analytics_recent_events(limit=3)) == 3


def test_W65_005_empty():
    from history_footnote.analytics import analytics_summary, analytics_clear
    analytics_clear()
    s = analytics_summary()
    assert s["total_events"] == 0
