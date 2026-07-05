"""v1.7.7 测试：英文 schema 键清洗"""
import sys
sys.path.insert(0, "src")

import history_footnote  # noqa
from history_footnote.narrative_sanitizer import strip_skill_metadata


def test_en_keywords_stripped():
    """英文 family schema 键应被清洗"""
    text = """你出门时，妻子陈氏说：

spouse: 陈氏（27岁，嫁过来六年）
children: ['阿大（5岁，男孩，调皮）', '二丫头（2岁，还在吃奶）']
elderly: 老娘沈王氏（58岁，住在镇南头老屋，腿脚不好）

"路上小心。"她叮嘱道。
"""
    cleaned = strip_skill_metadata(text)
    # 这些英文键应该被洗掉
    assert "spouse:" not in cleaned, f"spouse: 未清洗: {cleaned}"
    assert "children:" not in cleaned, f"children: 未清洗: {cleaned}"
    assert "elderly:" not in cleaned, f"elderly: 未清洗: {cleaned}"
    # 真叙事应保留
    assert "陈氏" in cleaned
    assert "路" in cleaned or "小心" in cleaned
    print(f"✅ test_en_keywords_stripped: 3 个英文键全清洗")
    print(f"   clean: {cleaned[:100]}...")


def test_chinese_keywords_kept():
    """中文 schema 键应保留（如果有）"""
    text = """姓名：陈氏
年龄：27岁

你出门。
"""
    cleaned = strip_skill_metadata(text)
    # 中文键不在清洗范围
    assert "姓名" in cleaned, "中文键被误清洗"
    assert "陈氏" in cleaned
    print(f"✅ test_chinese_keywords_kept: 中文键保留")


def test_list_value():
    """列表值应正确清洗（schema 行整行删除）"""
    text = """背景信息：
children: ['阿大（5岁）', '二丫头（2岁）']
然后你走进院子。
"""
    cleaned = strip_skill_metadata(text)
    assert "children:" not in cleaned
    # 列表内容（schema 行）整行删除 - 因为这本身就是 LLM 幻觉输出
    assert "阿大" not in cleaned  # schema 行被整体清除
    # 真叙事（紧跟在后的句子）保留
    assert "院子" in cleaned
    print(f"✅ test_list_value: 列表 schema 行正确清除")


def test_normal_text_unaffected():
    """正常中文叙事不受影响"""
    text = """你站在牙行门口。

张顺说："三两三。"

你心里想：他出价低。
"""
    cleaned = strip_skill_metadata(text)
    assert "牙行" in cleaned
    assert "张顺" in cleaned
    assert "三两三" in cleaned
    print(f"✅ test_normal_text_unaffected: 正常叙事完整保留")


def test_only_en_keyword_lines():
    """纯英文 key 行（无后续内容）应被清洗"""
    text = """spouse: 陈氏
children: ['阿大', '二丫头']
elderly: 老娘
"""
    cleaned = strip_skill_metadata(text)
    # 全部英文键行应被清除
    for k in ["spouse:", "children:", "elderly:"]:
        assert k not in cleaned, f"{k} 未清洗"
    print(f"✅ test_only_en_keyword_lines: 纯英文 key 行清除")


if __name__ == "__main__":
    print("=" * 50)
    print("v1.7.7 英文 schema 键清洗测试")
    print("=" * 50)
    test_en_keywords_stripped()
    test_chinese_keywords_kept()
    test_list_value()
    test_normal_text_unaffected()
    test_only_en_keyword_lines()
    print("\n✅ 所有 v1.7.7 英文清洗测试通过")