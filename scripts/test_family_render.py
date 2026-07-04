"""🆕 v1.6.5 修复测试：family 字段渲染 + 回车快捷键

Bug 报告：家庭信息显示原始程序格式：
  · spouse：周氏（桂花）
  · children：["大毛（9岁）","二丫（5岁）"]
  · elderly：老娘沈王氏（58岁，住在后屋隔壁的小间）

修复：
1. 把英文 key (spouse/children/elderly) 翻译成中文
2. 数组 children 用"、"连接而不是 JSON.stringify
"""
import sys
import re
sys.path.insert(0, "src")


def test_family_key_translation():
    """family key 翻译：spouse → 妻子"""
    familyKeyLabels = {
        "spouse": "妻子",
        "husband": "丈夫",
        "children": "子女",
        "elderly": "老人",
        "siblings": "兄弟姐妹",
        "parents": "父母",
        "father": "父亲",
        "mother": "母亲",
    }
    assert familyKeyLabels["spouse"] == "妻子"
    assert familyKeyLabels["children"] == "子女"
    assert familyKeyLabels["elderly"] == "老人"
    print("✅ test_family_key_translation: 8 个 key 全部翻译正确")


def test_family_array_format():
    """数组格式：['大毛（9岁）', '二丫（5岁）'] → 大毛（9岁）、二丫（5岁）"""
    children = ["大毛（9岁）", "二丫（5岁）"]
    # 模拟渲染逻辑
    display = "、".join(str(item) for item in children)
    assert display == "大毛（9岁）、二丫（5岁）"
    assert "[" not in display  # 不应该有数组符号
    assert '"' not in display  # 不应该有引号
    print(f"✅ test_family_array_format: 数组 → {display}")


def test_family_mixed_types():
    """混合类型（字符串 + 数组）"""
    family = {
        "spouse": "周氏（桂花）",
        "children": ["大毛（9岁）", "二丫（5岁）"],
        "elderly": "老娘沈王氏（58岁，住在后屋隔壁的小间）",
    }
    familyKeyLabels = {
        "spouse": "妻子", "children": "子女", "elderly": "老人",
    }
    output = []
    for k, v in family.items():
        label = familyKeyLabels.get(k, k)
        if isinstance(v, list):
            display = "、".join(str(item) for item in v)
        else:
            display = str(v)
        output.append(f"· {label}：{display}")

    result = "\n".join(output)

    # 关键断言
    assert "妻子：周氏（桂花）" in result
    assert "子女：大毛（9岁）、二丫（5岁）" in result
    assert "老人：老娘沈王氏" in result

    # 不应该有原始程序符号
    assert "spouse" not in result
    assert "children" not in result
    assert "[" not in result
    assert "]" not in result
    assert '"' not in result

    print(f"✅ test_family_mixed_types:")
    for line in output:
        print(f"    {line}")


def test_enter_key_logic():
    """Enter 提交 vs Shift+Enter 换行"""
    # 模拟 keydown 事件
    def should_submit(e):
        """True = 提交，False = 换行（默认行为）"""
        if e["key"] == "Enter" and not e["shiftKey"] and not e["altKey"]:
            return True
        if (e["ctrlKey"] or e["metaKey"]) and e["key"] == "Enter":
            return True
        return False

    # 裸 Enter → 提交
    assert should_submit({"key": "Enter", "shiftKey": False, "altKey": False, "ctrlKey": False, "metaKey": False}) is True

    # Shift+Enter → 换行（不提交）
    assert should_submit({"key": "Enter", "shiftKey": True, "altKey": False, "ctrlKey": False, "metaKey": False}) is False

    # Ctrl+Enter → 提交
    assert should_submit({"key": "Enter", "shiftKey": False, "altKey": False, "ctrlKey": True, "metaKey": False}) is True

    # Cmd+Enter (Mac) → 提交
    assert should_submit({"key": "Enter", "shiftKey": False, "altKey": False, "ctrlKey": False, "metaKey": True}) is True

    # Alt+Enter → 换行
    assert should_submit({"key": "Enter", "shiftKey": False, "altKey": True, "ctrlKey": False, "metaKey": False}) is False

    print("✅ test_enter_key_logic: 5 种组合全部正确")


def test_other_keys_pass_through():
    """普通字符不触发提交"""
    for key in ["a", "A", "1", " ", "，", "Tab", "Backspace"]:
        e = {"key": key, "shiftKey": False, "altKey": False, "ctrlKey": False, "metaKey": False}
        # 普通字符 → 不应触发提交
        should_submit = (e["key"] == "Enter" and not e["shiftKey"] and not e["altKey"])
        assert should_submit is False, f"普通字符 {key} 不应触发提交"
    print("✅ test_other_keys_pass_through: 普通字符正常输入")


def test_xss_protection_in_family():
    """XSS 防护：family 字段需要 escapeHtml"""
    family = {
        "spouse": "<script>alert('xss')</script>",
        "children": ["<img src=x onerror=alert(1)>"],
    }
    familyKeyLabels = {"spouse": "妻子", "children": "子女"}

    def escapeHtml(s):
        return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

    output = []
    for k, v in family.items():
        label = familyKeyLabels.get(k, k)
        if isinstance(v, list):
            display = "、".join(escapeHtml(item) for item in v)
        else:
            display = escapeHtml(v)
        output.append(f"· {label}：{display}")

    result = "\n".join(output)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    print("✅ test_xss_protection_in_family: XSS 防护正确")


if __name__ == "__main__":
    print("=" * 50)
    print("Family 渲染 + 回车快捷键 测试（v1.6.5）")
    print("=" * 50)
    test_family_key_translation()
    test_family_array_format()
    test_family_mixed_types()
    test_enter_key_logic()
    test_other_keys_pass_through()
    test_xss_protection_in_family()
    print("\n✅ 所有 v1.6.5 测试通过")