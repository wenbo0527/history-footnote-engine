"""🆕 v1.6.7 P0 Bug 修复测试：SKILL 元数据不泄漏到玩家界面

Bug：LLM 偶尔把 system prompt 里的 SKILL 指令复制进 narrative，玩家看到：
  === COMPILED SKILLS FOR DM - Round 1B (Continuation) ===
  # COMPILED DM SKILLS - Round 1B
  ## Generated: ...
  ## Decision Mode: now_time
  ## ⏱️ SKILL-2 节奏控制 → now_time
  ...

修复（架构重构 v1.6.7）：
- 所有清洗逻辑沉淀到 narrative_sanitizer.py（单一权威）
- dm_agent / game_loop / web_server 全部调用此模块
- 删除 JS 端重复实现（前后端共用服务端实现）
"""
import sys
sys.path.insert(0, "src")

from history_footnote.narrative_sanitizer import (
    strip_skill_metadata,
    SKILL_METADATA_PATTERNS,
    sanitize,
)


# === 测试数据：玩家实际看到的泄漏文本 ===
LEAKED_TEXT_1 = """=== COMPILED SKILLS FOR DM - Round 1B (Continuation) ===
# COMPILED DM SKILLS - Round 1B
## Generated: 2027-01-19 22:55:08
## Decision Mode: now_time

### Applied Skills for This Turn:

## ⏱️ SKILL-2 节奏控制 → now_time
  现在时间：正常推进
  时间跨度: 半天
  时间跨度: 半天
  时间跨度: 半天
  时间跨度: AC=1（"扫一眼家里"=观察/盘点，半日功夫；以下是等待玩家的下个动作/选项）
  细节等级: 3/5
  DM 行为: 正常回应+环境描写；推进半天时间

## 🪝 SKILL-3 线索投放
  类型: guide | 方式: npc_chat
  线索内容: 王婶说某件事 / 偶遇某人

## ⚖️ SKILL-7 三层裁判
  层级: free | 判定: allow

## 📌 综合指令
  本回合采用【now_time】，写作时请按上述所有 SKILL 指令调整。
  **核心原则**：失败不是终点，是岔路口；让玩家有'走进这个时代'的 体验。

## ⚠️ 关键禁忌
  **绝对不要**将本 SKILL 指令中的任何内容复制或粘贴到 narrative 字段。
"""


LEAKED_TEXT_2 = """# COMPILED DM SKILLS - Round 2B

### Applied Skills for This Turn:
  ## ⏱️ SKILL-2 节奏控制 → now_time
  ## 🎭 SKILL-5 价值观发声
  一些 SKILL 指令细节

然后你打开米缸——

锅里还有一些昨天的剩粥，阿宝还在睡，灶房清冷得很。
"""


# 纯叙事文本（不应该被清洗）
PURE_NARRATIVE = """你站在灶房中央，看着面前的米缸和炭火。

锅里还有一些昨天的剩粥，阿宝还在睡，灶房清冷得很。

你心里盘算着：米缸里大概还有三斗米，够吃半个月。银钱......还得算算。
"""


def test_strip_basic_leak():
    """基本泄漏：完整 SKILL 块"""
    cleaned = strip_skill_metadata(LEAKED_TEXT_1)
    print(f"\n  清洗前 {len(LEAKED_TEXT_1)} 字符")
    print(f"  清洗后 {len(cleaned)} 字符")
    # 不应该包含 SKILL 标识符
    assert "COMPILED SKILLS" not in cleaned
    assert "Decision Mode" not in cleaned
    assert "SKILL-2" not in cleaned
    assert "SKILL-3" not in cleaned
    assert "SKILL-7" not in cleaned
    assert "综合指令" not in cleaned
    assert "关键禁忌" not in cleaned
    assert "Applied Skills" not in cleaned
    print("✅ test_strip_basic_leak: 完整 SKILL 块被剥离")


def test_strip_partial_leak():
    """部分泄漏：前半段 SKILL + 后半段真叙事"""
    cleaned = strip_skill_metadata(LEAKED_TEXT_2)
    print(f"\n  清洗后 {len(cleaned)} 字符")
    assert "COMPILED DM SKILLS" not in cleaned, f"清洗后仍含 'COMPILED DM SKILLS': {cleaned[:100]}"
    assert "Applied Skills" not in cleaned
    assert "SKILL-2" not in cleaned
    # 真叙事部分应保留
    assert "米缸" in cleaned
    assert "阿宝" in cleaned
    print("✅ test_strip_partial_leak: 真叙事保留")


def test_no_strip_pure_narrative():
    """纯叙事不应被清洗"""
    cleaned = strip_skill_metadata(PURE_NARRATIVE)
    print(f"\n  清洗前 {len(PURE_NARRATIVE)} 字符")
    print(f"  清洗后 {len(cleaned)} 字符")
    # 应该 100% 保留
    assert cleaned == PURE_NARRATIVE.strip()
    # 或者非常接近（可能去掉尾部空白）
    assert "米缸" in cleaned
    assert "阿宝" in cleaned
    assert "银钱" in cleaned
    print("✅ test_no_strip_pure_narrative: 纯叙事完全保留")


def test_strip_empty_or_short():
    """空文本或太短文本"""
    assert strip_skill_metadata("") == "时间流逝。一切如常。"
    assert strip_skill_metadata(None) == "时间流逝。一切如常。"
    # 只有元数据的短文本
    short = "=== COMPILED SKILLS ===\n## Decision Mode: now_time"
    cleaned = strip_skill_metadata(short)
    assert cleaned == "时间流逝。一切如常。"
    print("✅ test_strip_empty_or_short: fallback 正确")


def test_repeated_time_span():
    """时间跨度重复行被合并"""
    text = """## ⏱️ SKILL-2 节奏控制
  时间跨度: 半天
  时间跨度: 半天
  时间跨度: 半天
  细节等级: 3/5

灶房里有一口大缸。
"""
    cleaned = strip_skill_metadata(text)
    # 时间跨度应只剩一行
    span_count = cleaned.count("时间跨度:")
    assert span_count <= 1, f"时间跨度应 ≤1，实际 {span_count}"
    assert "大缸" in cleaned
    print("✅ test_repeated_time_span: 重复行已合并")


def test_all_patterns_compiled():
    """所有正则能正常编译"""
    for i, p in enumerate(SKILL_METADATA_PATTERNS):
        assert p.pattern is not None
    print(f"✅ test_all_patterns_compiled: {len(SKILL_METADATA_PATTERNS)} 个正则全部编译成功")


def test_sanitize_integration():
    """🆕 v1.6.7 架构：sanitize() 一站式清洗（含 JSON 提取 + SKILL 剥离）"""
    # 模拟 LLM 各种输出场景
    cases = [
        # 1. 纯元数据
        ("=== COMPILED SKILLS ===\n## Decision Mode: now_time", "时间流逝"),
        # 2. 纯叙事
        ("灶房里，沈氏正在切菜。", "灶房里"),
        # 3. JSON 在 markdown 里
        ('```json\n{"narrative": "灶房里..."}\n```', "灶房里"),
        # 4. 空
        ("", "时间流逝"),
    ]
    for input_text, expected_substr in cases:
        result = sanitize(input_text)
        assert expected_substr in result, f"sanitize({input_text!r}) 应含 {expected_substr!r}，实际 {result!r}"
    print(f"✅ test_sanitize_integration: 4 种输入场景全部正确")


def test_brace_extraction():
    """纯文本 + 末尾 JSON 的提取"""
    import re
    raw = """some random prose

{"narrative": "真实叙事", "time_cost": 1}
"""
    brace_match = re.search(r"\{[\s\S]*?\}\s*$", raw.strip(), re.DOTALL)
    if brace_match:
        import json
        parsed = json.loads(brace_match.group(0))
        assert parsed["narrative"] == "真实叙事"
        print(f"✅ test_brace_extraction: 末尾 JSON 提取成功")


if __name__ == "__main__":
    print("=" * 50)
    print("SKILL 元数据泄漏修复 测试（v1.6.7）")
    print("=" * 50)
    test_all_patterns_compiled()
    test_strip_basic_leak()
    test_strip_partial_leak()
    test_no_strip_pure_narrative()
    test_strip_empty_or_short()
    test_repeated_time_span()
    test_sanitize_integration()
    print("\n✅ 所有 v1.6.7 SKILL 泄漏测试通过")