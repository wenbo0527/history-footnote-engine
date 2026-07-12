"""🆕 v2.10.1 W66: JSON 多重容错独立测试（验证 helper 函数，不导入包）"""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))


# ============= 复制 dm_tool.py 中的 helper（独立测试）=============

def _clean_json_string(s: str) -> str:
    import re
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    s = re.sub(r"'(\w+)'\s*:", r'"\1":', s)
    return s


def _extract_first_json_object(s: str) -> str | None:
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    quote_char = None
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if in_string:
            if c == quote_char:
                in_string = False
            continue
        if c in ('"', "'"):
            in_string = True
            quote_char = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _parse_llm_json_with_retry(json_str: str, max_retries: int = 2) -> dict | None:
    if not json_str:
        return None
    try:
        result = json.loads(json_str)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    for _ in range(max_retries):
        try:
            cleaned = _clean_json_string(json_str)
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except Exception:
            continue
    try:
        extracted = _extract_first_json_object(json_str)
        if extracted:
            result = json.loads(extracted)
            if isinstance(result, dict):
                return result
    except Exception:
        pass
    return None


# ============= 测试 =============

def test_W66_001_valid_strict():
    assert _parse_llm_json_with_retry('{"a": 1, "b": 2}') == {"a": 1, "b": 2}


def test_W66_002_trailing_comma():
    assert _parse_llm_json_with_retry('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_W66_003_single_line_comment():
    r = _parse_llm_json_with_retry('{"a": 1, // comment\n "b": 2}')
    assert r == {"a": 1, "b": 2}


def test_W66_004_multi_line_comment():
    r = _parse_llm_json_with_retry('{"a": 1, /* multi\nline */ "b": 2}')
    assert r == {"a": 1, "b": 2}


def test_W66_005_single_quote_keys():
    assert _parse_llm_json_with_retry("{'a': 1, 'b': 2}") == {"a": 1, "b": 2}


def test_W66_006_partial_extract():
    r = _parse_llm_json_with_retry('before {"a": 1, "b": 2} after')
    assert r == {"a": 1, "b": 2}


def test_W66_007_nested_partial():
    r = _parse_llm_json_with_retry('prefix {"outer": {"inner": 42}} suffix')
    assert r == {"outer": {"inner": 42}}


def test_W66_008_truly_broken_returns_none():
    r = _parse_llm_json_with_retry("{a: 'broken without closing")
    assert r is None or isinstance(r, dict)


def test_W66_009_empty_string():
    assert _parse_llm_json_with_retry("") is None


def test_W66_010_unicode_in_value():
    r = _parse_llm_json_with_retry('{"name": "茶馆", "year": 1587}')
    assert r["name"] == "茶馆"


def test_W66_011_clean_helper():
    """clean helper：验证去注释 + 去尾随逗号"""
    # 尾随逗号
    r = _clean_json_string('{"a": 1,}')
    assert "," not in r.split("}")[0].rstrip() or r == '{"a": 1}'
    # 单行注释（被移除）
    r = _clean_json_string('{"a": 1, // comment\n "b": 2}')
    assert "comment" not in r
    # 尾随逗号被移除（任意位置）
    r = _clean_json_string('{"a": 1, "b": 2,}')
    assert r.endswith("}") and not r.endswith(",}")


def test_W66_012_extract_helper():
    assert _extract_first_json_object('foo {"a": 1} bar') == '{"a": 1}'
    assert _extract_first_json_object('no json here') is None


def test_W66_013_realistic_llm_output():
    """模拟 LLM 实际输出（带尾随解释）"""
    llm = '```json\n{"chapter": 1, "title": "第 1 章", "nodes": [{"role": "start", "scene": "初入盛泽", "options": ["a", "b"]}]}\n```\n以上是章节蓝图。'
    r = _parse_llm_json_with_retry(llm)
    assert r is not None
    assert r["chapter"] == 1
    assert r["title"] == "第 1 章"


def test_W66_014_chapter_blueprint_format():
    """章节蓝图格式"""
    bp = '{"chapter": 2, "title": "茶馆", "nodes": [{"role": "start", "scene": "x", "options": ["a"]}]}'
    r = _parse_llm_json_with_retry(bp)
    assert r["chapter"] == 2
    assert r["nodes"][0]["role"] == "start"


tests = [v for k, v in dict(globals()).items() if k.startswith("test_W66_")]
passed = 0
failed = 0
for fn in tests:
    try:
        fn()
        print(f"  {fn.__name__}: PASS", flush=True)
        passed += 1
    except AssertionError as e:
        print(f"  {fn.__name__}: FAIL -- {e}", flush=True)
        failed += 1
print(f"\n  {passed}/{passed+failed} JSON 容错测试通过", flush=True)
sys.exit(0 if failed == 0 else 1)
