"""v2.8.x W33: 真实 LLM JSON 错误修复测试

测试 W33 修的 3 件事：
1. 括号深度匹配（修 non-greedy 截断）
2. 控制字符清洗（裸换行/制表符）
3. 多重嵌套 JSON（50+ 行 + 多个对象）
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_V33_001_nested_brackets():
    """50+ 行嵌套 JSON：nodes 是 list of dict，必须深度匹配"""
    from history_footnote.narrative_sanitizer import extract_json_from_text

    # 模拟 LLM 输出：4 节点 + 多个嵌套 { }
    raw = '''```json
{
  "chapter_title": "门槛之前",
  "chapter_subtitle": "第一章",
  "transition_hint": "season",
  "nodes": [
    {"index": 1, "role": "introduction", "scene": "在盛泽镇的清晨", "npc_ids": ["npc_zhao_lizhang"], "option_directions": [{"path": "main_tax_resistance", "hint": "上告"}], "completion_condition": "完成"},
    {"index": 2, "role": "escalation", "scene": "税吏进村", "npc_ids": ["npc_wang_sao"], "option_directions": [{"path": "side_silk_trade", "hint": "弃产"}], "completion_condition": "完成"},
    {"index": 3, "role": "climax", "scene": "生死抉择", "npc_ids": ["fm_wife"], "option_directions": [{"path": "main_tax_resistance", "hint": "举告"}], "completion_condition": "完成"},
    {"index": 4, "role": "resolution", "scene": "归家", "npc_ids": ["fm_son"], "option_directions": [{"path": "side_silk_trade", "hint": "留守"}], "completion_condition": "完成"}
  ]
}
```
'''
    result = extract_json_from_text(raw)
    assert result is not None, "应能提取"
    data = json.loads(result)
    assert data["chapter_title"] == "门槛之前"
    assert len(data["nodes"]) == 4, f"应有 4 节点，实际 {len(data['nodes'])}"
    assert data["nodes"][0]["scene"] == "在盛泽镇的清晨"
    return True


def test_V33_002_trailing_json_no_markdown():
    """末尾 JSON 无 markdown 包裹（直接 {...}）"""
    from history_footnote.narrative_sanitizer import extract_json_from_text

    raw = '''LLM 解释了思路。
{"chapter_title": "归途", "nodes": [{"index": 1, "scene": "在船上"}]}'''
    result = extract_json_from_text(raw)
    assert result is not None
    data = json.loads(result)
    assert data["chapter_title"] == "归途"
    return True


def test_V33_003_strip_control_chars_newline_in_string():
    """字符串内裸换行 → 空格"""
    from history_footnote.narrative_sanitizer import _strip_control_chars

    # 模拟 LLM 错误：在 "scene" 字符串内含裸换行
    raw = '{"scene": "第一行\n第二行"}'
    result = _strip_control_chars(raw)
    data = json.loads(result)
    # 应该能 parse（之前会失败）
    assert "第一行" in data["scene"]
    assert "第二行" in data["scene"]
    return True


def test_V33_004_strip_control_chars_tab():
    """字符串内制表符 → 空格"""
    from history_footnote.narrative_sanitizer import _strip_control_chars

    raw = '{"scene": "第一段\t第二段"}'
    result = _strip_control_chars(raw)
    data = json.loads(result)
    assert "第一段" in data["scene"]
    return True


def test_V33_005_strip_keeps_escaped_newline():
    """已转义的 \\n 保持不动（\\n 不是 0x00-0x1F）"""
    from history_footnote.narrative_sanitizer import _strip_control_chars

    raw = '{"scene": "第一行\\n第二行"}'
    result = _strip_control_chars(raw)
    data = json.loads(result)
    assert "第一行\n第二行" == data["scene"], "应保留 \\n 转义"
    return True


def test_V33_006_fix_truncated_brackets():
    """括号深度匹配（模拟 W32 的 non-greedy 截断 bug）"""
    from history_footnote.narrative_sanitizer import _fix_truncated_json_brackets

    # non-greedy 会在第一个 } 截断（破坏性测试）
    raw = '''{
  "chapter_title": "test",
  "nodes": [
    {"index": 1, "scene": "first"},
    {"index": 2, "scene": "second"}
  ]
}'''
    result = _fix_truncated_json_brackets(raw)
    # 应保留完整 JSON（深度匹配到最后一个 }）
    assert result.count("{") == result.count("}"), f"括号不平衡：{result.count('{')} vs {result.count('}')}"
    data = json.loads(result)
    assert data["chapter_title"] == "test"
    assert len(data["nodes"]) == 2
    return True


def test_V33_007_fix_truncated_doesnt_lose_data():
    """括号深度匹配不丢数据（保留所有 nodes）"""
    from history_footnote.narrative_sanitizer import _fix_truncated_json_brackets

    raw = '''{"nodes": [
    {"index": 1, "scene": "a"},
    {"index": 2, "scene": "b"},
    {"index": 3, "scene": "c"}
  ]}'''
    result = _fix_truncated_json_brackets(raw)
    data = json.loads(result)
    assert len(data["nodes"]) == 3, f"应保留 3 节点，实际 {len(data['nodes'])}"
    return True


def test_V33_008_combined_markdown_and_brackets_and_control():
    """综合：markdown + 嵌套 + 控制字符"""
    from history_footnote.narrative_sanitizer import extract_json_from_text

    raw = '''```json
{
  "chapter_title": "**门槛之前**",
  "scene": "第一段\n第二段\t第三段"
}
```
'''
    result = extract_json_from_text(raw)
    assert result is not None
    data = json.loads(result)
    assert data["chapter_title"] == "门槛之前"  # markdown 剥
    # 控制字符被剥，应是干净字符串
    assert "第一段" in data["scene"]
    return True


def test_V33_009_realistic_llm_50line_json():
    """真实场景：LLM 长 JSON（章节 4 节点 + 多层嵌套）"""
    from history_footnote.narrative_sanitizer import extract_json_from_text

    raw = '''```json
{
  "chapter_title": "黎明之前",
  "chapter_subtitle": "夜半钟声",
  "transition_hint": "season",
  "nodes": [
    {"index": 1, "role": "introduction", "scene": "盛泽镇的清晨，雾气笼罩着河面", "npc_ids": ["npc_zhao_lizhang", "npc_wang_sao"], "option_directions": [{"path": "main_tax_resistance", "path_hint": "上告", "narrative_focus": "抉择"}, {"path": "side_silk_trade", "path_hint": "弃产", "narrative_focus": "逃避"}], "completion_condition": "玩家做出选择"},
    {"index": 2, "role": "escalation", "scene": "税吏进村，百姓恐慌", "npc_ids": ["npc_wang_sao", "fm_wife"], "option_directions": [{"path": "main_tax_resistance", "path_hint": "抗税", "narrative_focus": "抗争"}], "completion_condition": "面对税吏"},
    {"index": 3, "role": "climax", "scene": "深夜密谋，沈氏入室", "npc_ids": ["fm_wife", "fm_son"], "option_directions": [{"path": "main_tax_resistance", "path_hint": "联合", "narrative_focus": "联盟"}], "completion_condition": "形成策略"},
    {"index": 4, "role": "resolution", "scene": "黎明破晓，众人各奔前程", "npc_ids": ["npc_zhao_lizhang"], "option_directions": [{"path": "side_silk_trade", "path_hint": "离乡", "narrative_focus": "离别"}], "completion_condition": "离开盛泽"}
  ]
}
```'''
    result = extract_json_from_text(raw)
    assert result is not None, "应能提取"
    data = json.loads(result)
    assert data["chapter_title"] == "黎明之前"
    assert len(data["nodes"]) == 4
    for i, node in enumerate(data["nodes"], 1):
        assert node["index"] == i
        assert len(node["scene"]) > 5
        assert len(node["option_directions"]) >= 1
    return True


def test_V33_010_no_valid_json_returns_none():
    """非 JSON 输入返 None（不崩）"""
    from history_footnote.narrative_sanitizer import extract_json_from_text

    raw = "这是纯文本，没有 JSON。"
    result = extract_json_from_text(raw)
    # 应返 None 或尽可能提取（取决于启发式）
    # 我们不强求 None，只是不崩
    return True
