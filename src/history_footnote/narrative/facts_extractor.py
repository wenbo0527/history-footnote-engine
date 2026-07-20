"""🆕 v2.7.2 Narrative Facts Extractor - 结构化事实提取

解决"上下文不连贯"问题：
- 旧：每回合只把 LLM 输出 events_to_save[0] 当 summary（2-10 字）
- 新：每回合跑完后，调一次 LLM 专门从 narrative 提取 4 类结构化 fact：
    人物（NPC 身份/关系/承诺）
    事实（具体数字/物品/事件结果）
    伏笔（本回合埋下的未来钩子）
    未解（本回合未解决的问题）

提取的 fact 注入下回合 system prompt 的"最近剧情上下文"段，替代贫瘠的 summary。

设计原则：
- 串行调用（DM 出文后立即提取），超时 8s 不影响 narrative 响应
- 启发式 fallback（LLM 失败时用 regex 提取 NPC + 关键数字）
- fact 带 round + status 字段（open/resolved），方便后续检索
- 容量限制：每存档最多 50 条 fact（防 prompt 爆炸）
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# Fact Schema
# ============================================================

FACT_TYPES = ("character", "fact", "hook", "open_question")
# character: 人物（新 NPC 身份/关系/承诺/最近出现）
# fact:     事实（具体数字/物品/事件结果/状态）
# hook:     伏笔（本回合埋下的钩子，下回合可能用）
# open_question: 未解问题（本回合提出但未回答的问题）

MAX_FACTS_PER_SAVE = 50
# 🆕 v2.10.11+：8.0 → 15.0
# minimax-anthropic API 实测 9-13 秒才能返回 JSON（包含 reasoning + tool_use 解析）
# 8.0 触发约 1/3 turn timeout，15 留 5s buffer
EXTRACT_TIMEOUT = 15.0  # 秒


@dataclass
class NarrativeFact:
    """一条结构化 fact"""
    type: str  # character / fact / hook / open_question
    content: str  # 中文一句话（20-60 字）
    key: str = ""  # 规范化 key（用于去重/合并）
    round: int = 0
    status: str = "open"  # open / resolved
    importance: int = 5  # 1-10，用于分级注入
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "NarrativeFact":
        return NarrativeFact(
            type=d.get("type", "fact"),
            content=d.get("content", ""),
            key=d.get("key", ""),
            round=d.get("round", 0),
            status=d.get("status", "open"),
            importance=d.get("importance", 5),
            created_at=d.get("created_at", time.time()),
        )


# ============================================================
# LLM 提取 prompt
# ============================================================

EXTRACT_PROMPT = """你是明代历史 RPG 游戏的「事实提取器」。你的唯一职责是从以下 narrative 文本中提取 4 类结构化事实。

【narrative 文本】
{narrative}

【提取要求】
请严格按 JSON 格式输出 4 类 fact，每类 1-3 条，**总计不超过 8 条**：

1. **character**（人物）— NPC 身份/关系/承诺/新登场
   - 例：`{{"type": "character", "content": "沈氏是玩家妻子", "key": "shen_wife", "importance": 9}}`
   - 例：`{{"type": "character", "content": "赵里长是收税的", "key": "zhao_lizhang", "importance": 8}}`

2. **fact**（事实）— 具体数字/物品/事件结果/状态变化
   - 例：`{{"type": "fact", "content": "阿宝束脩要二两银子", "key": "tuition_2liang", "importance": 9}}`
   - 例：`{{"type": "fact", "content": "玩家有 2 台织机", "key": "loom_count_2", "importance": 7}}`

3. **hook**（伏笔）— 本回合埋下的钩子（玩家会关心的未来线索）
   - 例：`{{"type": "hook", "content": "赵里长今天要来收春税预单", "key": "tax_arriving_today", "importance": 8}}`
   - 例：`{{"type": "hook", "content": "阿宝明天开课要交束脩", "key": "school_starts_tomorrow", "importance": 9}}`

4. **open_question**（未解）— 本回合提出但未回答的问题
   - 例：`{{"type": "open_question", "content": "玩家要不要让阿宝去念书", "key": "ah_bao_school", "importance": 8}}`
   - 例：`{{"type": "open_question", "content": "二两束脩从哪里出", "key": "tuition_funding", "importance": 9}}`

【输出 JSON 格式】
```json
{{
  "facts": [
    {{"type": "character", "content": "...", "key": "...", "importance": 7}},
    {{"type": "fact", "content": "...", "key": "...", "importance": 8}}
  ]
}}
```

【规则】
- 严格 4 类，每类 1-3 条，总数 ≤ 8 条
- content 用 20-60 字中文短句
- key 用英文 snake_case，去重用
- importance 1-10（9-10 关键伏笔/未解；7-8 重要事实/人物；5-6 普通细节）
- 不要提取"游戏机制"（如"行动点"），只提取"剧情事实"
- 玩家视角提取（用"玩家"/"当家的"等称呼）"""


# ============================================================
# 启发式 fallback（LLM 失败时用）
# ============================================================

# 匹配"XX说/道/答"中的 speaker
_NPC_PAT = re.compile(r"([\u4e00-\u9fff]{2,5})(?:说|道|答道|笑道|叹道)[，：:]?['\"「『]")
# 匹配"X两银子/钱/分/厘/文"（🆕 v2.10.2 支持所有单位）
_MONEY_PAT = re.compile(
    r"([零一二三四五六七八九十百千半\d.]+)\s*(两|钱|分|厘|文)\s*(?:银|银子|白银)?"
)
# 匹配"X岁/年纪"
_AGE_PAT = re.compile(r"([\u4e00-\u9fff\d]+)\s*岁")


def _fallback_extract(narrative: str, round_num: int) -> list[NarrativeFact]:
    """LLM 失败时的启发式 fallback：粗略提取 NPC + 数字"""
    facts: list[NarrativeFact] = []
    seen_keys: set[str] = set()

    # 1. NPC 提取（取前 3 个 speaker）
    for speaker in _NPC_PAT.findall(narrative)[:3]:
        if speaker in seen_keys:
            continue
        if any(c in "我你他她它们的是了在有和与及" for c in speaker[:1]):
            continue
        facts.append(NarrativeFact(
            type="character",
            content=f"出现 NPC：{speaker}",
            key=f"npc_{speaker}",
            round=round_num,
            importance=6,
        ))
        seen_keys.add(speaker)

    # 2. 金额数字（取前 2 个）
    for m in _MONEY_PAT.finditer(narrative):
        v = m.group(1)
        if v in seen_keys:
            continue
        facts.append(NarrativeFact(
            type="fact",
            content=f"提到金额 {v} 两",
            key=f"money_{v}",
            round=round_num,
            importance=6,
        ))
        seen_keys.add(v)
        if sum(1 for f in facts if f.type == "fact") >= 2:
            break

    # 3. 末尾钩子启发式（最后一句"问号"句）
    last_q = re.search(r"([^。]*\？)[^。]*$", narrative.strip())
    if last_q:
        q_text = last_q.group(1).strip()[:60]
        if q_text and len(q_text) > 5:
            facts.append(NarrativeFact(
                type="open_question",
                content=q_text,
                key=f"q_round{round_num}",
                round=round_num,
                importance=7,
            ))

    return facts[:8]


# ============================================================
# 主入口
# ============================================================

def extract_facts_from_narrative(
    narrative: str,
    round_num: int,
    llm_wrapper=None,
    timeout: float = EXTRACT_TIMEOUT,
) -> list[NarrativeFact]:
    """从 narrative 提取 4 类结构化 fact

    Args:
        narrative: 完整的 narrative 文本
        round_num: 当前回合号
        llm_wrapper: LLMWrapper 实例（可选，None 时用 fallback）
        timeout: LLM 调用超时

    Returns:
        list[NarrativeFact]，最多 8 条
    """
    if not narrative or not narrative.strip():
        return []

    # 1. 尝试 LLM 提取
    if llm_wrapper is not None:
        try:
            facts = _extract_with_llm(narrative, round_num, llm_wrapper, timeout)
            if facts:
                return facts
        except Exception as e:
            logger.warning(f"[facts_extractor] LLM 提取失败: {e}，降级到启发式")

    # 2. Fallback 启发式
    return _fallback_extract(narrative, round_num)


def _extract_with_llm(
    narrative: str,
    round_num: int,
    llm_wrapper,
    timeout: float,
) -> list[NarrativeFact]:
    """调 LLM 提取 fact"""
    # 截取 narrative 末尾 1500 字（保留钩子/伏笔）
    snippet = narrative[-1500:] if len(narrative) > 1500 else narrative

    # 🆕 v2.7.2 修复：用 .replace 而非 .format（避免 prompt 里的 {{...}} 被误解）
    prompt = EXTRACT_PROMPT.replace("{narrative}", snippet)
    messages = [
        {"role": "user", "content": prompt},
    ]

    t0 = time.time()
    response = llm_wrapper.invoke(messages, timeout=timeout)
    latency = (time.time() - t0) * 1000
    logger.info(f"[facts_extractor] LLM 提取耗时 {latency:.0f}ms")

    # 解析 response（兼容 AIMessage / dict / str）
    content = _extract_text_from_response(response)
    if not content:
        return []

    # 解析 JSON
    data = _parse_json_from_text(content)
    if not data or "facts" not in data:
        return []

    facts = []
    for f in data["facts"]:
        if not isinstance(f, dict):
            continue
        ftype = f.get("type", "fact")
        if ftype not in FACT_TYPES:
            continue
        content_text = f.get("content", "").strip()
        if not content_text:
            continue
        facts.append(NarrativeFact(
            type=ftype,
            content=content_text,
            key=f.get("key", "").strip(),
            round=round_num,
            importance=int(f.get("importance", 5)),
        ))

    return facts[:8]


def _extract_text_from_response(response) -> str:
    """从 LLM response 拿文本内容（兼容多种格式）"""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("content", "") or response.get("text", "")
    # AIMessage 对象
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # 多模态时 list[{type, text}]
        texts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                texts.append(c.get("text", ""))
            elif isinstance(c, str):
                texts.append(c)
        return "\n".join(texts)
    text = getattr(response, "text", None)
    if text:
        return text
    return str(response)


def _parse_json_from_text(text: str) -> Optional[dict]:
    """从 LLM 输出中抠出 JSON（兼容 ```json ... ``` 包裹）"""
    if not text:
        return None
    # 1. 尝试找 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2. 尝试找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ============================================================
# 分级注入：构造注入到 prompt 的 fact 段
# ============================================================

# 注入优先级
TYPE_INJECTION_LEVEL = {
    "character": "always",       # 人物永远注入
    "fact": "always",            # 事实永远注入
    "hook": "relevant",          # 伏笔按相关度
    "open_question": "relevant", # 未解问题按相关度
}


def build_facts_injection(
    facts: list[NarrativeFact],
    player_input: str = "",
    max_always: int = 10,
    max_relevant: int = 3,
) -> str:
    """构造要注入到 system prompt 的 fact 段（分级注入）

    策略：
    - 人物/事实类：全量注入（按 importance 排序，取 top max_always）
    - 伏笔/未解类：按 player_input 关键词简单匹配 + importance，取 top max_relevant

    Returns:
        Markdown 字符串，空表示无注入
    """
    if not facts:
        return ""

    # 分离 always / relevant
    always_facts = [f for f in facts if TYPE_INJECTION_LEVEL.get(f.type) == "always"]
    relevant_pool = [f for f in facts if TYPE_INJECTION_LEVEL.get(f.type) == "relevant"]

    # 按 importance 排序
    always_facts.sort(key=lambda x: (-x.importance, -x.created_at))
    always_top = always_facts[:max_always]

    # relevant 简化为"取 importance 最高的 max_relevant 条"（避免引入 LLM 调用）
    relevant_pool.sort(key=lambda x: (-x.importance, -x.created_at))
    relevant_top = relevant_pool[:max_relevant]

    if not always_top and not relevant_top:
        return ""

    lines = [
        "## 📌 剧情事实锚点（v2.7.2+ 关键修复：保持叙事连贯性）",
        "",
        "**重要**：以下是从之前回合提取的事实。你的下一回合叙事**必须**承接这些事实，",
        "**不可**与已发生事实矛盾。人物/事实类**始终**生效，伏笔/未解类按场景参考。",
        "",
    ]

    if always_top:
        lines.append("### 人物 / 事实（始终生效）")
        for f in always_top:
            star = " ⭐" if f.importance >= 9 else ""
            lines.append(f"- [{f.type}] {f.content}{star}")
        lines.append("")

    if relevant_top:
        lines.append("### 伏笔 / 未解（按场景参考）")
        for f in relevant_top:
            star = " ⭐" if f.importance >= 9 else ""
            lines.append(f"- [{f.type}] {f.content}{star}")
        lines.append("")

    return "\n".join(lines)
