"""🆕 v2.10.x W61: era 验证器测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W61_001_valid():
    from history_footnote.era_validator import era_validate
    era = {
        "era_id": "wanli1587", "title": "万历", "year": 1587,
        "narrative": {"setting": "x", "tone": "y", "main_conflict": "z"},
        "characters": [{"id": "c1", "name": "A"}],
        "fate_cards": [{"id": "f1"}],
    }
    assert era_validate(era)["valid"]


def test_W61_002_missing():
    from history_footnote.era_validator import era_validate
    r = era_validate({"era_id": "x"})
    assert not r["valid"]


def test_W61_003_empty_chars():
    from history_footnote.era_validator import era_validate
    era = {
        "era_id": "x", "title": "t", "year": 1,
        "narrative": {"setting": "a", "tone": "b", "main_conflict": "c"},
        "characters": [],
        "fate_cards": [],
    }
    assert not era_validate(era)["valid"]


def test_W61_004_fields():
    from history_footnote.era_validator import era_required_fields
    f = era_required_fields()
    assert "era_id" in f
    assert "characters" in f


def test_W61_005_fix():
    from history_footnote.era_validator import era_fix
    fixed = era_fix({"era_id": "x"})
    assert "narrative" in fixed
