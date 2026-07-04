"""🆕 v1.6.8 Issue Reporter 单元测试"""
import sys
sys.path.insert(0, "src")

from history_footnote.issue_reporter import (
    VERSION,
    VERSION_NAME,
    IS_BETA,
    get_version_info,
    validate_feedback,
    save_feedback,
    list_recent_feedback,
    ISSUE_CATEGORIES,
)


def test_version_info():
    """版本信息正确"""
    info = get_version_info()
    assert info["version"] == VERSION
    assert info["is_beta"] == IS_BETA
    assert "git_commit" in info
    assert "git_branch" in info
    assert len(info["full_label"]) > 0
    print(f"✅ test_version_info: {info['full_label']}")


def test_version_format():
    """版本号格式：v1.6.8 - 内测版"""
    assert VERSION.startswith("1.")
    assert "内测" in VERSION_NAME
    assert IS_BETA is True
    print(f"✅ test_version_format: VERSION={VERSION}, NAME={VERSION_NAME}")


def test_categories_complete():
    """所有分类有 key + label + placeholder"""
    assert len(ISSUE_CATEGORIES) >= 5, "至少 5 个分类"
    for cat in ISSUE_CATEGORIES:
        assert "key" in cat
        assert "label" in cat
        assert "placeholder" in cat
        assert len(cat["placeholder"]) >= 5
    print(f"✅ test_categories_complete: {len(ISSUE_CATEGORIES)} 个分类完整")


def test_validate_valid():
    """有效反馈"""
    assert validate_feedback("bug", "valid description here") is None
    assert validate_feedback("feature", "建议加剧情回顾") is None
    print("✅ test_validate_valid: 2 个有效输入通过")


def test_validate_invalid_category():
    """无效分类"""
    err = validate_feedback("invalid", "x" * 10)
    assert err is not None
    assert "分类" in err
    print(f"✅ test_validate_invalid_category: {err}")


def test_validate_empty_description():
    """空描述"""
    err = validate_feedback("bug", "")
    assert err is not None
    assert "不能为空" in err
    print(f"✅ test_validate_empty_description: {err}")


def test_validate_too_short():
    """描述过短"""
    err = validate_feedback("bug", "abc")
    assert err is not None
    assert "过短" in err
    print(f"✅ test_validate_too_short: {err}")


def test_validate_too_long():
    """描述过长"""
    err = validate_feedback("bug", "x" * 6000)
    assert err is not None
    assert "过长" in err
    print(f"✅ test_validate_too_long: {err}")


def test_save_feedback():
    """保存反馈"""
    result = save_feedback(
        session_id="test-session-123",
        category="bug",
        description="测试反馈内容 - 玩家点提交后叙事出现 SKILL 元数据",
        context={"round": 5, "user_agent": "Test", "screen": "1920x1080"},
    )
    assert "id" in result
    assert result["id"].startswith("fb-")
    assert "saved_at" in result
    assert result.get("saved_to", "").endswith(".jsonl")
    print(f"✅ test_save_feedback: {result['id']} → {result.get('saved_to', 'ERROR')}")


def test_list_recent_feedback():
    """列出最近反馈"""
    recent = list_recent_feedback(limit=10)
    assert isinstance(recent, list)
    assert len(recent) >= 1, "至少 1 条（前一个测试保存的）"
    # 验证结构
    fb = recent[0]
    for key in ["id", "category", "description", "saved_at", "version"]:
        assert key in fb, f"feedback 缺少字段: {key}"
    print(f"✅ test_list_recent_feedback: {len(recent)} 条记录")


def test_xss_protection_in_feedback():
    """XSS 防护：description 不会被注入到 HTML（前端需 escape）"""
    # 服务端只存原始文本，XSS 防护由前端负责
    # 这里只验证不抛异常
    result = save_feedback(
        session_id="xss-test",
        category="bug",
        description='<script>alert("xss")</script>',
    )
    assert "id" in result
    # 前端读取时会通过 escapeHtml 防护
    print(f"✅ test_xss_protection_in_feedback: 提交成功（XSS 由前端 escape）")


if __name__ == "__main__":
    print("=" * 50)
    print(f"Issue Reporter 测试（v{VERSION}）")
    print("=" * 50)
    test_version_info()
    test_version_format()
    test_categories_complete()
    test_validate_valid()
    test_validate_invalid_category()
    test_validate_empty_description()
    test_validate_too_short()
    test_validate_too_long()
    test_save_feedback()
    test_list_recent_feedback()
    test_xss_protection_in_feedback()
    print(f"\n✅ 所有 v1.6.8 Issue Reporter 测试通过")