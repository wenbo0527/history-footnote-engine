# 项目决策日志

> 记录关键架构决策、选型理由、阶段性结论
> 创建时间：2026-07-03

---

## Decision 001 · Agent框架选型 → LangGraph

**日期**：2026-07-03
**状态**：✅ 已确认
**决策者**：用户确认Q1同意

### 背景

历史注脚体验引擎的核心是AI DM Agent。DM不是"被调用的函数"或"等指令-响应"的Reactive Agent，而是**主动引导叙事节奏的Proactive Agent**（参考`DM引导者行为模式`文档）。

DM需要自主执行4种主动行为：
1. **推进节奏**（玩家犹豫/时代张力阈值/历史锚点）
2. **植入认知线索**（玩家探索触发/DM主动埋钩子）
3. **查证史实**（涉及历史人物/玩家行动后果时调Tool查证）
4. **融合叙事**（把上面三种行为在一次叙事输出中自然融合）

### 候选方案评估

| 框架 | 评估 | 关键缺陷 |
|------|------|---------|
| **LangGraph** | ✅✅ 完美匹配 | 学习曲线、生态演进中 |
| **PydanticAI** | ✅ 轻量、支持ReAct | 三阶段建模需手写，生态太新 |
| **原生API** | ⚠️ 可行 | 需手写200行ReAct基础设施+状态管理 |
| **LangChain Agent** | ⚠️ 已deprecated | 官方推荐迁移到LangGraph |
| **CrewAI / AutoGen** | ❌ 不适合 | 多Agent架构，3-5倍token膨胀 |

### 选型理由

**1. 三阶段行为模型 = StateGraph的三个节点**

DM的"态势评估→叙事生成→状态确认"三阶段行为模型（参考设计文档3.1.2），与LangGraph的StateGraph天然对应：

```python
class DMState(TypedDict):
    # 阶段1产出
    current_state: dict
    forced_events: list
    pacing_directives: list
    insight_candidates: list
    # 阶段2产出
    narrative: str
    should_fuse_pacing: bool
    # 阶段3产出
    events_to_save: list
    state_changes: dict
    validation_passed: bool

workflow = StateGraph(DMState)
workflow.add_node("situation_assessment", assess_node)    # 阶段1
workflow.add_node("narrative_fusion", narrative_node)     # 阶段2
workflow.add_node("state_confirmation", confirm_node)     # 阶段3
```

代码量减少约60%。

**2. ToolNode自动处理Tool Calling循环**

DM的5个Tool（get_state / recall_events / check_rules / query_knowledge / save_event）通过LangGraph的`ToolNode`自动注册和调用，框架托管"自主决定调哪个Tool、传什么参数、何时停止"的逻辑。

**3. LangSmith可视化调试**

DM每次Tool调用、每次状态变化都能可视化追踪——调试LLM应用的杀手级特性。

**4. 生态成熟**

2024-2025年快速演进，LangChain官方主推，社区活跃，文档齐全。

### 替代方案（降级路径）

如果LangGraph出现严重问题，降级路径是**PydanticAI**——同样支持ReAct+Tool，但三阶段建模需要手写。

### 依赖清单

```toml
[project.dependencies]
langgraph >= 0.2
langchain-core >= 0.3
langchain-openai >= 0.2  # OpenAI兼容协议，Minimax直接用
pydantic >= 2.0
```

注意：`openai` SDK由`langchain-openai`传递引入，不需要单独加。

### 实施计划

1. 脚手架：`pyproject.toml` + 目录结构
2. Mock LLM：实现LangChain `BaseChatModel`接口，支持Tool Calling模拟
3. 6个核心模块：game_state / rule_engine / game_memory / knowledge_base / dm_agent / game_loop
4. 时代包：从设计文档提取`era.json`和`dm_persona.md`到`eras/wanli1587/`
5. 验证：Mock模式下跑3-5回合，确认历史锚点强制触发、小人物身份边界、节奏推进、insight解锁、NPC主动介入

---

## Decision 002 · 项目脚手架选型 → 原生Python包 + pyproject.toml

**日期**：2026-07-03
**状态**：✅ 用户已确认
**决策者**：用户授权自主决定

### 选型理由

按设计文档v3.0结构（`核心交付物合集v3.0.md`第一章）：
```
history-footnote-engine/
├── pyproject.toml
├── src/history_footnote/   # Python包
├── eras/                   # 时代包
├── tools/                  # 校验工具
└── tests/                  # 测试
```

**优势**：
- `pip install -e .`可编辑安装
- 符合PEP 517/518标准
- 时代包（eras/）与引擎代码解耦，符合"配置驱动"设计
- 便于未来扩展（多时代包、CLI工具、IDE插件）

**项目名**：`history-footnote-engine`
**Python包名**：`history_footnote`

---

## Decision 003 · 开发策略 → Mock优先，跑通再接真API

**日期**：2026-07-03
**状态**：✅ 用户已确认
**决策者**：用户明确要求

### 核心策略

**Phase 1（当前）**：使用Mock LLM跑通全流程
- 不直接调用Minimax API
- Mock实现LangChain `BaseChatModel`接口
- 用预设剧本+关键词匹配模拟DM响应
- 重点验证：主循环、规则引擎、硬约束、状态管理

**Phase 2（验证主循环后）**：接入真API调试Agent
- 切换到Minimax（或Claude/DeepSeek）
- 调试真实LLM的Tool Calling、中文叙事质量、结构化输出

### 理由

- LLM成本/延迟/不稳定性不应阻塞主循环开发
- Mock可以快速迭代规则引擎逻辑
- 真实LLM行为只在Agent调试阶段才需要关注

---

## Decision 004 · 验证标准 → 跑通主循环+硬约束

**日期**：2026-07-03
**状态**：✅ 用户已确认

### 5项验证指标

| # | 验证项 | 通过标准 |
|---|--------|---------|
| 1 | 历史锚点强制触发 | round=1, 8, 11, 12等关键回合，`force_trigger=true`事件必须出现在叙事中 |
| 2 | 小人物身份边界 | 玩家尝试超出`action_boundaries`的行动，叙事中以合理方式拒绝 |
| 3 | 变量变化 | DM的state_changes通过`apply_changes`截断校验后生效 |
| 4 | insight解锁 | 关键词匹配触发`insight_unlocked`出现在`updates`中 |
| 5 | NPC主动介入 | `player_idle_rounds>=2`时，NPC自动找玩家谈话 |

不调优叙事质量（那是Phase 2的事）。

---

## 后续待决策项

| 决策点 | 触发时机 | 待定选项 |
|--------|---------|---------|
| LLM模型最终选型 | Phase 2接真API时 | Minimax / Claude 3.5 Sonnet / DeepSeek V3 |
| 是否启用结构化输出 | 验证主循环后 | 4字段DMResponse vs 自由文本+正则后提取 |
| 存档机制 | 完成主循环后 | 自动存档+3个手动存档位 |
| CLI命令 | 验证后 | run / continue / save / load / restart |

---

## 进度记录

### 2026-07-03
- ✅ 阅读设计文档v1.0、核心交付物合集v3.0
- ✅ 阅读DM引导者行为模式文档
- ✅ 完成可行性+复杂度分析
- ✅ 完成Agent框架选型分析
- ✅ 用户确认所有关键决策
- ✅ 写入项目决策日志 [docs/01-decision-log.md](docs/01-decision-log.md)
- ✅ 初始化项目脚手架（pyproject.toml + 目录结构）
- ✅ 实现Mock LLM + 6个核心模块：
  - `game_state.py`（数据模型+序列化，~120行）
  - `rule_engine.py`（JSON条件求值+状态机，~450行）
  - `game_memory.py`（多路召回，~150行）
  - `knowledge_base.py`（四层条目+关键词匹配，~100行）
  - `dm_agent.py`（LangGraph StateGraph三阶段，~530行）
  - `game_loop.py`（9步主循环，~250行）
  - `mock_llm.py`（LangChain ChatModel接口Mock，~290行）
  - `__main__.py`（CLI入口，~115行）
- ✅ 提取万历十五年时代包到 `eras/wanli1587/`（era.json + dm_persona.md）
- ✅ 时代包校验工具 `tools/validate_era.py`
- ✅ 规则引擎核心功能验证（7/7项通过）
- ✅ 游戏主循环验证（6回合跑通）
- ✅ 所有CLI命令可用（`list-eras`、`run`）

### 验证结果
- 行动边界 ✅（"去皇宫"被拒，"茶馆"允许）
- 强制历史事件 ✅（round 1/8/11分别触发he_01/he_03/he_04）
- 变量触发条件 ✅（tr_tax_spike在tax_burden=8时触发）
- 节奏推进 ✅（pr_idle在player_idle_rounds=3时触发）
- 认知解锁 ✅（6回合内解锁3个insight）
- 变量截断 ✅（max_shift_per_round生效）
- 季节切换 ✅（1月→7月叙事文案正确）
- 价值观偏移 ✅（"按时交税"→duty_vs_freedom=-1）
- 元指令 ✅（/state、/quit正常工作）

### 下一步（Phase 1 → Phase 2）
- ⏳ 接入真实LLM（替换Mock）
- ⏳ 调试真实LLM的Tool Calling+中文叙事
- ⏳ 跑完整50回合验证叙事连贯性
- ⏳ 接入Raw Sources到 sources/（等用户提供MD文档）

### 2026-07-03 Phase 1+存档重开
- ✅ 实现 SaveManager（[src/history_footnote/storage/save_manager.py](src/history_footnote/storage/save_manager.py)，~330行）
  - 会话管理（创建/查找/列出/删除）
  - 4个存档位（auto + slot1/2/3）
  - 自动存档（每回合）+ 手动存档
  - 元信息追踪（meta.json）
- ✅ GameLoop集成存档
  - 每回合自动存档到 auto.json
  - 游戏中指令 /save [slot] /load [slot] /state /help
  - 从存档恢复完整state（变量/事件/认知/价值观/NPC关系）
  - 同步event_log到state
- ✅ CLI 5个新命令
  - `run` - 新游戏
  - `continue` - 继续最近一次
  - `load <session_id> --slot <slot>` - 加载指定slot
  - `list-saves [--era]` - 列出存档
  - `delete-save <session_id>` - 删除整个session
  - `restart <era_id>` - 同身份重开
- ✅ 存档重开测试 [scripts/test_save_load.py](scripts/test_save_load.py)（5/5项通过）
- ✅ 真实CLI流程验证（run→save→list-saves→continue→load slot1→delete-save→restart）

### 2026-07-03 Wiki集成
- ✅ 知识条目扩展到 46条（+21条六层框架条目：时间骨架+空间舞台+社会结构+日常生活+时代张力+认知地图）
- ✅ 新增 era.json.knowledge.narrative_snippets 字段（16条小说片段）
- ✅ KnowledgeBase.query_snippets() + detect_scene()
- ✅ DM Agent新增 query_narrative_snippets Tool（支持player_gender过滤）
- ✅ Mock自动按场景调Tool并融合snippet到叙事
- ✅ 真实CLI验证：《醒世恒言》盛泽丝市描写出现在叙事中

### 2026-07-03 角色创建
- ✅ era.json.player_identities 多身份配置（6个：weaving/scholar/merchant × male/female）
- ✅ CLI问询：Q1性别 + Q2身份
- ✅ GameState.selected_identity + player_gender
- ✅ 规则引擎按身份过滤行动边界
- ✅ narrative_snippets.target_gender 过滤
- ✅ 存档恢复身份
- ✅ 动态开场白（不同身份显示不同描述）
- ✅ _semantic_match 滑动窗口bug修复（"科举考场" vs "科举考试"）

### 2026-07-03 LLM Provider层 + 身份切换
- ✅ 多provider架构 [src/history_footnote/llm_providers.py](src/history_footnote/llm_providers.py)
  - mock / openai / anthropic / minimax-anthropic / minimax-openai / custom
- ✅ CLI `--provider` 参数
- ✅ `list-providers` 命令
- ✅ era.json.identity_switch_offers 配置（4个：weaving→merchant/scholar × male/female）
- ✅ DM Agent.offer_identity_switch Tool（带性别一致性校验）
- ✅ GameLoop /accept /decline /offers 元指令
- ✅ 7/7项身份切换测试通过
- ✅ `.env` + `.gitignore` 安全配置（API Key不入库）

### 2026-07-03 Minimax LLM真实接入（Anthropic兼容协议）
- ✅ 模型：MiniMax-M3（订阅Key）
- ✅ Base URL：https://api.minimaxi.com/anthropic
- ✅ 配置：python-dotenv + .env 文件
- ✅ 验证1：直接anthropic SDK ✅
- ✅ 验证2：langchain-anthropic ✅
- ✅ 验证3：Tool Calling（get_weather调Tool成功）✅
- ✅ 验证4：端到端3回合（1313字中文叙事，含明代日常细节+真实NPC互动+时代元素）✅

### 关键决策记录
| 决策 | 选择 | 理由 |
|------|------|------|
| Minimax协议 | Anthropic兼容 | 与Claude生态一致；function calling支持稳定 |
| API Key管理 | .env文件+python-dotenv | 不入库；可轮换；跨平台 |
| 身份切换触发 | 条件满足+LLM判断 | 比硬规则灵活，符合"细节代替概括" |
| 性别锁定 | 跨性别切换硬件拒绝 | 符合明代社会现实，避免穿帮 |
| Provider架构 | 6种provider+工厂方法 | 未来可平滑替换；测试与生产解耦 |

### Phase 2 待办
- ⏳ 调试真实LLM的insight解锁output格式（当前0个解锁，预期至少1-2个）
- ⏳ 跑完整50回合验证叙事连贯性

### 2026-07-03 全部Wiki写入完成（精简版）
- ✅ 支线路径v2.0写入：8条entries（科举阶梯/秀才特权/灰色生态/打行/西门庆路径/妇健之风/才女路线/三姑六婆）
- ✅ 支线路径v2.0写入：6条snippets（范进中举/徐渭/温秀才/王婆/薛嫂/叶绍袁家族）
- ✅ 离乡路线v1.0写入：6条entries（人口流动/隆庆开关/月港/南洋/运河/募兵）
- ✅ 离乡路线v1.0写入：5条snippets（月港丝绸/吕宋白银/日本走私/运河艰险/参军克扣）
- ✅ 数据规模：60 entries + 27 snippets = 63KB（精简后可控）
- ✅ validate_era.py升级支持v1.1+多身份
- ✅ 全部6个测试+era校验通过

### 关键评估：Wiki写入策略
- ✅ 优点：所有"细节弹药"就位，DM可调用
- ⚠️ 风险：上下文窗口可能撑爆——已通过精简控制（平均171字符/条）
- 🔄 后续：进入向量数据库（Phase 2）解决大规模检索问题

### 用户反馈（重要架构挑战）
- ⚠️ 当前架构偏线性：DM的Tool调用是确定性的（按scene+keyword查top1）
- ⚠️ 用户期望：DND类型游戏，需要随机性、多样化的反馈
- ⚠️ 用户洞察：Wiki应该是"分段、按需触发、检索"，LLM完善故事，最后给用户
- 🔄 这指向下一步需要重新设计叙事生成机制

### 2026-07-03 DND化改造（MVP三件套）
- ✅ DiceEngine [src/history_footnote/dice_engine.py](src/history_footnote/dice_engine.py) - 支持d20/2d6+3/优势/劣势/DC判定/加权选择/概率
- ✅ 随机事件表 - era.json.world.random_events（6个事件：市集/茶馆/牙行/桑田/突遇/家庭）
- ✅ story_segments重组 - era.json.knowledge.story_segments（7个场景，32条片段）
- ✅ DM Agent新增3个Tool - query_story_segments / get_random_segment / roll_dice
- ✅ KnowledgeBase - 新增query_segments/get_random_segment方法
- ✅ GameLoop集成DiceEngine - 每回合自动_check_random_events
- ✅ Mock LLM - 40%概率调get_random_segment（增加随机性）
- ✅ 验证测试 scripts/test_dnd_randomness.py - 5次同一输入得到3种不同叙事

### 关键决策：DND叙事随机性
- 不用LLM的"温度参数"调随机性（黑盒、不可控）
- 用DiceEngine+随机事件表+story_segments的**显式随机化**
- LLM最终自由组合片段生成故事（创造性的部分留给LLM）

### Phase 2 待办（重新排序）
- ⏳ 调试真实LLM的insight解锁output格式
- ⏳ 跑完整50回合验证叙事连贯性
- ⏳ 进入向量数据库（ChromaDB）解决大规模检索
- ⏳ NPC关系动态系统（玩家与NPC的友谊/敌意累积）
- ⏳ 更多场景的story_segments（闺阁/县衙/运河/码头等）

### 2026-07-03 50回合长流程测试（最终结果）
- ✅ 测试cases：weaving_male/weaving_female各50回合 + 终极覆盖率测试
- ✅ Insight解锁率：36% → 57% → 79% → 93% → **100%**（14/14）
- ✅ 叙事独特性：45/45（100%）
- ✅ 触发事件：13条 historical_events全部按设计触发
- ✅ 存档验证：每回合自动存档正确
- ✅ 异常次数：0

### 关键Bug修复（50回合测试中发现）
- **insight trigger_keywords太严格**：原配置5个关键词，玩家自然输入难命中 → +66个同义词
- **narrative_guided无触发路径**：原需要dm_guided=True，但没人传 → 改成"前置+关键词"自动触发
- **narrative_hint关键词提取太短**：原[\u4e00-\u9fa5]{2,4}截断了4字以上关键词 → 改为不限长度
- **trigger_keywords不被narrative_guided使用**：原本只匹配topic → 改为优先trigger_keywords
- **ins_decline_signal触发太晚**：导致ins_grand_failure链式未触发 → 扩充关键词包含"闹事/贴出告示"等

### 最终项目状态（v1.2+）
| 维度 | 数值 |
|------|------|
| Wiki条目 | 69 entries + 31 snippets + 32 story_segments |
| 随机事件 | 6个事件表 |
| Insight | 14条全部解锁机制验证 |
| 身份 | 6个身份 + 4个切换offer |
| LLM Provider | 6种（mock/openai/anthropic/minimax-anthropic/minimax-openai/custom）|
| 测试脚本 | 8个（全部通过）|

---

## Decision 002 · LLM Temperature 控制（v2.7）→ 分用途分级

**日期**：2026-07-09
**状态**：✅ 已实施
**影响范围**：所有 LLM 调用点

### 背景

v2.5 引入全局 seed 机制承诺"同 seed 同开局"，但 v2.6 之前 LLM 调用没设 temperature → 模型默认 0.7 → 同 seed 输出**叙事文字不同**。

玩家分享 seed 体验"开局**走向**一样但**文字**不同"——失去"重玩对照"价值。

### 决策

引入 `LLM_PURPOSE_TEMPERATURE` 字典 + `make_llm_for_purpose()` 工厂：

| 用途 | temperature | 理由 |
|---|---|---|
| `dm` / `voice_options` / `internal_voice` | **0.0** | 完全可重放 |
| `wiki` / `recap` / `character` | 0.3 | 略变（避免"老套"）|

### 关键 insight

- 简单 "全局 temperature=0" 会让叙事太呆板
- 但**主流程**（DM/voice）必须 =0 才能保证可重放
- **创意类**（wiki/recap）可略变 0.3 —— 不影响重放价值

### 候选方案

| 方案 | 价值 | 缺陷 |
|---|---|---|
| 全局 temperature=0 | 简单 | 叙事呆板 |
| 全局 temperature=0.7 | 灵活 | 不可重放 |
| **分用途分级**（选）| 重放 + 灵活 | 实现复杂一点 |

### 实施细节

- 4 处 LLM 调用点全部加 `purpose` 参数
- `make_llm_for_purpose(purpose, ...)` 工厂
- `extra_kwargs` 可覆盖默认 temperature
- 默认 fallback = 0（向后兼容）

### 验证

L9 测试：同 seed × 同操作 → 100% 相同叙事（5 个测试通过）

---

## Decision 003 · 测试金字塔（v2.7）→ 5 层覆盖

**日期**：2026-07-09
**状态**：✅ 已实施
**影响范围**：测试基础设施

### 背景

v2.5-v2.6 累计 5 个 commit（全局 seed + 命运卡 + 文字地图 + 应急弹出）但**没完整测试套件**——无法验证质量。

### 决策

5 层测试金字塔：

| 层 | 数量 | 调 LLM | 目标 |
|---|---|---|---|
| L1 整合 | 12 | ❌ | 状态/路由/handler |
| L2 E2E mock | 5 | mock | 完整 1 局流程 |
| L3 E2E 真实 LLM | 3 | ✅ DeepSeek | 真实 LLM 输出 |
| L4 边界 | 8 | ❌ | 异常输入/性能 |
| L9 重放 | 5 | ❌ | 验证 v2.5 重玩机制 |
| temperature | 5 | ❌ | v2.7 温度控制 |
| 前端 vitest | 6 | ❌ | mapper 字段透传 |

### 关键 insight

- 5 层**互补**：
  - L1/L4 快速反馈（<1 分钟）
  - L2/L9 流程跑通（<1 分钟）
  - L3 真实质量（3-5 分钟）
- 测试发现**5 个隐藏 BUG**（mapper 漏字段等）
- 端到端测试**永远不嫌多**——上版 commit 修了后端，前端仍坏

### 实施细节

- `tests/run_all_v26.py` 一键跑
- 每个测试独立 fail 容易定位
- 前端用 vitest（项目已有）

---

## Decision 004 · 命运卡"感知闭环"（v2.5-v2.7）→ 双向可见

**日期**：2026-07-09
**状态**：✅ 已实施
**影响范围**：命运卡系统

### 背景

v2.5 引入命运卡，但 DM 不知道玩家用过 → 叙事不呼应。
玩家也不知道卡影响了谁 → 命运卡变成"一次性"装饰。

### 决策

**双向感知**：
- **DM 感知**（v2.6.1）：`🎴 命运已用` 段注入 prompt
- **玩家感知**（v2.6.2）：人物档案加 `🎴 命运影响` 段

### 关键 insight

- 命运卡 = 战略资源（不是装饰）—— 必须**双方都看见**
- 否则玩家"用卡 = 失去卡"（负反馈）→ 不用卡
- 双向反馈 = 玩家愿意主动用卡

### 候选方案

| 方案 | 价值 | 缺陷 |
|---|---|---|
| 命运卡是装饰 | 简单 | 玩家不愿用 |
| 单向（DM 知道）| 叙事呼应 | 玩家不知道影响 |
| **双向**（选）| 双方都有反馈 | 实现复杂 |

### 实施

- v2.6.1：system_base.md 加 `🎴 命运已用规则`
- v2.6.2：CharacterWikiModal 加 `🎴 命运影响段`
- 验证：DM 输出含"你之前用的卡" + 玩家看见"卡影响了沈氏 +30"

---

## Decision 005 · CharCard 命运卡预览（v2.7）→ 玩家一打开就看到

**日期**：2026-07-09
**状态**：✅ 已实施

### 背景

命运卡开局抽 5 张，但只在 `FateHandPanel`（侧栏折叠）显示——玩家要"找"才能看到。

### 决策

主角卡（CharCard）下方直接加 `🎴 我的命运` 段：
- 前 3 张未用的卡（chip 卡片）
- 已用的卡（灰度 + 仅图标）
- 计数器 `N / 5 未用`

### 实施

3 个 hidden BUG 修复（3 commit）：
- `584dfa6` format_state 透传
- `fa8fdbf` mapBackendState put
- `ab3cbf7` session 创建后立即 save_state

### 收益

- 玩家**一打开**就看到自己的卡
- 命运用卡的频次提升（最关键的 UX 改进）

---

## Decision 006 · 现代 CSS（v2.7）→ clamp + container queries

**日期**：2026-07-09
**状态**：✅ 已实施

### 决策

- `grid-template-columns: clamp(220px, 22vw, 280px)` 让 sidebar 跨设备平滑
- `container-type: inline-size` 让 CharCard 知道自己的宽度
- `@container char-card (max-width: 260px)` 极窄时隐藏名字

### 候选

| 方案 | 价值 | 缺陷 |
|---|---|---|
| 4-5 个 media query 散落 | 简单 | 难维护 |
| **clamp + container**（选）| 组件级响应 | 学习曲线 |

### 收益

- 命运卡 chip 永远适配（不论 sidebar 怎么变）
- 移动端自动隐藏文字（节省空间）
- 真正"零 media query 布局"
