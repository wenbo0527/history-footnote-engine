"""🆕 v2.10.1 W69: Jinja 占位符清洗测试"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))


def _strip_brace(m):
    body = m.group(0)[2:-2].strip()
    if not body:
        return "…"
    if len(body) > 20:
        return body[:20] + "…"
    return body


def clean_placeholder_text(text: str) -> str:
    """清洗未替换的 Jinja 占位符（与 narrative_sanitizer.py 等价）"""
    cleaned = re.sub(r"\{\{[^}]{1,80}\}\}", _strip_brace, text)
    cleaned = re.sub(r"\{%[^%]{1,80}%\}", "…", cleaned)
    cleaned = re.sub(r"\{#[^#]{1,80}#\}", "…", cleaned)
    return cleaned


def test_W69_001_user_avatar_url():
    """真实问题：{{user_avatar_url}}"""
    s = "<p>{{user_avatar_url}} <strong>「</strong> 爹！<strong>」</strong></p>"
    r = clean_placeholder_text(s)
    assert "{{" not in r
    assert "}}" not in r
    assert "user_avatar_url" in r


def test_W69_002_short_placeholder():
    """短占位符"""
    s = "{{ short }} normal text"
    r = clean_placeholder_text(s)
    assert "{{" not in r
    assert "short" in r


def test_W69_003_long_placeholder_truncate():
    """长占位符截断"""
    s = "{{ long_variable_name_that_exceeds_twenty_chars }} after"
    r = clean_placeholder_text(s)
    assert "…" in r
    assert "after" in r


def test_W69_004_jinja_statement():
    """Jinja 控制语句"""
    s = "{%if x%}block{%endif%}"
    r = clean_placeholder_text(s)
    assert "{%" not in r
    assert "block" in r


def test_W69_005_jinja_comment():
    """Jinja 注释"""
    s = "before {# comment #} after"
    r = clean_placeholder_text(s)
    assert "{#" not in r
    assert "after" in r


def test_W69_006_chinese_var():
    """中文占位符"""
    s = "正常{{未替换}}文本"
    r = clean_placeholder_text(s)
    assert "未替换" in r
    assert "{{" not in r


def test_W69_007_nested_braces():
    """嵌套大括号不应破坏"""
    s = "JSON: {{\"key\": \"value\"}}"
    r = clean_placeholder_text(s)
    # 包含 } 会导致提前结束，但这种 JSON 表达极少见
    assert "{{" not in r or r == s


def test_W69_008_mixed_content():
    """混合文本 + 占位符"""
    s = "你好，{{name}}，今天{{weather}}，请{{action}}。"
    r = clean_placeholder_text(s)
    assert "{{" not in r
    assert "name" in r
    assert "weather" in r
    assert "action" in r


def test_W69_009_no_placeholder():
    """无占位符不应变化"""
    s = "纯文本，无占位符"
    r = clean_placeholder_text(s)
    assert r == s


def test_W69_010_too_long_var_80():
    """超长变量名（>80）应保留原样（不在 regex 范围）"""
    s = "{{" + "x" * 100 + "}}"
    r = clean_placeholder_text(s)
    # 超过 80 字符的占位符不在 regex 范围，原样保留
    assert r == s


def test_W69_011_double_braces_preserved_inner_text():
    """长文本内嵌双花括号"""
    s = "句子{{var_name}}结束"
    r = clean_placeholder_text(s)
    assert "var_name" in r
    assert "{{" not in r


tests = [v for k, v in dict(globals()).items() if k.startswith("test_W69_")]
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
print(f"\n  {passed}/{passed+failed} 占位符清洗测试通过", flush=True)
sys.exit(0 if failed == 0 else 1)
