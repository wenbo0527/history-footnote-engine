"""🆕 v2.10.9 era.json Pydantic schema 校验单元测试"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_load_real_wanli_era():
    """真实 era.json (wanli1587) 应通过校验"""
    from history_footnote.wiki.era_schema import validate_era_file

    era_path = Path("eras/wanli1587/era.json")
    if not era_path.exists():
        pytest.skip("wanli1587 era.json not found (CI 环境)")

    cfg = validate_era_file(era_path)
    assert cfg.era_id == "wanli1587"
    assert cfg.era_name == "万历十五年"
    assert cfg.world.timeline.start.year == 1587
    assert cfg.world.timeline.end.year == 1601
    assert cfg.world.timeline.round_unit == "month"
    assert cfg.world.timeline.total_rounds == 50
    assert len(cfg.world.iron_laws) >= 5
    assert len(cfg.world.seasons) == 12


def test_missing_required_field():
    """缺 world 字段应抛 ValueError"""
    from history_footnote.wiki.era_schema import validate_era_config

    bad = {"era_id": "test", "era_name": "测试"}  # 缺 world
    with pytest.raises(ValueError, match="validation failed"):
        validate_era_config(bad)


def test_invalid_era_id_pattern():
    """era_id 含大写应抛 ValueError"""
    from history_footnote.wiki.era_schema import validate_era_config

    bad = {
        "era_id": "TestEra",
        "era_name": "测试",
        "world": {
            "timeline": {
                "start": {"year": 1587, "month": 1},
                "end": {"year": 1601, "month": 1},
                "round_unit": "month",
                "total_rounds": 50,
            }
        },
    }
    with pytest.raises(ValueError, match="validation failed"):
        validate_era_config(bad)


def test_invalid_round_unit():
    """round_unit 非法值应抛 ValueError"""
    from history_footnote.wiki.era_schema import validate_era_config

    bad = {
        "era_id": "test",
        "era_name": "测试",
        "world": {
            "timeline": {
                "start": {"year": 1587, "month": 1},
                "end": {"year": 1601, "month": 1},
                "round_unit": "hour",  # 非法
                "total_rounds": 50,
            }
        },
    }
    with pytest.raises(ValueError, match="round_unit must be one of"):
        validate_era_config(bad)


def test_invalid_month():
    """month=13 应抛 ValueError"""
    from history_footnote.wiki.era_schema import validate_era_config

    bad = {
        "era_id": "test",
        "era_name": "测试",
        "world": {
            "timeline": {
                "start": {"year": 1587, "month": 13},  # 非法
                "end": {"year": 1601, "month": 1},
                "round_unit": "month",
                "total_rounds": 50,
            }
        },
    }
    with pytest.raises(ValueError, match="validation failed"):
        validate_era_config(bad)


def test_lax_mode_accepts_extras():
    """lax 模式（strict=False）应接受 extra 字段"""
    from history_footnote.wiki.era_schema import validate_era_config

    good = {
        "era_id": "test_extra",
        "era_name": "测试",
        "version": "1.0.0",
        "mechanics": {"foo": "bar"},  # extra 字段
        "knowledge": {"baz": "qux"},  # extra 字段
        "world": {
            "timeline": {
                "start": {"year": 1587, "month": 1},
                "end": {"year": 1601, "month": 1},
                "round_unit": "month",
                "total_rounds": 50,
            }
        },
    }
    cfg = validate_era_config(good, strict=False)
    assert cfg.era_id == "test_extra"


def test_main_load_era_config_validates(tmp_path):
    """__main__.load_era_config 默认应校验 schema"""
    import importlib
    main_mod = importlib.import_module("history_footnote.__main__")

    # 在 tmp_path 创建 era 目录
    era_dir = tmp_path / "eras" / "test_era"
    era_dir.mkdir(parents=True)
    era_json = era_dir / "era.json"
    era_json.write_text(json.dumps({
        "era_id": "test_era",
        "era_name": "测试时代",
        "version": "1.0.0",
        "world": {
            "timeline": {
                "start": {"year": 100, "month": 1},
                "end": {"year": 200, "month": 12},
                "round_unit": "year",
                "total_rounds": 100,
            }
        },
    }))

    # chdir 到 tmp_path
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        cfg = main_mod.load_era_config("test_era")
        assert cfg["era_id"] == "test_era"
    finally:
        os.chdir(old_cwd)


def test_main_load_era_config_fails_on_invalid(tmp_path):
    """错填 era.json 应抛 ValueError"""
    import importlib
    main_mod = importlib.import_module("history_footnote.__main__")

    era_dir = tmp_path / "eras" / "bad_era"
    era_dir.mkdir(parents=True)
    era_json = era_dir / "era.json"
    era_json.write_text(json.dumps({
        "era_id": "bad_era",
        "era_name": "测试",
        # 缺 world
    }))

    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with pytest.raises(ValueError, match="era.json 校验失败"):
            main_mod.load_era_config("bad_era")
    finally:
        os.chdir(old_cwd)


def test_main_load_era_config_skip_validate(tmp_path):
    """validate=False 时应跳过校验"""
    import importlib
    main_mod = importlib.import_module("history_footnote.__main__")

    era_dir = tmp_path / "eras" / "no_validate"
    era_dir.mkdir(parents=True)
    era_json = era_dir / "era.json"
    era_json.write_text(json.dumps({
        "era_id": "no_validate",
        "era_name": "测试",
        # 缺 world，但 validate=False 应跳过
    }))

    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        cfg = main_mod.load_era_config("no_validate", validate=False)
        assert cfg["era_id"] == "no_validate"
    finally:
        os.chdir(old_cwd)