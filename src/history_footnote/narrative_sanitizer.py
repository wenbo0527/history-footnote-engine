"""🆕 v1.6.7 架构重构：Narrative Sanitizer

将 LLM 输出清洗逻辑从 dm_agent / game_loop / web_server 三处散落实现
沉淀为单一权威模块。

设计原则：
- 单一职责：只负责"清洗"（不是"生成"或"校验"）
- 无副作用：纯函数（输入字符串 → 输出字符串）
- 可观察：可被 LangGraph 节点调用、可被 web API 调用
- 可测试：纯逻辑，无外部依赖

职责清单：
1. 提取 markdown 包裹的 JSON 块
2. 剥离 SKILL 元数据（COMPILED SKILLS / Decision Mode / SKILL-N 段等）
3. 合并重复行（时间跨度: 半天 多次）
4. 太短内容 fallback

不在本模块：
- 不做 LLM 重新调用
- 不做状态更新
- 不做格式强制（这是 post_validator 的职责）
"""
from __future__ import annotations

import re
from typing import Optional


# 🆕 单一权威：所有 SKILL 元数据正则
# 同时供 Python（dm_agent）和 HTTP API（web_server）使用
# 注意：行模式用 MULTILINE，正则要"匹配一整段"（标题行+后续内容行）
SKILL_METADATA_PATTERNS: list[re.Pattern] = [
    # "=== COMPILED SKILLS FOR DM - Round 1B ==="
    re.compile(r"===\s*COMPILED\s+SKILLS.*?===\n?", re.DOTALL | re.IGNORECASE),
    # "# COMPILED DM SKILLS - Round 1B" 整段（只吃缩进行）
    re.compile(r"^#\s*COMPILED\s+DM\s+SKILLS.*?(?=\n[^ \t]|\Z)", re.DOTALL | re.IGNORECASE | re.MULTILINE),
    # "## Generated: 2027-01-19 22:55:08"（含或不含换行符）
    re.compile(r"^##\s*Generated:[^\n]*\n?", re.IGNORECASE | re.MULTILINE),
    # "## Decision Mode: now_time"（含或不含换行符）
    re.compile(r"^##\s*Decision Mode:[^\n]*\n?", re.IGNORECASE | re.MULTILINE),
    # "### Applied Skills for This Turn:" 整段（只吃缩进行）
    re.compile(r"^###\s*Applied Skills for This Turn:.*?(?=\n[^ \t]|\Z)", re.DOTALL | re.IGNORECASE | re.MULTILINE),
    # 通用 SKILL 段（## 开头 + 任意内容 + SKILL-N 标题 + 缩进内容行）
    # 兼容 ## ⏱️ SKILL-2 节奏控制 这种带 emoji 的形式
    # 🆕 关键改进：只吃缩进过的行（前导空白），无缩进行=新段落
    re.compile(r"^##[^\n]*SKILL[-‑]?\d[^\n]*\n((?:^[ \t].*\n?)*)", re.MULTILINE),
    # 单行 SKILL 标题（无后续内容的情况）
    re.compile(r"^##[^\n]*SKILL[-‑]?\d[^\n]*\n?", re.MULTILINE),
    # "## 📌 综合指令" 段（只吃缩进内容）
    re.compile(r"^##\s*📌\s*综合指令[^\n]*\n((?:^[ \t].*\n?)*)", re.MULTILINE),
    # 单行 "## 📌 综合指令" 标题
    re.compile(r"^##\s*📌\s*综合指令[^\n]*\n?", re.MULTILINE),
    # "## ⚠️ 关键禁忌" 段（只吃缩进内容）
    re.compile(r"^##\s*⚠️\s*关键禁忌[^\n]*\n((?:^[ \t].*\n?)*)", re.MULTILINE),
    # 单行 "## ⚠️ 关键禁忌" 标题
    re.compile(r"^##\s*⚠️\s*关键禁忌[^\n]*\n?", re.MULTILINE),
    # 单独的 "Applied Skills" 等孤立行
    re.compile(r"^\s*Applied\s+Skills.*\n?", re.MULTILINE | re.IGNORECASE),
    # 重复的"时间跨度: ..."行（保留第一行）
    re.compile(r"^(时间跨度:.*\n){2,}", re.MULTILINE),
]

# JSON 提取模式（用于 LLM 在 markdown 中包裹 JSON 的情况）
JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
JSON_TRAILING_PATTERN = re.compile(r"\{[\s\S]*?\}\s*$", re.MULTILINE)


def extract_json_from_text(text: str) -> Optional[str]:
    """从 LLM 输出中提取 JSON 块

    支持：
    - ```json ... ``` 包裹
    - 文本末尾 {...} 块
    - 纯 JSON 字符串

    Args:
        text: LLM 输出

    Returns:
        提取出的 JSON 字符串，如果找不到返回 None
    """
    if not text:
        return None
    # 优先尝试 markdown 包裹
    m = JSON_BLOCK_PATTERN.search(text)
    if m:
        return m.group(1)
    # 尝试末尾的 {...}
    m = JSON_TRAILING_PATTERN.search(text.strip())
    if m:
        return m.group(0)
    # 整段就是 JSON
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    return None


def strip_skill_metadata(text: str, min_length: int = 5) -> str:
    """剥离 LLM 输出中的 SKILL 元数据

    这是核心清洗函数。当 LLM 把 system prompt 里的 SKILL 指令
    复制到 narrative 字段时，用此函数清洗。

    Args:
        text: 可能是 LLM 输出的整段文本
        min_length: 清洗后少于这个字符数视为"全是元数据"，用 fallback
                    默认为 5（短叙事如"大缸里有米" 也算有效）

    Returns:
        清洗后的纯叙事文本
    """
    if not text:
        return "时间流逝。一切如常。"

    cleaned = text
    for pattern in SKILL_METADATA_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # 清理多余空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned) < min_length:
        return "时间流逝。一切如常。"

    return cleaned


def sanitize(text: str) -> str:
    """一站式清洗：先提 JSON，再清 SKILL，最后 fallback

    Args:
        text: LLM 原始输出

    Returns:
        清洗后的 narrative 文本
    """
    if not text:
        return "时间流逝。一切如常。"

    # 第一步：尝试提取 JSON 块
    import json
    json_text = extract_json_from_text(text)
    if json_text:
        try:
            parsed = json.loads(json_text)
            if isinstance(parsed, dict) and "narrative" in parsed:
                # 从 JSON 中拿到 narrative 字段，再清洗一次
                return strip_skill_metadata(parsed["narrative"])
            elif isinstance(parsed, dict):
                # JSON 完整但没 narrative 字段（异常情况）
                return "时间流逝。一切如常。"
        except json.JSONDecodeError:
            pass

    # 第二步：纯文本清洗
    return strip_skill_metadata(text)


def patterns_as_dict() -> dict:
    """导出正则模式（供前端 API 同步使用）"""
    return {
        "version": "1.6.7",
        "patterns": [p.pattern for p in SKILL_METADATA_PATTERNS],
        "fallback": "时间流逝。一切如常。",
        "min_length": 5,
    }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    import sys
    print("=" * 50)
    print("Narrative Sanitizer 测试（v1.6.7）")
    print("=" * 50)

    LEAKED = """=== COMPILED SKILLS FOR DM - Round 1B (Continuation) ===
# COMPILED DM SKILLS - Round 1B
## Generated: 2027-01-19 22:55:08
## Decision Mode: now_time

### Applied Skills for This Turn:

## ⏱️ SKILL-2 节奏控制 → now_time
  现在时间：正常推进
  时间跨度: 半天
  时间跨度: 半天
  时间跨度: 半天
  细节等级: 3/5

## ⚖️ SKILL-7 三层裁判
  层级: free | 判定: allow

## 📌 综合指令
  本回合采用【now_time】
"""

    PURE = """你站在灶房中央，看着面前的米缸和炭火。

锅里还有一些昨天的剩粥，阿宝还在睡，灶房清冷得很。
"""

    MIXED_JSON = """## ⏱️ SKILL-2 节奏控制 → now_time

```json
{
  "narrative": "灶房里，沈氏正在切菜。你看着她切，心里盘算着米缸还剩多少。",
  "is_action": true,
  "time_cost": 1
}
```
"""

    # 测试 1：基本清洗
    cleaned = strip_skill_metadata(LEAKED)
    assert "COMPILED SKILLS" not in cleaned
    assert "Decision Mode" not in cleaned
    assert "SKILL-2" not in cleaned
    assert "SKILL-7" not in cleaned
    assert "综合指令" not in cleaned
    print(f"✅ strip_skill_metadata: 611 → {len(cleaned)} 字符")

    # 测试 2：纯叙事保留
    cleaned_pure = strip_skill_metadata(PURE)
    assert "米缸" in cleaned_pure
    assert "阿宝" in cleaned_pure
    print(f"✅ strip_skill_metadata 纯叙事: {len(PURE)} → {len(cleaned_pure)} 字符（保留）")

    # 测试 3：JSON 提取
    json_str = extract_json_from_text(MIXED_JSON)
    assert json_str is not None
    import json as _json
    parsed = _json.loads(json_str)
    assert "narrative" in parsed
    print(f"✅ extract_json_from_text: 提取 {len(json_str)} 字符 JSON")

    # 测试 4：sanitize 一站式（整段是元数据 → fallback）
    result = sanitize(LEAKED)
    assert result == "时间流逝。一切如常。", f"纯元数据应 fallback，实际: {result!r}"
    print(f"✅ sanitize 整段纯元数据: {len(LEAKED)} → {len(result)} 字符（fallback）")

    result_json = sanitize(MIXED_JSON)
    assert "灶房里" in result_json
    assert "COMPILED" not in result_json
    print(f"✅ sanitize 混合 JSON: {len(MIXED_JSON)} → {len(result_json)} 字符")

    # 测试 5：空文本 fallback
    assert sanitize("") == "时间流逝。一切如常。"
    assert sanitize(None) == "时间流逝。一切如常。"
    print(f"✅ sanitize 空文本: fallback 正确")

    # 测试 7：太短内容 fallback
    short = "## S"  # 4 字符 < 5
    assert sanitize(short) == "时间流逝。一切如常。"
    print(f"✅ sanitize 太短内容: fallback 正确")

    # 测试 7：模式导出（供前端 API）
    patterns = patterns_as_dict()
    assert patterns["version"] == "1.6.7"
    assert len(patterns["patterns"]) == len(SKILL_METADATA_PATTERNS)
    print(f"✅ patterns_as_dict: {len(patterns['patterns'])} 个模式")

    print("\n✅ 所有 Narrative Sanitizer 测试通过")