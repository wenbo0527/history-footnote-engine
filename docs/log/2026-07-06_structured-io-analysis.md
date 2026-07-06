# 技术分析 —— 输入输出结构化方案

**日期**：2026-07-06
**版本**：v1.7.27
**作者**：AI 协作（Claude + Trae IDE）
**主题**：从"JSON 配置 + Python 解析"到"鲁棒多模态"——历史脚注引擎的 IO 结构化方案演进

---

## 📋 目录

1. [三个相关概念](#-1-三个相关概念)
2. [当前实现全景](#-2-当前实现全景)
3. [实际流程图](#-3-实际流程图)
4. [关键模块分析](#-4-关键模块分析)
5. [设计与实际对比](#-5-设计与实际对比)
6. [实际工作流](#-6-实际工作流-例子)
7. [当前方案优劣势](#-7-当前方案优劣势)
8. [改进建议](#-8-改进建议)
9. [关键结论](#-9-关键结论)
10. [相关文件清单](#-10-相关文件清单)

---

## 📌 1. 三个相关概念

| 概念 | 是什么 | 位置 |
|---|---|---|
| **配置 JSON** | 时代包数据（事件/规则/数值）| `eras/wanli1587/era.json` |
| **输入结构化** | LLM 输入格式（prompt schema）| `dm/prompts/system_base.md` |
| **输出结构化** | LLM 输出格式（JSON + 文本）| **混合模式**（核心） |

---

## 📊 2. 当前实现全景

### A. 配置层（JSON 配置文件）

**`eras/wanli1587/era.json`** —— 这是**配置数据**（不是 LLM 通信格式）：

```json
{
  "era_id": "wanli1587",
  "era_name": "万历十五年",
  "version": "1.1.0",
  "world": {
    "timeline": {
      "start": {"year": 1587, "month": 1},
      "end": {"year": 1601, "month": 10},
      "round_unit": "month",
      "total_rounds": 50
    },
    "iron_laws": [
      {
        "id": "il_01",
        "fact": "万历帝自1585年起逐渐怠政，1587年后长期不视朝",
        "source": "明史·神宗本纪"
      }
    ],
    "random_events": [...]
  },
  "knowledge": {
    "narrative_snippets": [...],
    "story_segments": [...]
  },
  "player_identities": [...]
}
```

**Python 加载方式**（直接当 dict 用，不需要解析）：

```python
import json
config = json.loads(open("era.json").read())
# config["iron_laws"] → 直接 list
# config["knowledge"]["narrative_snippets"] → 直接 list
```

### B. 输入结构化（LLM Prompt）

**`dm/prompts/system_base.md`** —— **明确要求 LLM 输出 JSON**：

```markdown
## 📤 输出格式（严格遵守）

你必须输出合法 JSON：

```json
{
  "narrative": "具体场景描写（半文半白，**必须 300-500 字**，绝对不能 < 100 字)",
  "narrative_blocks": [   // 🆕 v1.7.0 可选：结构化分段
    {"type": "scene",      "text": "环境描写..."},
    {"type": "dialogue",   "speaker": "张顺", "text": "三两三"},
    {"type": "monologue",  "text": "他出价低..."},
    {"type": "transition", "text": "片刻后"}
  ],
  "is_action": true,
  "time_cost": 2,
  "intent_type": "action",  // action | inquire | describe | voice
  "voice_options": [         // 🆕 v1.5+：2-4 个内在声音选项
    {
      "voice_id": "voice_xxx",
      "voice_name": "内在声音名",
      "intent_text": "按这个声音行动时，玩家实际做的事（10-20字）"
    }
  ],
  "state_changes": {"variable_id": +1.0},
  "events_to_save": ["事件摘要"],
  "updates": {"insight:xxx": "unlocked"}
}
```

### 🆕 v1.7.0 连贯性约束（必须遵守）

1. **承接上文**：本次叙事必须承接"最近 3 回合"中的地点、NPC、玩家状态。
2. **选项永远存在**（固定模块）：`voice_options` 必须有 2-4 个选项，**永远不能为空**。
3. **narrative_blocks 优先**（可选但鼓励）。
```

### C. 输出结构化（实际实现）—— **混合模式**

**实测 LLM 输出**（R1 响应，从 `/api/input` 拿到的数据）：

```python
{
  "recent_narratives": [{
    "round": 1,
    "summary": "...",
    "narrative": "屋子正中两台织机是你吃饭的家伙，榉木架子还算结实..."  # ← 纯文本！
  }],
  "last_voice_options": [
    {
      "voice_id": "voice_accountant",
      "voice_name": "算盘声",
      "intent_text": "再盘算盘算，看能不能借到银子或换条活路"
    },
    {
      "voice_id": "voice_compliance",
      "voice_name": "本分",
      "intent_text": "照官府说的办，别给家里招祸"
    },
    {
      "voice_id": "voice_craft",
      "voice_name": "手艺人的骄傲",
      "intent_text": "把活儿做好，名声立住了自然有客来"
    }
  ]
}
```

**关键发现**：
- ✅ LLM 输出**纯文本** narrative（不是 JSON）
- ✅ `voice_options` **不是**从 LLM JSON 拿的（LLM 没输出）
- ✅ `voice_options` 是**后端从 narrative 文本提取**（inline 列表）+ **context-aware 兜底**

---

## 🔍 3. 实际流程图

```
┌──────────────────────────────────────────────────────────────┐
│                    LLM 输入（Prompt）                          │
│                                                              │
│  system_base.md 要求：                                         │
│  "你必须输出合法 JSON"                                       │
│  ```json                                                       │
│  { "narrative": "...", "voice_options": [...], ... }         │
│  ```                                                          │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                    LLM 实际输出                                │
│                                                              │
│  情况 A（理想）：输出 JSON 块                                 │
│  ```json                                                      │
│  { "narrative": "...", "voice_options": [...], ... }         │
│  ```                                                          │
│                                                              │
│  情况 B（实际多见）：输出纯文本                                │
│  屋子正中两台织机是你吃饭的家伙...                            │
│  （根本不是 JSON）                                            │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              后端解析（v1.6.7 后的核心）                        │
│                                                              │
│  1. narrative_sanitizer.sanitize()                            │
│     - extract_json_from_text() 试提取 JSON                    │
│     - 提取成功 → 拿 narrative 字段                            │
│     - 提取失败 → strip_skill_metadata() 清洗文本              │
│                                                              │
│  2. narrative_sanitizer.merge_voice_options()                 │
│     - structured_options 不空 → 直接用                        │
│     - 空 → extract_inline_options() 从 narrative 文本         │
│       提取 "**一、**" "**二、**" 列表项                       │
│                                                              │
│  3. dm_agent.py context-aware 兜底                            │
│     - 关键词匹配（织/银/官/牙行 → 4 种时代个性声音）          │
│     - base 兜底声音池补足                                     │
│     - 去重 + 截取前 3                                         │
│                                                              │
│  4. sidebar_parser.build_sidebar_data()                       │
│     - parse_aside_block() 找 <aside>...</aside> 块            │
│     - infer_from_narrative() 找关键词（"税"/"束脩"等）        │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              post_validator 校验（4 层）                        │
│                                                              │
│  1. 铁律（iron_laws）                                        │
│  2. 行动边界（action_boundaries）                             │
│  3. 时间一致性（不能"快进"或"倒退"）                          │
│  4. 史实锚点（historical_anchors）                            │
│                                                              │
│  不通过 → 标记 issue → 触发重试                                │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                   写入 state + 返回前端                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 4. 关键模块分析

### 模块 1: `narrative_sanitizer.py`（~480 行）

**3 个核心函数**：

```python
def sanitize(text: str) -> str:
    """一站式清洗：先提 JSON，再清 SKILL，最后 fallback"""
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

    # 第二步：直接当文本处理
    return strip_skill_metadata(text)


def merge_voice_options(
    structured_options: list[dict] | None,
    narrative_text: str,
) -> list[dict]:
    """🆕 v1.6.9 合并 voice_options：优先用结构化选项，缺失时回填内嵌选项"""
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


def extract_inline_options(narrative: str) -> list[dict]:
    """从 narrative 文本提取 '**一、**' 列表项"""
    # 正则：**一、xxx** ... **二、yyy**
    pattern = re.compile(r'\*\*([一二三四五六七八九十]+)、\s*([^*]+?)\*\*')
    matches = pattern.findall(narrative)
    return [{"index": f"一", "label": "..."}, ...] if matches else []
```

### 模块 2: `dm_agent.py`（~1200 行，LangGraph 状态机）

**5 个节点**：

```python
def make_dm_nodes(...):
    """构造 5 个 DM 决策节点"""
    return (
        skill_orchestration_node,      # 阶段1.1: 决定调哪些 Skill
        situation_assessment_node,     # 阶段1.2: 情况评估
        should_continue,                # 阶段1.3: 是否继续 Tool 调用
        narrative_fusion_node,          # 阶段2: 融合 Tool 结果生成叙事
        extract_narrative_node_inner,   # 阶段3: 提取 narrative
    )
```

**第一轮 LLM**（绑定 tools）：

```python
# LLM 返回 AIMessage(tool_calls=[...])
# tool_calls 格式：[{"name": "query_narrative_snippets", "args": {...}}, ...]
if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
    # 调 ToolNode
    ...
```

**第二轮 LLM**（融合 Tool 结果）：

```python
# Prompt 包含：原始 messages + 工具结果
response = llm_with_tools.invoke(state["messages"])
# LLM 返回 AIMessage(content="""```json
# { "narrative": "...", "voice_options": [...], ... }
# ```""")
# 或纯文本 narrative（实际更常见）
return {"messages": [response]}
```

**第三轮：提取 narrative**：

```python
def extract_narrative_node(state: DMState) -> dict:
    """从最后一条AIMessage中提取结构化叙事"""
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            # 🆕 v1.6.7：单一权威 sanitize()（JSON 提取 + SKILL 剥离 + fallback 一站完成）
            narrative_data["narrative"] = _narrative_sanitize(msg.content)
            break
    ...
```

**Tool 定义**（用 LangChain `@tool` 装饰器）：

```python
from langchain_core.tools import tool

@tool
def get_state() -> dict:
    """获取当前游戏状态（变量值+已触发事件+NPC状态+回合数）"""
    view = rule_engine.make_view(state)
    return {
        "round": state.round_number,
        "date": state.current_date,
        "variables": dict(state.variables),
        ...
    }

@tool
def recall_events(query: str = "", recent_n: int = 3, by_entity: str = "") -> list[dict]:
    """召回相关历史事件"""
    return memory.recall_events(query=query, recent_n=recent_n, by_entity=by_entity)

@tool
def check_rules(action: str = "", check_type: str = "all") -> dict:
    """查询规则引擎"""
    view = rule_engine.make_view(state)
    result = {}
    if check_type in ("all", "action_boundary") and action:
        result["action_check"] = rule_engine.check_action(view, action)
    ...
    return result
```

**Tool 绑定到 LLM**：

```python
# 绑定 tools 到 LLM（真实 LLM 需要这一步）
if hasattr(self.llm, "bind_tools"):
    new_llm = self.llm.bind_tools(self.tools)
    self._llm_with_tools = new_llm
```

### 模块 3: `post_validator.py`（~400 行）

**4 层校验**（不修改输出结构，只检查）：

```python
def post_validate(dm_response, era_config, state, ...) -> ValidationResult:
    """四层校验"""
    issues = []
    issues.extend(_validate_format(dm_response, narrative))
    issues.extend(_validate_iron_laws(dm_response, narrative, era_config))
    issues.extend(_validate_action_boundaries(dm_response, narrative, era_config, state))
    issues.extend(_validate_time_consistency(dm_response, state, current_date))
    issues.extend(_validate_anchors(dm_response, narrative, era_config))
    return ValidationResult(issues=issues)
```

**格式校验**（示例）：

```python
def _validate_format(dm_response: dict, narrative: str) -> list[ValidationIssue]:
    """格式校验"""
    issues = []
    if not narrative:
        issues.append(ValidationIssue(...))
    if narrative and len(narrative) < 100:
        issues.append(ValidationIssue(
            layer=ValidationLayer.FORMAT.value,
            severity="warning",
            message=f"叙事过短（{len(narrative)} 字），可能不够丰富",
        ))
    ...
```

---

## 📈 5. 设计与实际对比

| 维度 | 原始设计 | 当前实际 |
|---|---|---|
| **配置** | JSON 配置文件 | ✅ JSON 配置文件（era.json）|
| **LLM 输出要求** | JSON 严格 | ⚠️ Prompt 仍写 JSON，但 LLM 实际多输出文本 |
| **解析方式** | Python 解析 JSON | **混合**：JSON 优先 + 文本 fallback |
| **结构化字段** | 全部（9 个）| 部分（narrative 必有；voice_options 多 fallback）|
| **严格性** | 严格 | **宽松**（多重兜底）|
| **错误处理** | 错误 → 失败 | 错误 → 降级 + 重试 |
| **LLM 假设** | 严格遵循 | 概率性输出（不严格遵循）|

### 实际工作的"结构化"—— 字段级鲁棒性表

| 字段 | 来源 | 鲁棒性 |
|---|---|---|
| **narrative** | ① JSON.narrative → ② 纯文本 | 🟢 高（一定拿到）|
| **voice_options** | ① JSON.voice_options → ② inline 列表 → ③ context-aware 兜底 | 🟢 高（4 重兜底）|
| **state_changes** | ① JSON.state_changes → ② 规则引擎计算 | 🟡 中 |
| **time_cost** | ① JSON.time_cost → ② 规则判定 | 🟡 中 |
| **is_action** | ① JSON.is_action → ② 规则判定 | 🟡 中 |
| **intent_type** | ① JSON.intent_type → ② _detect_intent | 🟡 中 |
| **narrative_blocks** | ① JSON.narrative_blocks → ② 文本解析 | 🔴 低（基本靠 LLM）|
| **events_to_save** | ① JSON → ② 触发事件列表 | 🟡 中 |
| **updates** | ① JSON → ② insight_candidates fallback | 🟡 中 |

---

## 🔄 6. 实际工作流（例子）

### 例子：玩家输入"我去牙行问问有没有活计"

#### 步骤 1: LLM 第一次调用（绑定 tools）

```python
# LLM 返回 AIMessage(tool_calls=[...])
# tool_calls 格式示例：
# [
#   {"name": "get_state", "args": {}, "id": "call_1"},
#   {"name": "recall_events", "args": {"query": "牙行"}, "id": "call_2"},
#   {"name": "check_rules", "args": {"action": "去牙行"}, "id": "call_3"}
# ]
```

#### 步骤 2: ToolNode 执行（LangChain 自动）

```python
# 调 query_narrative_snippets → 返回 list[dict]
# 调 get_state → 返回当前游戏状态
# ToolMessage(content=JSON字符串)
```

#### 步骤 3: LLM 第二次调用（融合 Tool 结果）

```python
# Prompt 包含：原始 messages + 工具结果
# LLM 返回 AIMessage(content="""```json
# { "narrative": "...", "voice_options": [...], ... }
# ```""")
# 或纯文本 narrative（实际更常见）
```

#### 步骤 4: extract_narrative_node 提取

```python
# sanitize() 试提取 JSON → 失败则当文本
# merge_voice_options() 试 voice_options 字段 → 空则 inline
# 字段全部填好后返回 dict
```

#### 步骤 5: post_validate 校验

```python
# 4 层校验：铁律/边界/时间/史实
# 不通过 → 标记 issue → 触发重试
```

#### 步骤 6: 写入 state + 返回前端

---

## 🏆 7. 当前方案优劣势

### ✅ 优势

1. **鲁棒性强**：LLM 输出无论格式都能拿到数据
2. **不依赖严格遵循**：prompt 强化 + 重试 + 后端兜底
3. **DE 风格支持**：3 重保障的 voice_options
4. **可调试**：所有解析步骤都有日志
5. **向后兼容**：LLM 输出变化时仍能工作
6. **Function Calling 支持**：tools 绑定是 LangChain 标准

### ⚠️ 劣势

1. **LLM 资源浪费**：prompt 写 JSON 但 LLM 实际不输出
2. **解析复杂**：3 套 fallback 代码
3. **隐性 bug 风险**：fallback 边界情况难测
4. **状态不一致**：LLM 输出 JSON 但没 voice_options 字段 → 走 inline 提取
5. **维护成本**：JSON schema 变更需同步多处

---

## 🎯 8. 改进建议

### 短期（v1.7.28+）

1. **使用 OpenAI/Anthropic 的 `response_format: json_object`**：

   ```python
   response = llm.invoke(
       messages,
       response_format={"type": "json_object"},
   )
   ```

   - 强制 LLM 输出 JSON
   - 减少 fallback 复杂度
   - ⚠️ 部分 LLM（如 DeepSeek）不支持

2. **更严格的 prompt 约束**：
   - "你**必须**输出 JSON，否则会失败"
   - 给出 JSON 模板 + 反例
   - "如果输出不是 JSON，将无法进行游戏"

### 中期（v1.8+）

1. **完全结构化（Function Calling）**：

   ```python
   @tool
   def submit_dm_response(
       narrative: str,
       voice_options: list[dict],
       time_cost: int,
       is_action: bool,
       intent_type: str,
       state_changes: dict,
       events_to_save: list[str],
       updates: dict
   ) -> dict:
       """DM 提交最终响应（结构化）"""
       return {
           "narrative": narrative,
           "voice_options": voice_options,
           "time_cost": time_cost,
           "is_action": is_action,
           "intent_type": intent_type,
           "state_changes": state_changes,
           "events_to_save": events_to_save,
           "updates": updates,
       }
   ```

   - LLM 调 Tool 提交（**100% 结构化**）
   - 不用解析 narrative 文本
   - 字段类型由 LangChain 校验

2. **Pydantic 模型验证**：

   ```python
   from pydantic import BaseModel, Field
   from typing import Literal

   class VoiceOption(BaseModel):
       voice_id: str
       voice_name: str
       intent_text: str = Field(min_length=5, max_length=30)

   class DMResponse(BaseModel):
       narrative: str = Field(min_length=100, max_length=2000)
       voice_options: list[VoiceOption] = Field(min_length=2, max_length=4)
       time_cost: int = Field(ge=0, le=3)
       is_action: bool
       intent_type: Literal["action", "inquire", "describe", "voice"]
       state_changes: dict = Field(default_factory=dict)
       events_to_save: list[str] = Field(default_factory=list)
       updates: dict = Field(default_factory=dict)
   ```

   - LLM 严格遵循 schema
   - 自动验证 + 错误信息

3. **Prompt 改为 JSON 模式**：

   ```python
   response = llm.invoke(
       messages,
       response_format={"type": "json_object"},
   )
   ```

### 长期（v2.0+）

1. **结构化输出框架**（如 Instructor、Outlines）：
   - 自动从 Pydantic 模型生成 JSON schema
   - 传给 LLM 强制遵循
   - 自动重试 + 错误信息

2. **可视化调试工具**：
   - 显示 LLM 原始输出 + 解析后的字段
   - 标记 fallback 触发位置
   - 性能分析（哪步慢）

3. **多 Provider 兼容性**：
   - OpenAI：原生支持 response_format
   - Anthropic：通过 tool_use 模拟
   - DeepSeek：自有 API 差异
   - 本地模型（Ollama）：需特殊处理

---

## 💡 9. 关键结论

### 答用户问："原本设计 JSON 配置 + Python 解析，现在怎么解决的？"

| 维度 | 现状 |
|---|---|
| **配置** | JSON 配置文件（era.json）+ Python 直接 load |
| **LLM 输入** | Markdown prompt（含 JSON schema 示例）|
| **LLM 输出** | **JSON 块（理想）或纯文本（实际）**—— 不可控 |
| **解析** | **混合方案**：JSON 优先 → 文本解析 → 字段兜底 |

### 核心设计哲学转变

| 原始设计 | 实际实现 |
|---|---|
| **严格结构化** | **鲁棒多模态** |
| "LLM 必须输出 JSON" | "LLM 无论输出啥我都能解析" |
| 单点解析 | **多层兜底** |
| 错误 → 失败 | 错误 → 降级 |
| 假设 LLM 严格遵循 | 假设 LLM 概率性输出 |

### 重要洞察

> **这是一次重要的"现实主义"转变**——从理想化的"严格 JSON 协议"到务实的"鲁棒多模态解析"。
>
> **这是 v1.7.x 期间所有 v1.7.21-26 改进的根本出发点**。

### 关键经验

1. **LLM 是概率性模型**：prompt ≠ 执行
2. **必须有多层兜底**：单一解析路径不够鲁棒
3. **重试机制是底线**：LLM 偶尔输出异常是正常的
4. **可降级的设计**：即使 LLM 输出完全不可用，也能给玩家"时间流逝。一切如常。"
5. **实测 LLM 行为**：理论上的"JSON 输出"和实际上的"纯文本输出"差距很大

### 未来方向

- ✅ **短期**：用 `response_format: json_object` 强制 JSON
- ✅ **中期**：完全结构化（Function Calling 提交 DMResponse）
- ✅ **长期**：Pydantic 校验 + 多 Provider 兼容

---

## 📚 10. 相关文件清单

| 文件 | 行数 | 作用 |
|---|---|---|
| `narrative_sanitizer.py` | ~480 | narrative 文本清洗 + JSON 提取 + inline 选项提取 |
| `dm_agent.py` | ~1200 | LangGraph 状态机 + Tool 绑定 + 5 节点 |
| `post_validator.py` | ~400 | 4 层校验（不修改结构）|
| `system_base.md` | 258 | LLM prompt（含 JSON schema 规范）|
| `era.json` | 1000+ | 时代包配置 |
| `mock_llm.py` | ~400 | Mock LLM（测试用）|
| `narrative_renderer.py` | ~300 | narrative 渲染（前端展示）|
| `sidebar_parser.py` | 173 | 侧边栏数据解析（aside + 推断）|

---

## 🎓 总结

**当前结构化方案 = Prompt 引导 + 鲁棒多模态解析 + 多重兜底** —— 是工程实践中的"现实主义"选择。

这一方案**比"严格 JSON 协议"更鲁棒**，但**牺牲了一些效率**（LLM 资源浪费 + 解析复杂）。

**最佳实践路径**：
1. 先用 `response_format: json_object` 强制 JSON
2. 用 Pydantic 校验 + 自动错误信息
3. 兜底机制保留（应对边缘情况）
4. 持续监控 LLM 输出变化，动态调整解析策略

**核心理念**：**"假设 LLM 概率性输出"** + **"工程上多层兜底"** = **生产级可靠性**。
