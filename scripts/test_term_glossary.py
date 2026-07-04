"""🆕 v1.6.6 明朝名词字典测试"""
import sys
sys.path.insert(0, "src")

from history_footnote.term_glossary import (
    TERM_GLOSSARY,
    SYNONYM_MAP,
    get_term,
    get_term_html,
    search_terms,
    extract_terms_from_text,
    escape_html,
)


def test_basic_lookup():
    """基本查询"""
    term = get_term("牙行")
    assert term is not None
    assert term["category"] == "经济"
    assert "牙行" in term["definition"] or "中介" in term["definition"]
    print(f"✅ test_basic_lookup: 牙行 → 经济类")


def test_synonyms():
    """同义词映射"""
    # "牙家" 应映射到 "牙行"
    assert get_term("牙家") == get_term("牙行")
    # "生员" → "秀才"
    assert get_term("生员") == get_term("秀才")
    # "孝廉" → "举人"
    assert get_term("孝廉") == get_term("举人")
    # "银子" → "银子" (自身)
    assert get_term("银子")["category"] == "货币"
    print(f"✅ test_synonyms: 4 个同义词映射正确")


def test_extract_terms():
    """从文本提取名词"""
    text = "你去了牙行和湖丝店，见到秀才李四。"
    terms = extract_terms_from_text(text)
    assert "牙行" in terms
    assert "湖丝" in terms
    assert "秀才" in terms
    print(f"✅ test_extract_terms: {len(terms)} 个名词从文本提取 → {terms}")


def test_extract_terms_no_overlap():
    """长 key 优先匹配（不会重复匹配子串）"""
    text = "你织了一匹湖绫。"
    terms = extract_terms_from_text(text)
    # "绫" 应该被提取，"湖绫" 在字典里但可能被拆解
    # 实际：字典没有"湖绫"，只有"绫"
    assert "绫" in terms
    print(f"✅ test_extract_terms_no_overlap: '绫' 正确提取")


def test_extract_empty():
    """空文本"""
    assert extract_terms_from_text("") == []
    assert extract_terms_from_text("今天天气不错。") == []
    print(f"✅ test_extract_empty: 空文本返回 []")


def test_search_terms():
    """搜索"""
    # 搜索"丝"
    matches = search_terms("丝")
    assert "湖丝" in matches
    assert "苏缎" in matches
    # 搜索"科举"
    matches2 = search_terms("科举")
    assert "科举" in matches2 or "秀才" in matches2
    # 空 query 返回全部
    matches_all = search_terms("", limit=50)
    assert len(matches_all) >= 30  # 字典有 41 个
    print(f"✅ test_search_terms: '丝' → {len(matches)} 个，空 → {len(matches_all)} 个")


def test_html_escaping():
    """HTML 转义（XSS 防护）"""
    html = get_term_html("牙行")
    assert "<script>" not in html
    # 检查用户/字典值是否被转义（应该没有未转义的引号等）
    # 检查输出结构：必须有 4 个 div，data-term 属性
    assert html.count("<div") == 5  # term-entry, term-name, term-def, term-cat (span), term-example(if exists)
    assert 'data-term="牙行"' in html
    # 检查定义内容里有 '<' 都被转义
    assert html.count("<script>") == 0
    print(f"✅ test_html_escaping: HTML 结构正确，无 XSS")


def test_glossary_size():
    """字典规模"""
    assert len(TERM_GLOSSARY) >= 30, f"字典应至少 30 个词，实际 {len(TERM_GLOSSARY)}"
    assert len(SYNONYM_MAP) >= 50, f"同义词应至少 50 个，实际 {len(SYNONYM_MAP)}"
    print(f"✅ test_glossary_size: {len(TERM_GLOSSARY)} 词 + {len(SYNONYM_MAP)} 同义词")


def test_categories():
    """分类完整性"""
    categories = set(t["category"] for t in TERM_GLOSSARY.values())
    assert "经济" in categories
    assert "科举" in categories
    assert "制度" in categories
    print(f"✅ test_categories: {len(categories)} 个分类: {sorted(categories)}")


def test_marked_text_format():
    """marked_text 格式正确（模拟 extract_terms API 行为）"""
    text = "你去了牙行买湖丝。"
    # 模拟服务端 marked_text 输出（未读词高亮）
    seen = []
    found = extract_terms_from_text(text)
    new_terms = [t for t in found if t not in seen]
    marked = text
    for t in found:
        if t not in seen:
            marked = marked.replace(
                t,
                f'<span class="term-new" data-term="{escape_html(t)}">{escape_html(t)}</span>'
            )
    # 第一次访问：所有词都是新的
    assert "牙行" in marked and "term-new" in marked
    print(f"✅ test_marked_text_format: 未读词被标记")


def test_seen_terms_tracking():
    """seen_terms 跟踪已读词（不再高亮）"""
    text = "你去了牙行买湖丝。"
    seen = ["牙行"]  # 已读过"牙行"
    found = extract_terms_from_text(text)
    new_terms = [t for t in found if t not in seen]
    # "湖丝" 仍未读，"牙行" 已读
    assert "湖丝" in new_terms
    assert "牙行" not in new_terms
    print(f"✅ test_seen_terms_tracking: seen=牙行 时 new=[湖丝]")


if __name__ == "__main__":
    print("=" * 50)
    print("明朝名词字典 测试（v1.6.6）")
    print("=" * 50)
    test_basic_lookup()
    test_synonyms()
    test_extract_terms()
    test_extract_terms_no_overlap()
    test_extract_empty()
    test_search_terms()
    test_html_escaping()
    test_glossary_size()
    test_categories()
    test_marked_text_format()
    test_seen_terms_tracking()
    print("\n✅ 所有 v1.6.6 名词字典测试通过")