# 历史注脚体验引擎 (History Footnote Engine)

> **AI当DM，你当历史里的小人物。** 通过对话体验一个历史时期，历史走势不可改，但你的选择路径完全开放。

## 🎉 v1.6.1 已发布

最新版本（2026-07-04）完成了：
- ✅ **后校验 + 重试 + 兜底**（v1.0 文档要求的 P0 缺失项）
- ✅ **5 层并发架构**（支持数十个玩家同时在线）
- ✅ **KV 缓存集成**（节省 70-98% tokens）
- ✅ **Tab 式 UX**（选项 + 自由输入渐进式选择）
- ✅ **完整测试覆盖**（30+ 单元测试 + 5 玩家并发压力测试）

详见 [CHANGELOG.md](CHANGELOG.md) 和 [完整产品设计文档 v3.0](docs/历史注脚体验引擎：完整产品设计文档 v3.0.md)。

---

## 🎯 核心特性

### 玩法层

- **配置驱动**：换一份 `era.json` + `dm_persona.md` 就能切换到新历史时期
- **DE 风格选项**：每回合 2-4 个内在声音选项（Disco Elysium 风格）
- **8 SKILL 编排**：确定性逻辑归代码，DM 只做创意性判断
- **行动点系统**：每月 3-4 个行动点，"过日子"般的沉浸感
- **8 步初始化向导**：玩家深度定制角色（时代→世界→性别→位置→身份→生活→人设→开始）
- **位置锁定**：6 个盛泽镇地点 → 6 个 identity 映射

### 工程层

- **单 Agent + 13 Tool**：LLM 编排层最小化
- **后校验 + 重试 + 兜底**：5 层校验，2 次重试，模板兜底（不卡死）
- **5 层并发**：进程级（gunicorn）+ 线程级 + 会话级 + LLM 级 + 持久化级
- **KV 缓存**：System Prompt 加 `cache_control`，节省 70-98% input tokens
- **三阶段行为模型**：态势评估 → 叙事生成 → 状态确认

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/history-footnote-engine.git
cd history-footnote-engine

# 安装依赖
pip install -e ".[dev]"

# 配置 .env（必填）
cp .env.example .env
# 编辑 .env，填入 MINIMAX_API_KEY
```

### 启动 Web 服务

```bash
# 单进程模式（开发）
python -m history_footnote.web_server --port 8765

# 多进程模式（生产）
gunicorn history_footnote.web_server:app \
  --workers 4 \
  --threads 2 \
  --bind 0.0.0.0:8765
```

访问 **http://localhost:8765/** 开始游戏。

### CLI 模式（终端）

```bash
# 跑万历十五年（Mock 模式，无需 API Key）
python -m history_footnote run wanli1587

# 列出可用时代包
python -m history_footnote list-eras

# 验证时代包配置
python tools/validate_era.py eras/wanli1587/era.json
```

### 单元测试

```bash
# 后校验
python scripts/test_post_validator.py

# 并发
python scripts/test_concurrency.py

# KV 缓存
python scripts/test_kv_cache.py

# 意图识别
python scripts/test_intent_detect.py

# 8 SKILL 烟雾测试
python scripts/smoke_test_8_skills.py

# 5 回合真实 LLM
python scripts/test_8_skills_real.py

# 5 玩家并发压力测试（需先启动 web server）
python scripts/test_concurrent_real.py
```

---

## 📁 项目结构

```
history-footnote-engine/
├── CHANGELOG.md                 # 版本变更记录
├── README.md                    # 本文档
├── pyproject.toml
├── docs/                        # 项目文档
│   ├── 历史注脚体验引擎：完整产品设计文档 v3.0.md   ← 当前主文档
│   ├── 历史注脚体验引擎：完整产品设计文档 v2.0.md   ← 历史版本
│   ├── 历史注脚体验引擎：完整产品设计文档 v1.0.md   ← 历史版本
│   ├── WORK_SUMMARY.md          # v1.6+ 工作总结
│   ├── 调研成果汇报.md           # Disco Elysium 调研
│   ├── AI DM SKILL体系整合.md     # 8 SKILL 设计
│   └── AI DM节奏控制设计——借鉴剧本杀与DND人类DM.md
├── src/
│   └── history_footnote/        # 引擎代码（17 个模块）
│       ├── __main__.py          # CLI 入口
│       ├── game_loop.py         # 游戏主循环 + 后校验重试
│       ├── dm_agent.py          # DM Agent（LangGraph StateGraph）
│       ├── dm_skills.py         # 8 SKILL 编排（v1.4+）
│       ├── rule_engine.py       # 规则引擎（9 个方法）
│       ├── game_memory.py       # 三层记忆
│       ├── game_state.py        # GameState 数据模型
│       ├── knowledge_base.py    # 知识库（60% 实现）
│       ├── post_validator.py    # 🆕 v1.6 后校验器
│       ├── concurrency.py       # 🆕 v1.6 5 层并发
│       ├── kv_cache.py          # 🆕 v1.6 KV 缓存
│       ├── web_server.py        # Web 服务 + 8 步向导 + Tab 式 UX
│       ├── web_server_concurrent.py  # 🆕 v1.6 并发 web 入口
│       ├── llm_providers.py     # LLM 适配层（Minimax/OpenAI/Anthropic）
│       ├── mock_llm.py          # Mock LLM（Phase 1）
│       ├── dice_engine.py       # DND 风格掷骰
│       ├── character_generator.py  # LLM 人设生成
│       └── storage/
│           └── save_manager.py
├── eras/                        # 时代包
│   ├── _template/               # 新时代包模板
│   └── wanli1587/               # 万历十五年（首个 Demo）
│       ├── era.json             # ~4800 行配置
│       └── dm_persona.md        # DM 人格 + 8 SKILL 章节
├── scripts/                     # 测试 + 工具脚本
│   ├── test_post_validator.py   # 后校验测试
│   ├── test_concurrency.py      # 并发测试
│   ├── test_kv_cache.py         # KV 缓存测试
│   ├── test_concurrent_real.py  # 5 玩家并发压力测试
│   ├── test_intent_detect.py    # 意图识别测试
│   ├── test_8_skills_real.py    # 5 回合真实 LLM 测试
│   ├── smoke_test_8_skills.py   # 8 SKILL 烟雾测试
│   └── _archive/                # 归档的过期脚本
└── tools/
    └── validate_era.py          # 时代包校验工具
```

---

## 🏗️ 核心架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Web Server (HTTP API)                              │
│   Layer 1: 进程级（多进程 gunicorn，扩展）                              │
│   Layer 2: 线程级（ThreadingHTTPServer + ThreadPoolExecutor）         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│              DM Agent（唯一的 LLM 调用点）                              │
│   System Prompt = DM 人格 + 时代配置 + 8 SKILL Directives            │
│   13 个 Tool：规则引擎 + 记忆管理 + 知识库 + skill_orchestration     │
│   KV Cache：cache_control: {"type": "ephemeral"}                    │
└──────────┬──────────────────────────────────────────────────────────┘
           │ Function Calling
    ┌──────┼──────────┬──────────────┬────────────┐
    ▼      ▼          ▼              ▼            ▼
┌────────┐┌────────┐┌──────────┐┌─────────┐┌─────────────┐
│规则引擎 ││记忆管理  ││知识库检索  ││Dice掷骰  ││8 SKILL 编排  │
└────────┘└────────┘└──────────┘└─────────┘└─────────────┘
                                                      ↓
                                       ┌─────────────────────────┐
                                       │ 注入到 DM 上下文的       │
                                       │ SKILL Directives 文本    │
                                       └─────────────────────────┘
```

**Layer 3（会话级）**：每个 session 一个 `RLock` + `SessionPool` 全局锁

**Layer 4（LLM 级）**：`LLMThrottle` Semaphore 限制 `max_concurrent=3` 同时 LLM 调用

**Layer 5（持久化级）**：`AsyncSaveQueue` 异步存档 + 文件锁

---

## 🎯 8 SKILL 编排体系（v1.4+ 核心创新）

| SKILL | 功能 | 实现 |
|---|---|---|
| **SKILL-1 读场判断** | 6 维度评估（投入度/情绪/张力/进度/路线/偏离） | `dm_skills.skill_1_assess_scene` |
| **SKILL-2 节奏控制** | 4 时间模式（slow/now/abstract/sharp_cut）+ 扶正 | `dm_skills.skill_2_decide_pacing` |
| **SKILL-3 线索投放** | 4 类型（推动/引导/揭示/压力） | `dm_skills.skill_3_plan_lead` |
| **SKILL-4 史实锚定** | 三层操作（铺垫/触发/应对） | `dm_skills.skill_4_anchor_history` |
| **SKILL-5 价值观发声** | 5 维度 + 等级 1-5 触发（DE 风格的内在声音） | `dm_skills.skill_5_activate_voices` |
| **SKILL-6 失败叙事化** | 4 类型 → 4 转化（"做不到 A，但发现 B"） | `dm_skills.skill_6_handle_failure` |
| **SKILL-7 三层裁判** | 铁律/可然/自由 | `dm_skills.skill_7_three_layer_verdict` |
| **SKILL-8 认知框架锁定** | 路线 → 信息过滤 | `dm_skills.skill_8_lock_cognitive_frame` |

灵感来自 [Disco Elysium 调研](docs/调研成果汇报.md) + [8 SKILL 体系整合](docs/历史注脚体验引擎：AI DM SKILL体系整合.md) + [DND 节奏控制](docs/历史注脚体验引擎：AI DM节奏控制设计——借鉴剧本杀与DND人类DM.md)。

---

## 📊 实测性能（v1.6.1）

### 5 回合真实 LLM 测试

| 指标 | 结果 |
|---|---|
| 叙事长度 | 254-885 字符（极丰富） |
| SKILL-4 春税触发 | 6 次 |
| SKILL-5 内心独白 | 8 次 |
| 已解锁认知 | 2 个（ins_city_life / ins_silk_trade） |
| 触发事件 | 1 个（he_01 万历帝罢朝） |
| 崩溃 | 0 |

### 5 玩家并发压力测试

| 指标 | 结果 |
|---|---|
| 并发玩家数 | 5 个同时 |
| 成功率 | **5/5（100%）** |
| 总耗时 | 71.8s |
| 每个玩家叙事长度 | 51-694 字符 |
| 数据竞争 | 0 |

### KV 缓存节省（理论 50 回合）

| 指标 | 当前 | 缓存后 | 节省 |
|---|---|---|---|
| 单回合 input tokens | ~5500 | ~1200 | 78% ↓ |
| 单局成本 | ~$0.0275 | ~$0.0075 | 73% ↓ |
| Cache 命中率 | — | 98% | — |
| 首 token 延迟 | 3-5s | 1-2s | 50% ↓ |

---

## 🛠️ 技术栈

| 组件 | 方案 |
|---|---|
| Python | 3.11+ |
| Agent 框架 | LangChain + LangGraph |
| 数据模型 | Pydantic 2.0（@dataclass） |
| LLM | Minimax M3（Anthropic 兼容协议） |
| Web 服务 | Python `http.server`（无依赖） |
| 并发 | threading + Semaphore（标准库） |
| KV 缓存 | Anthropic `cache_control`（ephemeral 5min） |

---

## 📚 文档

| 文档 | 说明 |
|---|---|
| [**v3.0 完整产品设计文档**](docs/历史注脚体验引擎：完整产品设计文档 v3.0.md) | **当前主文档**（含 v1.6+ 所有实现） |
| [WORK_SUMMARY.md](docs/WORK_SUMMARY.md) | v1.6+ 工作总结 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [调研成果汇报.md](docs/调研成果汇报.md) | Disco Elysium 调研 |
| [AI DM SKILL体系整合.md](docs/历史注脚体验引擎：AI DM SKILL体系整合.md) | 8 SKILL 设计基础 |
| [AI DM节奏控制设计.md](docs/历史注脚体验引擎：AI DM节奏控制设计——借鉴剧本杀与DND人类DM.md) | 4 时间模式设计 |

---

## 🤝 贡献指南

欢迎贡献！建议流程：

1. Fork 本仓库
2. 创建 feature 分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献方向

- 🌟 新增时代包（贞观之治、交子、太平天国等）
- 🌟 接入新 LLM（OpenAI / Anthropic / DeepSeek）
- 🌟 完成 P1/P2 缺失项（知识库 4 层 / finale_templates / Dice Engine 接入）
- 🌟 单元测试覆盖
- 🌟 文档翻译

---

## 📜 License

MIT

---

## 🔗 相关链接

- 项目主页：http://localhost:8765/（本地启动后）
- 问题反馈：[GitHub Issues](https://github.com/your-org/history-footnote-engine/issues)
- 完整文档：[docs/](docs/)
- 工作总结：[docs/WORK_SUMMARY.md](docs/WORK_SUMMARY.md)