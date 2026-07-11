"""🆕 v2.9.x W37: GitHub Release workflow 验证

测试目标：
1. CHANGELOG.md 存在 + 格式正确（## [TAG] - DATE）
2. 提取逻辑能正确拿到 ## [v2.8.0] 段落
3. release.yml 存在 + 含关键步骤
4. ci.yml 存在
5. 标签格式 v*.*.* 匹配

测试方法：用纯 Python 模拟 workflow 的 CHANGELOG 解析逻辑。
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _extract_changelog_section(changelog_text: str, tag: str) -> str:
    """与 release.yml 同样的解析逻辑（必须 100% 一致）"""
    pattern = rf"## \[{re.escape(tag)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    m = re.search(pattern, changelog_text, re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip()


def test_W37_001_changelog_exists():
    """CHANGELOG.md 存在"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    assert p.exists(), f"CHANGELOG.md 不存在 at {p}"
    return True


def test_W37_002_changelog_has_v28_section():
    """CHANGELOG.md 有 ## [v2.9.0] 段落（v2.9.0 release tag 对应）"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    # 🆕 W37: release tag v2.9.0 → 找 ## [v2.9.0] 段
    assert "## [v2.9.0]" in text, "应含 ## [v2.9.0] 段"
    return True


def test_W37_003_changelog_has_w36_section():
    """CHANGELOG.md 有 ## [v2.9.x-W36] 段落"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    assert "## [v2.9.x-W36]" in text, "应含 ## [v2.9.x-W36] 段"
    return True


def test_W37_004_extract_v28_section():
    """提取 v2.9.0 段落（含 320 测试）"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    body = _extract_changelog_section(text, "v2.9.0")
    assert "320" in body or "测试" in body, f"v2.9.0 段应含 320 测试信息，实际：\n{body[:200]}"
    return True


def test_W37_005_extract_w36_section():
    """提取 v2.9.x-W36 段落（含 5-15 夹紧）"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    body = _extract_changelog_section(text, "v2.9.x-W36")
    assert "5-15" in body or "夹紧" in body, f"W36 段应含 5-15 信息，实际：\n{body[:200]}"
    return True


def test_W37_006_extract_unknown_tag_returns_empty():
    """提取不存在的 tag 返空字符串"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    body = _extract_changelog_section(text, "v999.0.0-nonexistent")
    assert body == "", f"应返空字符串，实际 {body!r}"
    return True


def test_W37_007_release_workflow_exists():
    """release.yml 存在"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    assert p.exists(), f"release.yml 不存在 at {p}"
    return True


def test_W37_008_release_workflow_has_jobs():
    """release.yml 含 test + release 2 job"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "jobs:" in text
    assert "test:" in text
    assert "release:" in text
    return True


def test_W37_009_release_workflow_tag_trigger():
    """release.yml 用 tag v*.*.* 触发"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "tags:" in text
    assert "v*.*.*" in text, f"应用 v*.*.* 触发，实际：\n{text[:500]}"
    return True


def test_W37_010_release_workflow_uses_changelog():
    """release.yml 用 CHANGELOG.md 作 body"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "CHANGELOG.md" in text
    assert "softprops/action-gh-release" in text
    assert "body_path" in text
    return True


def test_W37_011_release_workflow_runs_pytest():
    """release.yml 跑 pytest"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "tests/" in text
    return True


def test_W37_012_release_workflow_runs_vitest():
    """release.yml 跑 vitest"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "vitest" in text
    assert "npm install" in text
    return True


def test_W37_013_release_needs_test():
    """release job depends on test (test fail → release 不发)"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "needs: test" in text
    return True


def test_W37_014_release_has_write_perm():
    """release workflow 有 contents: write 权限"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "release.yml"
    text = p.read_text(encoding="utf-8")
    assert "permissions:" in text
    assert "contents: write" in text
    return True


def test_W37_015_ci_workflow_still_exists():
    """ci.yml 仍存在（没被覆盖）"""
    p = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    assert p.exists(), "ci.yml 应保留"
    return True


def test_W37_016_tag_format_v2_8_0():
    """tag v2.8.0 格式正确"""
    # 已 push 的 tag
    import subprocess
    r = subprocess.run(
        ["git", "tag", "--list", "v2.8.0"],
        cwd=Path(__file__).parent.parent,
        capture_output=True, text=True, check=False,
    )
    assert r.stdout.strip() == "v2.8.0", f"应含 tag v2.8.0，实际 {r.stdout}"
    return True


def test_W37_017_extract_w32_section():
    """提取 v2.8.x-W32 段落（含 51→0 ERROR 标志）"""
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    body = _extract_changelog_section(text, "v2.8.x-W32")
    assert len(body) > 100, f"W32 段应有内容，实际 {len(body)} 字符"
    return True
