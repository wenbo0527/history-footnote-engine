"""🆕 v2.10.x W62: API 网关测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W62_001_rate_allowed():
    from history_footnote.api_gateway import rate_limit_check
    assert rate_limit_check("u1", limit=5)["allowed"]


def test_W62_002_rate_exceeded():
    from history_footnote.api_gateway import rate_limit_check, rate_limit_reset
    rate_limit_reset("u2")
    for _ in range(3):
        rate_limit_check("u2", limit=3)
    assert not rate_limit_check("u2", limit=3)["allowed"]


def test_W62_003_api_key():
    from history_footnote.api_gateway import api_key_validate
    assert api_key_validate("demo_key") is not None
    assert api_key_validate("invalid") is None


def test_W62_004_register():
    from history_footnote.api_gateway import api_key_register, api_key_validate
    k = api_key_register("test", "pro")
    assert api_key_validate(k) is not None


def test_W62_005_openapi():
    from history_footnote.api_gateway import openapi_spec
    spec = openapi_spec()
    assert spec["openapi"] == "3.0.0"
    assert "/api/input" in spec["paths"]
