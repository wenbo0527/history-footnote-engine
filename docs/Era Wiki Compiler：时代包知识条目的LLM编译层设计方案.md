# Era Wiki Compiler：时代包知识条目的LLM编译层设计方案

> 一句话定位：Raw Sources进，结构化知识条目出，人工审核后写入era.json。

---

## 一、整体架构

### 1.1 三层结构

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Raw Sources（不可变原始资料）            │
│  《万历十五年》、明史食货志、江南方志、论文...       │
│  只读，LLM读取但不修改，这是真相来源               │
└──────────────────────┬──────────────────────────┘
                       │ 摄入
                       ▼
┌─────────────────────────────────────────────────┐
│  Layer 2: Wiki（LLM维护的编译层）                  │
│  Markdown文件目录，按六层框架组织                   │
│  LLM读完原始资料后生成，人工可编辑                  │
│  交叉引用已存在，矛盾已标注，综合已反映所有来源       │
└──────────────────────┬──────────────────────────┘
                       │ 编译
                       ▼
┌─────────────────────────────────────────────────┐
│  Layer 3: era.json knowledge.entries（运行时数据）  │
│  JSON格式，DM Agent运行时读取                      │
│  单一数据源，Wiki是上游，era.json是下游             │
└─────────────────────────────────────────────────┘
```

### 1.2 数据流

```
Raw Sources ──摄入──→ Wiki ──编译──→ era.json
                         ↑                │
                    人工审核/修正      DM Agent运行时只读
                         │
                    增量更新（新资料加入时）
```

**关键原则**：
- **单向数据流**：Raw Sources → Wiki → era.json，不反向
- **Wiki是中间态**：可以人工编辑，但每次从Raw Sources重新编译会覆盖
- **era.json是最终态**：编译输出，DM Agent运行时唯一的知识来源

---

## 二、项目目录结构

### 2.1 与现有结构的集成

在现有 `history-footnote-engine/eras/` 下扩展：

```
history-footnote-engine/
├── src/
│   └── history_footnote/
│       ├── game_loop.py
│       ├── dm_agent.py
│       ├── rule_engine.py
│       ├── validator.py
│       ├── game_memory.py
│       ├── knowledge_base.py
│       └── wiki_compiler/          # 新增：编译器模块
│           ├── __init__.py
│           ├── compiler.py          # 编译主流程
│           ├── schema.py            # JSON Schema定义
│           ├── ingester.py          # Raw Sources摄入
│           └── reviewer.py          # 审核辅助工具
├── eras/
│   ├── _template/
│   │   ├── era.json
│   │   ├── dm_persona.md
│   │   └── wiki/                   # 新增：模板Wiki目录
│   │       ├── schema.md           # 编译规范（Schema层）
│   │       └── _README.md          # 贡献者指南
│   ├── wanli1587/
│   │   ├── era.json                # 编译输出（下游）
│   │   ├── dm_persona.md
│   │   ├── sources/                # 新增：Raw Sources（上游）
│   │   │   ├── 1587_a_year_of_no_significance.md
│   │   │   ├── ming_shi_food_and_money.md
│   │   │   ├── shengze_gazetteer.md
│   │   │   └── sources_index.json  # 来源索引
│   │   └── wiki/                   # 新增：编译层（中间态）
│   │       ├── 01-时间骨架/
│   │       │   ├── 关键年份.md
│   │       │   └── 季节循环.md
│   │       ├── 02-空间舞台/
│   │       │   ├── 盛泽镇.md
│   │       │   └── 交通路线.md
│   │       ├── 03-社会结构/
│   │       │   ├── 权力层级.md
│   │       │   ├── 经济链条.md
│   │       │   └── 信息流动.md
│   │       ├── 04-日常生活/
│   │       │   ├── 物价与银钱.md
│   │       │   ├── 饮食.md
│   │       │   ├── 服饰.md
│   │       │   ├── 住房.md
│   │       │   └── 节庆与信仰.md
│   │       ├── 05-时代张力/
│   │       │   └── 核心矛盾.md
│   │       ├── 06-认知地图/
│   │       │   ├── 话语体系.md
│   │       │   └── 知识边界.md
│   │       └── index.md            # Wiki索引
│   └── jiaozi_song/
│       ├── era.json
│       ├── dm_persona.md
│       ├── sources/
│       └── wiki/
├── tools/
│   ├── validate_era.py
│   └── compile_wiki.py             # 新增：编译CLI工具
└── tests/
```

### 2.2 三个目录的职责

| 目录 | 层级 | 谁写 | 谁读 | 可变性 |
|------|------|------|------|--------|
| `sources/` | Raw Sources | 人类贡献者 | LLM编译器 | 不可变（追加） |
| `wiki/` | Wiki编译层 | LLM生成 + 人类审核修正 | LLM编译器（编译era.json时） | 可编辑 |
| `era.json` | 运行时数据 | 编译器输出 | DM Agent | 编译时覆盖 |

---

## 三、Schema定义

### 3.1 知识条目JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#"，
  "title": "EraKnowledgeEntry"，
  "type": "object"，
  "required": ["id"， "layer"， "title"， "content"， "trigger_keywords"]，
  "properties": {
    "id": {
      "type": "string"，
      "pattern": "^(bg|sc|en|pr)_[a-z][a-z0-9_]*$"，
      "description": "条目ID，前缀对应层级：bg=背景，sc=场景，en=实体，pr=原理"
    }，
    "layer": {
      "type": "string"，
      "enum": ["background"， "scene"， "entity"， "principle"]，
      "description": "知识层级"
    }，
    "title": {
      "type": "string"，
      "maxLength": 30，
      "description": "条目标题，简洁可读"
    }，
    "content": {
      "type": "string"，
      "maxLength": 500，
      "description": "条目内容，DM叙事时引用的核心信息"
    }，
    "trigger_keywords": {
      "type": "array"，
      "items": {"type": "string"}，
      "minItems": 2，
      "maxItems": 8，
      "description": "触发关键词，DM用这些词匹配是否检索此条目"
    }，
    "trigger_scene": {
      "type": "string"，
      "description": "触发场景，玩家在特定场景时自动注入"
    }，
    "related_entries": {
      "type": "array"，
      "items": {"type": "string"}，
      "description": "关联条目ID列表"
    }，
    "source_refs": {
      "type": "array"，
      "items": {
        "type": "object"，
        "properties": {
          "source_id": {"type": "string"}，
          "location": {"type": "string"， "description": "来源中的位置（章节/页码）"}
        }
      }，
      "description": "来源引用，可追溯到Raw Sources"
    }，
    "confidence": {
      "type": "string"，
      "enum": ["high"， "medium"， "low"]，
      "default": "medium"，
      "description": "LLM对内容准确性的置信度"
    }，
    "needs_review": {
      "type": "boolean"，
      "default": true，
      "description": "是否需要人工审核"
    }
  }
}
```

### 3.2 Wiki Markdown规范

每个Wiki页面遵循统一格式：

```markdown
# [标题]

> 层级：[background/scene/entity/principle]
> 对应条目ID：[bg_xxx / sc_xxx / en_xxx / pr_xxx]

## 摘要
[一段话概括，编译时写入content字段]

## 详细内容
[完整信息，编译时用于DM深度参考]

## 触发关键词
- 关键词1
- 关键词2

## 触发场景
[玩家在什么场景下会接触到这些信息]

## 关联条目
- [[关联条目ID]]：关联说明

## 来源
- [来源1]：章节/页码
- [来源2]：章节/页码

## 矛盾标注
[如果不同来源有矛盾，在这里标注]
- 来源A说X，来源B说Y → 待确认
```

### 3.3 sources_index.json 规范

```json
{
  "era_id": "wanli1587"，
  "sources": [
    {
      "id": "src_1587_book"，
      "title": "万历十五年"，
      "author": "黄仁宇"，
      "type": "book"，
      "file": "1587_a_year_of_no_significance.md"，
      "coverage": ["政治结构"， "财政制度"， "道德体系"， "关键人物"]，
      "reliability": "high"
    }，
    {
      "id": "src_ming_shi"，
      "title": "明史·食货志"，
      "author": "张廷玉等"，
      "type": "official_history"，
      "file": "ming_shi_food_and_money.md"，
      "coverage": ["税收"， "货币"， "物价"， "户籍"]，
      "reliability": "high"
    }
  ]
}
```

---

## 四、编译流程

### 4.1 四阶段流程

```
Stage 1: 摄入（Ingest）
  Raw Sources → LLM阅读 → 提取关键信息 → 生成Wiki页面草稿

Stage 2: 编译（Compile）
  Wiki页面 → 按Schema提取 → 生成knowledge.entries JSON

Stage 3: 审核（Review）
  标记needs_review=true的条目 → 人工审核 → 修正/确认

Stage 4: 输出（Export）
  审核通过的条目 → 写入era.json的knowledge.entries
```

### 4.2 Stage 1：摄入

**输入**：sources/目录下的Markdown文件 + sources_index.json

**处理**：

```python
def ingest(source_file: str， schema: Schema， existing_wiki: Wiki) -> WikiPages:
    """
    LLM阅读原始资料，按六层框架提取信息，生成Wiki页面。
    
    关键行为：
    1. 阅读原始资料，识别属于哪个层级的信息
    2. 提取关键事实、数据、因果关系
    3. 整合到现有Wiki中——更新已有页面、创建新页面
    4. 标注新旧信息矛盾
    5. 维护交叉引用
    """
    prompt = f"""
    你是一个历史知识编译器。阅读以下原始资料，按六层框架提取信息，
    生成或更新Wiki页面。
    
    六层框架：
    1. 时间骨架（什么时候）
    2. 空间舞台（在哪里）
    3. 社会结构（谁管谁）
    4. 日常生活（怎么活）
    5. 时代张力（什么在崩）
    6. 认知地图（当时人怎么想）
    
    现有Wiki状态：{existing_wiki.summary()}
    
    原始资料：{source_file}
    
    输出格式：按Wiki Markdown规范生成页面。
    如果新信息与现有Wiki矛盾，在"矛盾标注"部分标出。
    """
    # LLM调用 + 输出解析
```

**输出**：wiki/目录下的Markdown文件

**增量更新**：新资料加入时，LLM不只生成新页面，还更新已有页面——这是LLM Wiki的核心优势。

### 4.3 Stage 2：编译

**输入**：wiki/目录下的Markdown文件

**处理**：

```python
def compile_wiki(wiki_dir: str， schema: Schema) -> list[KnowledgeEntry]:
    """
    将Wiki Markdown页面编译为era.json的knowledge.entries。
    
    关键行为：
    1. 读取每个Wiki页面
    2. 提取摘要 → content字段
    3. 提取触发关键词 → trigger_keywords字段
    4. 提取关联条目 → related_entries字段
    5. 提取来源引用 → source_refs字段
    6. 根据层级前缀生成ID
    7. 标记置信度和审核状态
    """
```

**输出**：knowledge.entries JSON数组

### 4.4 Stage 3：审核

**工具辅助**：

```python
def review_entries(entries: list[KnowledgeEntry]) -> ReviewReport:
    """
    生成审核报告，辅助人工审核。
    
    检查项：
    1. needs_review=true的条目清单
    2. confidence=low的条目清单
    3. 矛盾标注汇总
    4. 缺失层级检查（六层框架是否都有覆盖）
    5. 关联条目完整性（引用的ID是否存在）
    6. 触发关键词去重检查
    """
```

**人工操作**：
- 审核报告标记的条目
- 修正错误、补充细节
- 将needs_review改为false
- 可以直接编辑Wiki Markdown，然后重新编译

### 4.5 Stage 4：输出

```python
def export_to_era_json(entries: list[KnowledgeEntry]， era_json_path: str):
    """
    将审核通过的条目写入era.json。
    
    只写入needs_review=false的条目。
    保留era.json中其他字段不变，只更新knowledge.entries。
    """
    # 读取现有era.json
    # 替换knowledge.entries
    # 写回era.json
```

---

## 五、CLI工具

### 5.1 compile_wiki.py

```bash
# 摄入新资料
python tools/compile_wiki.py ingest \
  --era wanli1587 \
  --source sources/new_paper.md

# 编译Wiki到era.json
python tools/compile_wiki.py compile \
  --era wanli1587 \
  --output eras/wanli1587/era.json

# 生成审核报告
python tools/compile_wiki.py review \
  --era wanli1587

# 全流程：摄入+编译+审核报告
python tools/compile_wiki.py build \
  --era wanli1587
```

### 5.2 输出示例

```
$ python tools/compile_wiki.py build --era wanli1587

[1/4] 摄入 Raw Sources...
  ✓ 读取 3 个来源文件
  ✓ 生成 12 个Wiki页面（新增8个，更新4个）
  ⚠ 发现 2 处矛盾标注

[2/4] 编译 Wiki → knowledge.entries...
  ✓ 编译 42 个知识条目
  ✓ 层级分布：bg=6， sc=12， en=10， pr=14

[3/4] 审核检查...
  ⚠ 7 个条目 needs_review=true
  ⚠ 3 个条目 confidence=low
  ⚠ 2 处矛盾待确认
  ⚠ 第4层（日常生活）覆盖偏薄，建议补充饮食、服饰条目

[4/4] 输出...
  ✓ 35 个已审核条目写入 era.json
  ⚠ 7 个待审核条目未写入（需人工审核后重新编译）
```

---

## 六、开源贡献者工作流

### 6.1 制作新时代包的流程

```
Step 1: 创建时代目录
  cp -r eras/_template eras/tang_anlushan
  编辑 sources/sources_index.json

Step 2: 准备Raw Sources
  把书、论文、方志等资料转为Markdown，放入sources/
  更新sources_index.json

Step 3: 运行编译器
  python tools/compile_wiki.py build --era tang_anlushan
  LLM自动生成Wiki页面和知识条目

Step 4: 审核
  查看审核报告，修正错误
  编辑Wiki Markdown页面
  重新编译

Step 5: 补全其他部分
  编写era.json的world/mechanics/growth部分
  编写dm_persona.md

Step 6: 测试
  python tools/validate_era.py eras/tang_anlushan/era.json
  运行3-5回合原型测试
```

### 6.2 贡献门槛对比

| 步骤 | 无编译器 | 有编译器 |
|------|---------|---------|
| 研究时代 | 4.5-6.5天 | 4.5-6.5天（不变） |
| 编写知识条目 | 2-3天手写40-50条 | 2-3小时LLM生成+4-6小时审核 |
| 质量保证 | 依赖个人知识 | Schema强制+来源追溯+矛盾标注 |
| 总耗时 | 6.5-9.5天 | 5-7天（节省1-3天） |

---

## 七、Phase规划

### Phase 1：最小可用（与引擎原型同步）

- [x] 定义Schema（知识条目JSON Schema + Wiki Markdown规范）
- [ ] 实现compile_wiki.py的compile和review命令
- [ ] 手动创建wanli1587的Wiki目录（从现有25条目反向生成）
- [ ] 验证编译输出与现有era.json一致

**不实现**：ingest命令（Phase 1手动写Wiki，验证编译流程）

### Phase 2：LLM摄入

- [ ] 实现ingest命令
- [ ] 用wanli1587的Raw Sources测试增量摄入
- [ ] 补全日常生活和认知地图条目
- [ ] 验证矛盾标注功能

### Phase 3：开源就绪

- [ ] 完善贡献者文档
- [ ] 制作_template的Wiki模板
- [ ] 用第二个时代包（如安史之乱）端到端验证
- [ ] 发布编译器工具

---

## 八、设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Wiki格式 | Markdown | 人类可读、LLM可写、Git可diff |
| 编译方向 | 单向（Sources→Wiki→era.json） | 避免双向同步的复杂性 |
| 运行时是否查Wiki | Phase 1不查 | 先验证构建流程，运行时只读era.json |
| 来源追溯 | source_refs字段 | 每个条目可追溯到原始资料 |
| 矛盾处理 | 标注不解决 | LLM标注矛盾，人类决定采信哪个 |
| 增量更新 | LLM更新已有页面 | LLM Wiki的核心优势：知识复利 |

---

## 九、信息来源

1. LLM Wiki：用LLM构建个人知识库的新范式 — 三层架构、增量编译、知识复利
2. 从RAG到编译式知识库：LLM Wiki如何构建可生长的AI知识系统 — 编译器模式vs解释器模式
3. LLM Wiki很优雅，但它替代不了RAG — LLM Wiki的适用边界和局限性
4. LLM Wiki架构解析：基于知识关系的知识库构建与RAG对比 — 摄入与查询管线设计
