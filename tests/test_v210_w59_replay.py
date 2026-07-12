"""🆕 v2.10.x W59: 回放测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W59_001_record_replay():
    from history_footnote.replay import replay_record_chapter, replay_chapter
    replay_record_chapter("s1", 1, "narration", [{"choice": "a"}], "summary", 100.0, 200.0)
    r = replay_chapter("s1", 1)
    assert r["narrative"] == "narration"
    assert r["round_count"] == 1


def test_W59_002_meta():
    from history_footnote.replay import replay_record_chapter, replay_chapter_meta
    replay_record_chapter("s2", 1, "x", [], "s", 100.0, 150.0)
    m = replay_chapter_meta("s2", 1)
    assert m["duration_seconds"] == 50.0


def test_W59_003_list():
    from history_footnote.replay import replay_record_chapter, replay_list_chapters
    replay_record_chapter("s3", 1, "x", [], "s", 0, 1)
    replay_record_chapter("s3", 2, "y", [], "s", 0, 1)
    assert replay_list_chapters("s3") == [1, 2]


def test_W59_004_delete():
    from history_footnote.replay import replay_record_chapter, replay_delete_chapter, replay_chapter
    replay_record_chapter("s4", 1, "x", [], "s", 0, 1)
    assert replay_delete_chapter("s4", 1)
    assert replay_chapter("s4", 1) is None
