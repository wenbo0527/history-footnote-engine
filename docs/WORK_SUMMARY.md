# 历史注脚体验引擎：工作总结 v1.6+

> 日期：2026-07-04
> 范围：从 v1.0 产品文档到 v1.6+ 完整实现的全部演进
> 重点：**Agent 架构 + 知识库配置**

---

## 🎯 项目最终状态

- **版本**：v1.6+
- **代码行数**：~5000+
- **模块数**：14 个核心模块
- **完成度**：约 90%
- **下一阶段**：P0 后校验 + 重试 + 兜底（本会话剩余任务）

---

## 一、Agent 架构演进（重点）

### 1.1 版本时间线

| 版本 | 关键变化 | 解决问题 |
|---|---|---|
| v1.0 | 单次 LLM 调用 + Function Calling | 原型最小化 |
| v1.1+ | 三阶段（态势/叙事/确认） | DM 主动行为 |
| v1.3+ | 行动点系统 | 节奏控制 |
| **v1.4+** | **+ 8 SKILL 编排层** | DM 自主判断变多，但确定性逻辑不稳 |
| **v1.5+** | **+ 4 阶段模型 + voice_options + describe** | DM 更聚焦，玩家体验提升 |
| **v1.6+** | **+ Tab 式 UX** | 渐进式用户自由度 |

### 1.2 8 SKILL 体系（v1.4+ 核心创新）

灵感来自三份调研文档：
- [调研成果汇报.md](调研成果汇报.md) — Disco Elysium 调研
- [AI DM SKILL体系整合.md](历史注脚体验引擎：AI DM SKILL体系整合.md) — 8 SKILL 设计基础
- [AI DM节奏控制设计.md](历史注脚体验引擎：AI DM节奏控制设计——借鉴剧本杀与DND人类DM.md) — 4 时间模式

| SKILL | 借鉴来源 | 实现位置 |
|---|---|---|
| **SKILL-1 读场判断** | 剧本杀 DM 控场 | dm_skills.py: skill_1_assess_scene |
| **SKILL-2 节奏控制** | DND 4 时间模式（Robin D. Laws） | dm_skills.py: skill_2_decide_pacing |
| **SKILL-3 线索投放** | 剧本杀线索发放技巧 | dm_skills.py: skill_3_plan_lead |
| **SKILL-4 史实锚定** | 三层操作（铺垫/触发/应对） | dm_skills.py: skill_4_anchor_history |
| **SKILL-5 价值观发声** | DE 技能即性格（24 声音） | dm_skills.py: skill_5_activate_voices |
| **SKILL-6 失败叙事化** | DE 失败也是故事 | dm_skills.py: skill_6_handle_failure |
| **SKILL-7 三层裁判** | 三层分类法（铁律/可然/自由） | dm_skills.py: skill_7_three_layer_verdict |
| **SKILL-8 认知框架锁定** | DE 思想内阁 | dm_skills.py: skill_8_lock_cognitive_frame |

### 1.3 4 阶段行为模型（v1.5+）

```
阶段 0: 8 SKILL 编排（确定性逻辑归代码）
   ↓ 输出 DMContext + skill_directive 文本

阶段 1: 态势评估（Reason about Situation）
   → DM 自主决定调用哪些 Tool

阶段 2: 叙事生成（Generate Narrative）
   → 必须输出 voice_options（2-4 个 DE 风格内在声音选项）
   → 输出 intent_type（action/inquire/describe/voice）

阶段 3: 状态确认（Confirm & Save）
   → 保存事件到记忆 + voice_options 持久化
```

### 1.4 Agent 关键文件改动

| 文件 | 关键改动 |
|---|---|
| `dm_agent.py` | + `skill_orchestration_node`；+ 4 阶段模型；+ voice_options/intent_type schema |
| `dm_skills.py` | 从 0 到 1000+ 行；8 个 SKILL + 数据结构 + `_detect_intent_type` |
| `game_loop.py` | 集成 8 SKILL；state_ref 同步到 GameState；action_points 差异化 |
| `mock_llm.py` | Phase 1 模拟用 |

---

## 二、知识库演进（重点）

### 2.1 架构变化

| 版本 | era.json 字段 | 知识库层 | 检索方式 |
|---|---|---|---|
| v1.0 | `historical_events`, `insight_tree` | background | 关键词匹配 |
| **v1.4+** | +5 个新字段（见下表） | background + search_by_text | 关键词 + 派生 |
| v2.0（待补） | scene/entity/principle 三层 | 待实现 | 待实现 |

### 2.2 era.json v1.4+ 新增字段

| 字段 | 数量 | 作用 | SKILL |
|---|---|---|---|
| `world.pacing_anchors` | 6 | 史实锚点（春税/倭寇/丝价崩等）+ 时间模式 | SKILL-4 |
| `world.failure_mappings` | 8 种 | 失败 → 新故事转化 | SKILL-6 |
| `world.cognitive_frames` | 5 | 路线 → 信息过滤（科举/经营/出家/抗税/织户） | SKILL-8 |
| `world.voices` | 6 | 内在声音（算盘声/读书人的本分等） | SKILL-5 |
| `player_identities[].action_points_max` | 6 身份 | 行动点差异化（织户 3 / 商人 4 / 读书 2） | 行动点系统 |

### 2.3 字段路径修复（重要 bug fix）

**Bug**：很多 SKILL 函数用 `era_config.get("xxx")`，但实际字段在 `era_config["world"]["xxx"]`。修复了 6 处字段路径：
- `_detect_anchors_near`
- `skill_4_anchor_history`
- `skill_5_activate_voices`
- `skill_6_handle_failure`
- `skill_7_three_layer_verdict`
- `skill_8_lock_cognitive_frame`

修复方式：`era_config.get("world", {}).get("pacing_anchors", []) or era_config.get("pacing_anchors", [])`

### 2.4 4 层 vs 实际实现

| 层 | 文档要求 | 实际实现 | 状态 |
|---|---|---|---|
| background | ✅ | ✅ `get_background()` | 100% |
| scene | ✅ | ❌ | 缺失 |
| entity | ✅ | ❌ | 缺失 |
| principle | ✅ | ⚠️ `search_by_text` 部分 | 部分 |

### 2.5 知识库相关文件

| 文件 | 行数 | 状态 |
|---|---|---|
| `knowledge_base.py` | ~150 | ⚠️ 60%（仅 background + search_by_text） |
| `eras/wanli1587/era.json` | ~4800 | ✅ 含 v1.4+ 所有字段 |
| `eras/wanli1587/dm_persona.md` | ~250 | ✅ 含 8 SKILL 章节 |

---

## 三、遇到的问题与解决方案

### 🔴 P0 严重问题（5 个）— 已修

| # | 问题 | 解决方案 |
|---|---|---|
| 1 | **开屏循环**（`renderWizard() → attachWizardHandlers → generateCharacter → renderWizard()`） | 4 步修复：generateCharacter 不再调 renderWizard()；attachWizardHandlers 用 fire-and-forget；step 2 局部重渲染；INDEX_HTML 加版本标记 |
| 2 | **`/api/start` ValueError: not enough values to unpack** | `make_dm_nodes` return 改返回 5 个值 |
| 3 | **DM 人设完全没用** | 后端接收 character → GameLoop 注入 → _print_opening 优先用 custom_character |
| 4 | **开局没 voice_options** | appendOpeningVoiceOptions 渲染 3 个预定义选项 |
| 5 | **pacing_anchors 与 historical_events 重复 + 重复触发** | 合并机制（custom + 派生）；triggered_events 过滤 |

### 🟡 P1 中等问题（10 个）— 已修

1. web 位置不映射到 identity → 6 位置→6 identity 表
2. SKILL-8 route_tendency 字段不存在 → GameState 加 + dm_agent 同步
3. action_points_max 未按身份差异化 → 织户 3/商人 4/读书 2
4. dm_skills 跑两次 → 只跑一次 + 转 dict
5. voice_options 未持久化 → GameState.last_voice_options + _format_state 暴露
6. describe 来源混乱 → 优先规则判定
7. identity 死代码 → 删除
8. voice_option 双击防护 → _submitting 锁
9. DOM 顺序错误 → insertBefore(input-area)
10. intent_text 空字符串防护 → trim + 早返

### 🟢 P2 小问题（4 个）— 已修或接受

1. ROUTE_KEYWORDS 词表窄 → 扩充到 120+ 关键词
2. scripts/ 30 个过期脚本 → 归档到 _archive/
3. smoke test print 错位 → 接受
4. 未使用 imports → 接受

---

## 四、UX 关键改进（v1.5+ → v1.6+）

### 4.1 8 步初始化向导

1. 选择时代（wanli1587）
2. 世界画卷（LLM 渲染）
3. 选择性别
4. 选择位置（6 个盛泽镇地点）
5. 描述身份（可选）
6. 描述期望生活（可选）
7. AI 生成人设（LLM 输出 name/hometown/family/background/voices/skills/opening）
8. 确认 → 开始游戏

### 4.2 DE 风格内在声音选项

```
🎭 你脑海中的声音——选择按哪个行动
[算盘声] [读书人的本分] [做人要有骨气]
[✍️ 其他...]   ← Tab 式：斜体、半透明
```

### 4.3 Describe 类型

| 输入 | intent_type | 行动点 |
|---|---|---|
| "我在织机前织布" | action | ✅ |
| "我去看看窗外" | inquire | ❌ |
| "我所在的盛泽镇是..." | **describe** | ❌ |
| "我是从福建逃难来的..." | **describe** | ❌ |

### 4.4 Tab 式 UX（v1.6+）

- 之前：选项 + 自由输入按钮 + 文本框常驻并列
- 现在：选项为主，「其他...」按钮（斜体/半透明），点后切换到自由输入 Tab，可「← 返回选项」

---

## 五、文档演进

| 文档 | 状态 |
|---|---|
| [完整产品设计文档 v1.0.md](历史注脚体验引擎：完整产品设计文档 v1.0.md) | 已归档（v1.0 设计） |
| [完整产品设计文档 v2.0.md](历史注脚体验引擎：完整产品设计文档 v2.0.md) | ✅ 反映 v1.5+ 实际实现 |
| [调研成果汇报.md](调研成果汇报.md) | Disco Elysium 调研（8 SKILL 灵感） |
| [AI DM SKILL体系整合.md](历史注脚体验引擎：AI DM SKILL体系整合.md) | 8 SKILL 设计基础 |
| [AI DM节奏控制设计.md](历史注脚体验引擎：AI DM节奏控制设计——借鉴剧本杀与DND人类DM.md) | 4 时间模式基础 |

---

## 六、测试验证

| 测试 | 通过率 | 关键指标 |
|---|---|---|
| 8 SKILL 烟雾测试 | ✅ 6/6 场景全过 | 8 SKILL 全部验证 |
| 意图识别单元测试 | ✅ 11/12（92%）| describe/inquire/action 分类 |
| 路线倾向识别 | ✅ 8/8 | 6 个路线全覆盖 |
| 5 回合真实 LLM | ✅ 全跑通 | 8 SKILL 全部触发；叙事 231-825 字符 |
| 8 步向导 character 传递 | ✅ 已验证 | 沈岐年人设正确传到开局白 |
| Web HTTP 200 | ✅ | 服务稳定运行 |

---

## 七、待补做（v2.0 文档标记）

### P0（关键安全网）— **本会话正在补做**
- ❌ `post_validate`（铁律校验 + 事件矛盾检查）
- ❌ `regenerate`（重试机制，MAX_RETRY=2）
- ❌ `generate_safe_narrative`（2 次重试失败后模板化兜底）

### P1（完整性）
- ⚠️ 知识库 scene/entity/principle 三层（仅 60%）
- ⚠️ `finale_templates` 配置（缺失）
- ⚠️ NPC 关系代价交换实际计算（仅占位）

### P2（增强）
- ⚠️ Dice Engine 接入 DM 主循环
- ⚠️ 第二个时代包验证（仅 wanli1587）

---

## 八、产出文件清单

### 核心代码（v1.6+）

| 文件 | 行数 | 说明 |
|---|---|---|
| `dm_agent.py` | ~1100 | Agent 主脑 |
| `dm_skills.py` | ~1000 | 8 SKILL 编排 |
| `rule_engine.py` | ~600 | 9 个方法 |
| `knowledge_base.py` | ~150 | 60% 实现 |
| `game_state.py` | ~250 | GameState dataclass |
| `game_loop.py` | ~450 | 游戏主循环 |
| `game_memory.py` | ~150 | 三层记忆 |
| `dice_engine.py` | ~200 | DND 风格掷骰 |
| `mock_llm.py` | ~200 | Phase 1 模拟 LLM |
| `character_generator.py` | ~250 | LLM 人设生成 |
| `llm_providers.py` | ~200 | LLM 适配层 |
| `web_server.py` | ~1500 | Web 服务 + 8 步向导 |
| `__main__.py` | ~200 | CLI 入口 |

### 时代包配置

| 文件 | 行数 | 说明 |
|---|---|---|
| `eras/wanli1587/era.json` | ~4800 | 万历十五年配置 |
| `eras/wanli1587/dm_persona.md` | ~250 | DM 人格 + 8 SKILL 章节 |

### 测试脚本（保留）

| 脚本 | 用途 |
|---|---|
| `add_action_points_max.py` | 一次性 era.json 配置 |
| `add_skills_to_era.py` | 一次性 era.json 配置 |
| `smoke_test_8_skills.py` | 8 SKILL 验证 |
| `test_8_skills_real.py` | 5 回合真实 LLM 验证 |
| `test_intent_detect.py` | 意图识别单元测试 |

---

## 九、最大的几个产出

| 产出 | 价值 |
|---|---|
| **8 SKILL 编排层** | 把"DM 自主判断"改为"代码确定性计算 + DM 创意生成"，DM 输出稳定可靠 |
| **DE 风格 voice_options** | 移植 DE 核心玩法到历史体验引擎 |
| **8 步初始化向导 + 位置锁定** | 玩家深度定制角色，沉浸感大幅提升 |
| **describe 类型** | 区分玩家"做事" vs "描述"，避免无意义消耗 |
| **Tab 式 UX** | 选项为主、自由为辅，降低决策门槛 |
| **产品文档 v2.0** | 全面反映实际实现，标记缺失项 |