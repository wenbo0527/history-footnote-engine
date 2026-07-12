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

    # 🆕 v1.7.7 英文 schema 清洗（防止 LLM 幻觉输出 spouse:/children:/elderly: 等）
    # 背景：LLM 训练数据里 family/character schema 常用英文键
    # 当 LLM 收到中文 system prompt 时，仍可能"翻译"成英文输出
    # 这些键名出现在叙事里破坏沉浸感
    # 模式：英文 key: value（整行删除，因为这些 schema 行本身无叙事价值）
    # 例：spouse: 陈氏（27岁...） / children: ['阿大', '二丫头'] / elderly: 老娘沈王氏
    # 兼容 key 后跟 [..] 列表 / (..) 元组 / 字符串 / 数字
    re.compile(
        r"^[ \t]*\b(spouse|children|elderly|household|family|background|age|gender|role|name|occupation|class|status|location|address)\s*:\s*"
        r"(?:\[[^\]]*\]|\([^)]*\)|[^\n]*)"
        r"\n?",
        re.MULTILINE | re.IGNORECASE,
    ),

    # 🆕 v1.7.19: 单行内嵌 family schema（行首是中文 label 如"家庭：spouse: ..."）
    # 模式：family/spouse/children/elderly key + value，但前面有任意文本
    # 例："家庭：spouse: 周氏 / children: ['阿福（9岁）', '阿芸（5岁）'] / elderly: 老娘..."
    # 修复策略：匹配 key: value 到下一个 " / " 或行尾，删除该段
    re.compile(
        r"\b(spouse|children|elderly|household|family)\s*:\s*"
        r"(?:\[[^\]]*\]|\([^)]*\)|[^/\n]+?)"
        r"(?=\s*(?:/|$|\n))",
        re.IGNORECASE,
    ),

    # 🆕 v1.7.11 LLM 思考过程 / 内部标记 清洗
    # <zh>...</zh> / <en>...</en> 是某些 LLM 输出的"思考语言标签"
    re.compile(r"<zh>.*?</zh>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<en>.*?</en>", re.DOTALL | re.IGNORECASE),
    # 裸的 <zh> 开标签但无闭合（LLM 输出被截断）
    re.compile(r"<zh>[^\n]*\n?(.*?)(?=\n\n|\Z)", re.DOTALL | re.IGNORECASE),
    # 脚注引用 [^N-N]: ... （LLM 引用原文时用）
    re.compile(r"^\s*\[\^?\d+[-‐‑‒–—]\d+\]:\s*[^\n]*\n?", re.MULTILINE),
]


# 🆕 v1.7.7 英文 family key → 中文标签
# 用于 LLM 输出含 [family] 段时，把英文 key 翻译为中文标签再插入正文
EN_FAMILY_KEY_TO_CN = {
    "spouse": "配偶",
    "children": "子女",
    "elderly": "老人",
    "household": "家口",
    "family": "家人",
    "background": "出身",
    "age": "年岁",
    "gender": "性别",
    "role": "身份",
    "name": "姓名",
    "occupation": "营生",
    "class": "身份",
    "status": "现状",
    "location": "住处",
    "address": "住址",
}

# JSON 提取模式（用于 LLM 在 markdown 中包裹 JSON 的情况）
# 🆕 W33: 用括号深度匹配而非 non-greedy 截断
# non-greedy `\{.*?\}` 会在第一个 `}` 停下，LLM JSON 通常 50+ 行 + 多个嵌套对象 → 截到一半
# 用括号深度算法找到真正匹配的结束 `}`
JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.DOTALL)
# 末尾 JSON（greedy，从末尾倒推找最深 `{`）
JSON_TRAILING_PATTERN = re.compile(r"\{[\s\S]*\}$", re.MULTILINE)


def extract_json_from_text(text: str) -> Optional[str]:
    """从 LLM 输出中提取 JSON 块

    支持：
    - ```json ... ``` 包裹
    - 文本末尾 {...} 块
    - 纯 JSON 字符串

    🆕 W32: 清洗 markdown 加粗（`**xxx**` → `xxx`）
    🆕 W33: 括号深度匹配（修 W32 的 non-greedy 截断 bug）
    🆕 W33: 清洗控制字符（LLM 长 scene 字段偶尔含裸换行/制表符）

    Args:
        text: LLM 输出

    Returns:
        提取出的 JSON 字符串，如果找不到返回 None
    """
    if not text:
        return None
    raw = None
    # 1. markdown 包裹 + 括号深度匹配
    m = JSON_BLOCK_PATTERN.search(text)
    if m:
        candidate = m.group(1)
        raw = _fix_truncated_json_brackets(candidate)
    # 2. 末尾 {...} 块（greedy）
    if raw is None:
        m = JSON_TRAILING_PATTERN.search(text.strip())
        if m:
            raw = _fix_truncated_json_brackets(m.group(0))
    # 3. 整段就是 JSON
    if raw is None:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            raw = _fix_truncated_json_brackets(stripped)
    if raw is None:
        return None

    # 4. 清洗 markdown 加粗
    cleaned = _strip_markdown_bold_in_json(raw)
    # 5. 清洗控制字符
    cleaned = _strip_control_chars(cleaned)
    return cleaned


def _fix_truncated_json_brackets(json_str: str) -> str:
    """括号深度匹配：找到真正匹配的 { ... }

    之前的 non-greedy `\\{.*?\\}` 会在第一个 `}` 停下。
    LLM JSON 50+ 行 + 嵌套对象（nodes 是 list of dict）→ 必须深度匹配。
    """
    if not json_str or not json_str.lstrip().startswith("{"):
        return json_str
    depth = 0
    in_str = False
    escape = False
    last_valid_end = -1
    for i, ch in enumerate(json_str):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_valid_end = i
                break
    if last_valid_end > 0:
        return json_str[: last_valid_end + 1]
    return json_str


def _strip_markdown_bold_in_json(json_str: str) -> str:
    """剥 JSON 字符串内的 markdown 加粗（**xxx** → xxx）"""
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", json_str)


def _strip_control_chars(json_str: str) -> str:
    """剥 JSON 字符串内的控制字符（裸换行/制表符）

    背景：LLM 偶尔在长 scene 字段输出未转义的换行（应写为 \\n）
    实际 JSON 标准允许字符串内裸换行（但 json.loads 严格模式会拒）
    这里把所有 0x00-0x1F 字符替换为空格（保留在引号外的不变）。
    """
    import json as _json
    try:
        _json.loads(json_str)
        return json_str  # 已合法就不动
    except _json.JSONDecodeError:
        pass
    # 不合法：在字符串外剥控制字符，字符串内替换 \\n
    out = []
    in_str = False
    escape = False
    for ch in json_str:
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == "\\":
            out.append(ch)
            escape = True
            continue
        if ch == '"' and not escape:
            in_str = not in_str
            out.append(ch)
            continue
        if in_str:
            if ord(ch) < 0x20:
                out.append(" ")  # 字符串内裸换行 → 空格
            else:
                out.append(ch)
        else:
            if ord(ch) < 0x20:
                out.append(" ")  # 字符串外裸换行 → 空格
            else:
                out.append(ch)
    return "".join(out)


def strip_skill_metadata(text: str, min_length: int | None = None) -> str:
    """剥离 LLM 输出中的 SKILL 元数据

    这是核心清洗函数。当 LLM 把 system prompt 里的 SKILL 指令
    复制到 narrative 字段时，用此函数清洗。

    Args:
        text: 可能是 LLM 输出的整段文本
        min_length: 清洗后少于这个字符数视为"全是元数据"，用 fallback
                    默认为 config.Sanitizer.MIN_LENGTH（5）

    Returns:
        清洗后的纯叙事文本
    """
    # 🆕 v1.7.2 默认值从 config 读（环境变量可覆盖）
    from history_footnote.config import Sanitizer as _SanCfg
    if min_length is None:
        min_length = _SanCfg.MIN_LENGTH

    if not text:
        return _SanCfg.FALLBACK_TEXT

    cleaned = text
    for pattern in SKILL_METADATA_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # 🆕 v1.7.24: 清洗末尾的"技术信息"（行动点/消耗等）
    # 背景：LLM 偶尔在 narrative 末尾输出 "**行动点：0/3（问询不消耗）**"
    #       破坏文学沉浸感 + 占用叙事空间
    # 修复：移除末尾的元信息块（横线分隔 + 技术元数据）
    cleaned = re.sub(
        r"\n*\s*---\s*\n+\s*\*\*行动点[^*]*\*\*\s*",
        "\n",
        cleaned,
        flags=re.MULTILINE,
    )
    # 也匹配 "消耗 X 点" 等元信息
    cleaned = re.sub(
        r"\n+\s*\*\*(消耗|行动点|时间)[^*]*\*\*\s*$",
        "",
        cleaned,
        flags=re.MULTILINE,
    )

    # 清理多余空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    # 🆕 v2.10.1 W69: 清洗 LLM 幻觉的 Jinja 占位符
    # 背景：LLM 看到 prompt 中的 {{...}} 模式会"模仿"产生新占位符
    #       （如 {{user_avatar_url}}、{{npc.name}}）→ 玩家看到裸 {{...}}
    # 修复：把所有 `{{...}}` `{%...%}` `{#...#}` 替换为「...」
    import re as _re2
    def _strip_brace(m: "re.Match[str]") -> str:
        body = m.group(0)[2:-2].strip()
        if not body or body[0] in "{%#":
            return "…"
        if len(body) > 20:
            return body[:20] + "…"
        return body
    cleaned = _re2.sub(r"\{\{[^}]{1,80}\}\}", _strip_brace, cleaned)
    cleaned = _re2.sub(r"\{%[^%]{1,80}%\}", "…", cleaned)
    cleaned = _re2.sub(r"\{#[^#]{1,80}#\}", "…", cleaned)

    # 🆕 v1.7.25: 末尾问号兜底（保证玩家永远有决策引导）
    # 背景：v1.7.24 prompt 强化 4 段结构 + 末尾问号，但 LLM 不一定遵循
    # 现象：5/5 narrative 末尾无问号（玩家不知道要决策什么）
    # 修复：检测末尾 30 字内无问号时，**追加**通用问句（不替换原文）
    if not _ends_with_question(cleaned):
        # 提取一个合适的"决策点"提示
        fallback_questions = [
            "\n\n**你想做什么？**",
            "\n\n**接下来怎么办？**",
            "\n\n**你怎么应对？**",
        ]
        # 用最后一句话作为锚点（去掉尾部标点）
        import random
        cleaned += fallback_questions[hash(cleaned[-20:]) % len(fallback_questions)]

    if len(cleaned) < min_length:
        return _SanCfg.FALLBACK_TEXT

    return cleaned


def _ends_with_question(text: str) -> bool:
    """🆕 v1.7.25: 检测末尾 30 字内是否有问号（含中英文 ?？）"""
    if not text:
        return False
    tail = text[-30:].strip()
    return ("?" in tail) or ("？" in tail)


# ============================================================
# 🆕 v1.6.9 叙事中的选项提取（LLM 写 narrative 时的"中文数字选项"）
# ============================================================

# 匹配中文章节编号 + 标题
# 例："一、**答应周老板**：..."  "二、全卖给张顺：..."  "3. 选项..."
# 关键：捕捉 [编号+顿号/点] 开头的行
OPTION_LINE_PATTERN = re.compile(
    r"^\s*([一二三四五六七八九十]+|\d{1,2})\s*[\.、:：]\s*\**\s*(.+?)(?=\n|$)",
    re.MULTILINE,
)

# 🆕 v1.7.11 真实 LLM 输出的"*" 包裹格式
# 例：*王掌柜开价一百一十文，当场成交省事，但比上月跌了十文。*
# 例：*去陈牙行碰碰运气，可能价高些，也可能白跑一趟。*
# 这种格式下没有"一、二、三"标号，但每行是一个独立选项
ASTERISK_OPTION_PATTERN = re.compile(
    r"^\*([^*]+)\*\s*$",
    re.MULTILINE,
)


def extract_inline_options(text: str, max_options: int = 6) -> list[dict]:
    """🆕 v1.6.9 从 narrative 文本中提取"中文章节选项"

    适用场景：LLM 把选项写进 narrative 文本（"一、**答应周老板**..."），
    而没有通过 voice_options 字段返回。

    Args:
        text: narrative 文本
        max_options: 最多提取多少个选项（默认 6）

    Returns:
        [{"index": "一", "label": "答应周老板", "full_text": "一、答应周老板：..."}, ...]
        如果没有找到，返回空列表
    """
    if not text:
        return []
    options = []
    matches = list(OPTION_LINE_PATTERN.finditer(text))

    # 🆕 启发式过滤：只保留"看起来像选项"的行
    # 要求：标签 ≥ 2 字符（避免"一、" 这种孤立行）
    for m in matches:
        index = m.group(1).strip()
        label = m.group(2).strip()
        # 清理：** 加粗、尾部标点
        label = re.sub(r"\*+", "", label).strip()
        # 取标签的前 20 字符（按钮显示用）
        display_label = label.split("：")[0].split(":")[0].strip()
        # 去掉 "：..." 之类后缀
        if len(display_label) < 2:
            continue
        if len(display_label) > 30:
            display_label = display_label[:30] + "..."
        options.append({
            "index": index,
            "label": display_label,
            "full_text": m.group(0).strip(),
        })
        if len(options) >= max_options:
            break

    # 🆕 v1.7.11: 真实 LLM 经常输出 *xxx* 格式的选项（无"一、二"标号）
    # 如果 OPTION_LINE_PATTERN 没找到，尝试 ASTERISK_OPTION_PATTERN
    if not options:
        asterisk_matches = list(ASTERISK_OPTION_PATTERN.finditer(text))
        for i, m in enumerate(asterisk_matches):
            label = m.group(1).strip()
            if len(label) < 4:
                continue
            # 取前 20 字作为按钮标签
            display_label = label[:20] + ("..." if len(label) > 20 else "")
            # 用数字标号（一、二、三...）
            index_chars = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            index = index_chars[i] if i < len(index_chars) else str(i + 1)
            options.append({
                "index": index,
                "label": display_label,
                "full_text": m.group(0).strip(),
            })
            if len(options) >= max_options:
                break

    return options


def merge_voice_options(
    structured_options: list[dict] | None,
    narrative_text: str,
) -> list[dict]:
    """🆕 v1.6.9 合并 voice_options：优先用结构化选项，缺失时回填内嵌选项

    Args:
        structured_options: LLM 通过 voice_options 字段返回的选项
        narrative_text: narrative 文本（fallback 解析来源）

    Returns:
        最终选项列表
    """
    if structured_options and len(structured_options) > 0:
        return structured_options

    # fallback：从 narrative 提取
    inline = extract_inline_options(narrative_text)
    if not inline:
        return []

    # 把内嵌选项转成 voice_options 格式
    converted = []
    for opt in inline:
        converted.append({
            "voice_name": opt["index"],
            "intent_text": opt["label"],
            "source": "inline_extracted",  # 标记：是从 narrative 提取的
        })
    return converted


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