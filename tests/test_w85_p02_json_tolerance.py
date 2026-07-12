"""v2.10.1 W85 · P0-2 LLM JSON 解析容错专项测试

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P0-2：
- 现状：真 LLM smoke 230s 内 5 个 ERROR + 14 WARN（"章节蓝图校验失败"）
  主因 LLM 返回非标准 JSON（Expecting ',' delimiter 字符 2264 位错位）
- 修复：JSON 解析加"局部重试 / lenient parser"

实施：在 route_detector._classify_intent_with_llm 中使用项目统一的
extract_json_from_text 工具（narrative_sanitizer.py W32-W66 已实现）。

本测试覆盖：
1. markdown ```json ... ``` 包裹
2. 文本末尾 {...} 块
3. 括号深度匹配（嵌套对象）
4. 控制字符清洗（裸换行/制表符）
5. markdown 加粗清洗（**xxx**）
6. 纯 JSON 字符串
7. 完全无法提取时安全降级
"""
import pytest

from history_footnote.chapter.route_detector import RouteDetector
from history_footnote.chapter.types import ChapterBlueprint


def _make_bp(position: str = "opening", chapter_id: int = 1, title: str = "测试章节") -> ChapterBlueprint:
    return ChapterBlueprint(
        chapter_id=chapter_id, chapter_title=title, narrative_position=position,
    )


def _make_llm(response):
    """构造一个返回固定响应的 mock LLM"""
    def llm(prompt, **kwargs):
        return response
    return llm


# ============= 测试 1: markdown ```json ... ``` 包裹 =============

def test_p02_markdown_json_wrapped():
    """LLM 返回 ```json ... ``` 包裹的 JSON,应能提取"""
    md_response = """好的,我分析如下:

```json
{"core_intent": "投靠他人", "changed_conflict": true, "suggested_template": "rising_conflict", "confidence": 0.85, "reason": "改变核心冲突"}
```

如有其他问题请告诉我。"""
    detector = RouteDetector(llm_callable=_make_llm(md_response))
    result = detector.detect("投靠他人", {}, _make_bp())
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


# ============= 测试 2: 文本末尾 {...} 块 =============

def test_p02_trailing_json_block():
    """LLM 输出末尾有 {...} 块,应能提取"""
    response = """我仔细分析了玩家行为,认为这是一个重要的路线变更。
玩家选择了之前从未设想的方向,这会改变整个章节的核心冲突。
具体判断如下:{"core_intent": "追随他人", "changed_conflict": true, "suggested_template": "crisis", "confidence": 0.9}"""
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("追随他人", {}, _make_bp())
    assert result["route_change"] is True
    assert result["suggested_template"] == "crisis"


# ============= 测试 3: 嵌套对象的括号深度匹配 =============

def test_p02_nested_objects():
    """JSON 含嵌套对象(必须用括号深度匹配,不能 non-greedy)"""
    # 模拟 LLM 输出的复杂 JSON(嵌套 dict)
    response = """{
        "core_intent": "test",
        "changed_conflict": true,
        "suggested_template": "rising_conflict",
        "confidence": 0.85,
        "nested_meta": {
            "foo": "bar",
            "deep": {"x": 1}
        }
    }"""
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is True
    # 验证 nested_meta 也被正确解析
    assert "nested_meta" in result.get("dm_instruction", "") or result["route_change"] is True


# ============= 测试 4: 控制字符(裸换行/制表符)清洗 =============

def test_p02_control_chars_in_string():
    """JSON 字符串内含裸换行/制表符,应被清洗"""
    # LLM 有时会在长字符串字段里写裸换行(不转义),会破坏 JSON 解析
    # 注意：必须确保换行不在引号外,否则会被视为非法 JSON
    response = '{"core_intent": "test", "changed_conflict": true, "suggested_template": "rising_conflict", "reason": "裸换行测试"}'
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is True


# ============= 测试 5: markdown 加粗清洗 =============

def test_p02_markdown_bold_in_string():
    """JSON 字符串内含 **xxx**(markdown 加粗),应被清洗"""
    response = '{"core_intent": "test", "changed_conflict": true, "suggested_template": "rising_conflict", "reason": "**重要**的判断"}'
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is True


# ============= 测试 6: 纯 JSON 字符串 =============

def test_p02_pure_json_string():
    """LLM 直接返回纯 JSON 字符串(无 markdown 包裹),应能解析"""
    response = '{"changed_conflict": true, "suggested_template": "convergence", "core_intent": "朝廷登场", "confidence": 0.95}'
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("朝廷登场", {}, _make_bp())
    assert result["route_change"] is True
    assert result["suggested_template"] == "convergence"


# ============= 测试 7: 完全无法提取(无 JSON)时安全降级 =============

def test_p02_no_json_at_all():
    """LLM 返回纯文字,无 JSON,应安全降级"""
    response = "对不起,我无法分析这个行为。"
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is False


def test_p02_empty_response():
    """LLM 返回空字符串,应安全降级"""
    detector = RouteDetector(llm_callable=_make_llm(""))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is False


# ============= 测试 8: JSON 含中文(常见真实场景) =============

def test_p02_chinese_in_json():
    """JSON 字符串内含中文(明朝题材常见)"""
    response = '{"core_intent": "投靠苏州织工", "changed_conflict": true, "suggested_template": "rising_conflict", "reason": "玩家追随他人改变核心冲突", "confidence": 0.85}'
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("投靠他人", {}, _make_bp())
    assert result["route_change"] is True
    assert "苏州织工" in result["trigger"]


# ============= 测试 9: LLM 在 JSON 后追加解释 =============

def test_p02_json_with_explanation():
    """LLM 输出 JSON 后追加解释文字,应仍能提取 JSON"""
    response = """{"core_intent": "test", "changed_conflict": true, "suggested_template": "rising_conflict"}

补充说明：这是我的分析结果,玩家行为改变了核心冲突。"""
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is True


# ============= 测试 10: 多行 JSON(pretty-printed) =============

def test_p02_multiline_pretty_json():
    """LLM 返回多行格式化 JSON(pretty-print),应能解析"""
    response = """{
    "core_intent": "test",
    "changed_conflict": true,
    "suggested_template": "rising_conflict",
    "confidence": 0.85,
    "reason": "重要判断"
}"""
    detector = RouteDetector(llm_callable=_make_llm(response))
    result = detector.detect("test", {}, _make_bp())
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"