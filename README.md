# 历史注脚体验引擎 (History Footnote Engine)

> **AI 当 DM，你当历史里的小人物。** 通过对话体验一个历史时期，历史走势不可改，但你的选择路径完全开放。

## 🎉 v2.7 已发布（命运卡完整闭环）

最新版本（2026-07-09）完成了命运卡"感知闭环"：

- ✅ **命运卡从装饰到核心战略**（v2.5 → v2.6：抽 + 主动使用 + 应急弹出）
- ✅ **DM 知道玩家用过什么卡**（v2.6.1：已用卡段注入 prompt）
- ✅ **玩家知道卡影响了谁**（v2.6.2：人物档案命运影响段）
- ✅ **完全可重放**（v2.7：LLM temperature=0 + 同 seed 100% 复现）
- ✅ **66 个测试**（整合 + E2E + 边界 + 重放 + 温度控制）

详见 [docs/log/2026-07-09_v2.5-v2.7-work-log.md](docs/log/2026-07-09_v2.5-v2.7-work-log.md)

---

## 🎯 核心特性

### 玩法层

- **配置驱动**：换一份 `era.json` + `dm_persona.md` 就能切换到新历史时期
- **DE 风格选项**：每回合 2-4 个内在声音选项（Disco Elysium 风格）
- **8 SKILL 编排**：确定性逻辑归代码，DM 只做创意性判断
- **行动点系统**：每月 3-4 个行动点，"过日子"般的沉浸感
- **8 步初始化向导**：玩家深度定制角色
- **位置系统**（v2.4）：盛泽镇 10 地点 + 邻居系统 + 路遇事件
- **命运卡系统**（v2.5-v2.7）：
  - 抽 5 张开局命运卡
  - 3 种 use_type：immediate / round_start / emergency
  - 5 个 emergency 触发器
  - DM 知道玩家用过什么卡
  - 玩家看见卡影响了哪些 NPC
  - **同 seed 100% 重放**（v2.7 温度控制）

### 工程层

- **后端**：Python 3.11 + LangGraph + dataclass
- **前端**：Svelte 5 + Vite + TypeScript + 现代 CSS
- **后校验 + 重试 + 兜底**：5 层校验，2 次重试，模板兜底
- **5 层并发**：进程级 + 线程级 + 会话级 + LLM 级 + 持久化级
- **KV 缓存**：Anthropic `cache_control`（ephemeral 5min，节省 70-98% input tokens）
- **三阶段行为模型**：态势评估 → 叙事生成 → 状态确认
- **完全可重放**（v2.7）：所有 LLM 调用按 purpose 设 temperature

---

## 🚀 快速开始

### 启动后端 + 前端

```bash
# 1. 后端（端口 8765）
python -m history_footnote.web_server_concurrent --port 8765 --workers 2

# 2. 前端（端口 5173）
cd src/frontend && npm install && npm run dev
```

访问 **http://localhost:5173/** 开始游戏。

### CLI 模式

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
# 后端 v2.5-v2.7 测试套件（66 个）
cd /Users/mac/Documents/trae_projects/history_footnote
python tests/run_all_v26.py

# 单独跑某个测试
python tests/test_v26_integration.py        # L1 整合（12）
python tests/test_v26_edge_cases.py          # L4 边界（8）
python tests/test_v26_e2e_mock.py            # L2 E2E mock（5）
python tests/test_v26_e2e_real_llm.py        # L3 E2E 真实 LLM（3）
python tests/test_l9_replay.py               # L9 重放（5）
python tests/test_v27_temperature.py         # v2.7 温度（5）

# 前端 mapper 测试（6 个，需要 DEEPSEEK_API_KEY）
cd src/frontend
npm test -- src/lib/api/mapper.test.ts
```

### 早期测试（v2.4 之前）

```bash
# 后校验 / 并发 / KV 缓存
python scripts/test_post_validator.py
python scripts/test_concurrency.py
python scripts/test_kv_cache.py

# 5 玩家并发压力测试
python scripts/test_concurrent_real.py
```

---

## 📁 项目结构

```
history-footnote-engine/
├── README.md                    # 本文档
├── CHANGELOG.md                 # 版本变更记录
├── pyproject.toml
├── docs/                        # 项目文档
│   ├── README.md                # 文档索引
│   ├── design/                  # 引擎设计
│   ├── eras/万历十五年/          # 时代包知识
│   ├── api/                     # API 文档
│   ├── log/                     # 工作日志
│   │   ├── 2026-07-09_v2.5-v2.7-work-log.md  ← 🆕
│   │   ├── 2026-07-07_v1.9.1-4-work-log.md
│   │   ├── 2026-07-06_structured-io-analysis.md
│   │   └── 2026-07-05_v1.7.20-26-work-log.md
│   └── architecture/            # 架构文档
├── src/
│   ├── history_footnote/        # 后端（22+ 模块）
│   │   ├── game_loop.py         # 游戏主循环
│   │   ├── dm_agent/            # DM Agent（LangGraph）
│   │   ├── fate_cards.py        # 🆕 v2.5-v2.7 命运卡
│   │   ├── location_service.py  # 🆕 v2.4 文字地图
│   │   ├── random_utils.py      # 🆕 v2.5 seed 机制
│   │   ├── llm_providers.py     # 🆕 v2.7 temperature 控制
│   │   ├── post_validator.py    # 后校验
│   │   ├── concurrency.py       # 5 层并发
│   │   ├── kv_cache.py          # KV 缓存
│   │   └── ...
│   └── frontend/                # 前端 Svelte 5 + Vite
│       ├── src/
│       │   ├── routes/
│       │   │   ├── +page.svelte           # 主页
│       │   │   ├── game/+page.svelte      # 游戏页
│       │   │   └── wizard/+page.svelte    # 8 步初始化
│       │   ├── lib/
│       │   │   ├── api/
│       │   │   │   ├── mapper.ts          # 🆕 v2.7 字段映射
│       │   │   │   ├── mapper.test.ts     # 🆕 6 个 vitest
│       │   │   │   ├── types.ts
│       │   │   │   └── ...
│       │   │   ├── stores/
│       │   │   │   ├── fate-events.ts     # 🆕 v2.7 事件总线
│       │   │   │   ├── game.ts
│       │   │   │   └── ...
│       │   │   └── components/
│       │   │       ├── game/
│       │   │       │   ├── CharCard.svelte      # 🆕 命运卡预览
│       │   │       │   ├── FateHandPanel.svelte # 命运卡手牌
│       │   │       │   ├── GameView.svelte      # 🆕 响应式布局
│       │   │       │   └── ...
│       │   │       └── modals/
│       │   │           └── CharacterWikiModal.svelte  # 🆕 命运影响段
│       │   └── ...
│       ├── package.json
│       └── vite.config.ts
├── tests/                       # 🆕 v2.5-v2.7 测试套件
│   ├── run_all_v26.py           # 一键跑全部
│   ├── test_v26_integration.py  # L1 整合（12）
│   ├── test_v26_edge_cases.py    # L4 边界（8）
│   ├── test_v26_e2e_mock.py      # L2 mock（5）
│   ├── test_v26_e2e_real_llm.py  # L3 真实（3）
│   ├── test_l9_replay.py         # L9 重放（5）
│   └── test_v27_temperature.py   # 温度（5）
├── eras/
│   ├── _template/               # 时代包模板
│   └── wanli1587/               # 万历十五年
│       ├── era.json
│       └── dm_persona.md
├── scripts/                     # 早期测试
└── tools/
    └── validate_era.py
```

---

## 🏗️ 核心架构

```
┌─────────────────────────────────────────────────────────────────────┐
│              Web Server (HTTP API :8765)                            │
│  Layer 1: 进程级（gunicorn / concurrent）                              │
│  Layer 2: 线程级（ThreadingHTTPServer + ThreadPoolExecutor）         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│     DM Agent（唯一的 LLM 调用点 · v2.7 temperature 控制）             │
│  System Prompt = DM 人格 + 时代配置 + 8 SKILL Directives            │
│  13 个 Tool：规则引擎 + 记忆管理 + 知识库 + skill_orchestration     │
│  KV Cache：cache_control: {"type": "ephemeral"}                    │
│  🆕 v2.6.1：已用命运卡 + 当前 buff 注入 prompt                       │
└──────────┬──────────────────────────────────────────────────────────┘
           │ Function Calling
    ┌──────┼──────────┬──────────────┬────────────┬─────────────┐
    ▼      ▼          ▼              ▼            ▼             ▼
┌────────┐┌────────┐┌──────────┐┌─────────┐┌──────────┐┌──────────────┐
│规则引擎 ││记忆管理  ││知识库检索  ││Dice掷骰  ││8 SKILL 编排 ││命运卡系统 🆕 │
│        ││        ││          ││        ││          ││v2.5-v2.7     │
└────────┘└────────┘└──────────┘└─────────┘└──────────┘└──────────────┘
                                                  ↓       ↓
                                       ┌──────────────────────────┐
                                       │ 🆕 同 seed 100% 重放     │
                                       │    (v2.7 LLM temp=0)     │
                                       └──────────────────────────┘
```

**Layer 3（会话级）**：每个 session 一个 `RLock` + `SessionPool` 全局锁
**Layer 4（LLM 级）**：`LLMThrottle` Semaphore 限制 `max_concurrent=3` 同时 LLM 调用
**Layer 5（持久化级）**：`AsyncSaveQueue` 异步存档 + 文件锁
**🆕 v2.7**：session 创建后立即存档（保证命运卡持久化）

---

## 🎯 命运卡系统（v2.5-v2.7 核心创新）

| 版本 | 主题 | 关键能力 |
|---|---|---|
| **v2.5** | 命运卡基础 | 抽 5 张卡 + 全局 seed 机制 + 立即应用 |
| **v2.6** | 主动使用 | 3 种 use_type + 5 触发器 + 应急弹出 |
| **v2.6.1** | DM 感知 | 已用卡段注入 prompt + buff 跟踪 |
| **v2.6.2** | 玩家感知 | 人物档案命运影响段 + 命运卡分享按钮 |
| **v2.7** | 完全可重放 | LLM temperature=0 + 同 seed 100% 复现 |
| **v2.7** | UI 集成 | CharCard 命运卡预览 + chip 跳转/一键使用 |
| **v2.7** | 响应式 | clamp + container queries 跨设备 |

### 命运卡"感知闭环"

```
玩家抽卡    →  用卡    →  DM 知道    →  玩家看见影响    →  同 seed 重玩
v2.5 抽     v2.6 主动   v2.6.1 prompt  v2.6.2 档案     v2.7 100%
```

### 3 种 use_type

| 类型 | 触发时机 | 例子 |
|---|---|---|
| `immediate` | 玩家主动 | 💰天降横财、❤️沈氏倾心 |
| `round_start` | 回合开始 | ⏳时光悠悠、⚡精力充沛 |
| `emergency` | 自动弹出 | ✨吉星高照、🛡️护身符 |

### 5 个 emergency 触发器

- `cash_critical`（现金 < 1 两）
- `debt_high`（欠债 > 3 两）
- `rice_empty`（米 < 1）
- `unlucky_active`（有 unluck buff）
- `late_round`（回合 > 6）

---

## 🧪 测试覆盖

### 66 个测试（v2.5-v2.7）

| 类别 | 数量 | 工具 | 时长 |
|---|---|---|---|
| 后端单元（v2.5 之前）| 22 | pytest-like | <1 分钟 |
| L1 整合 | 12 | direct | <1 分钟 |
| L2 E2E mock | 5 | mock LLM | <1 分钟 |
| L3 E2E 真实 LLM | 3 | DeepSeek API | 3-5 分钟 |
| L4 边界 | 8 | direct | <1 分钟 |
| L9 重放 | 5 | direct | <1 分钟 |
| temperature | 5 | direct | <1 分钟 |
| 前端 vitest | 6 | vitest | <10 秒 |
| **总计** | **66** | | **~7 分钟** |

### 一键跑全部

```bash
python tests/run_all_v26.py
# 后端 60 通过 / 0 失败
# 前端 6 通过（vitest，需要 DEEPSEEK_API_KEY 可选）
```

### 早期测试（v2.4 之前）

| 类别 | 文件 |
|---|---|
| 后校验 | `scripts/test_post_validator.py` |
| 并发 | `scripts/test_concurrency.py` |
| KV 缓存 | `scripts/test_kv_cache.py` |
| 5 玩家并发压力 | `scripts/test_concurrent_real.py` |
| 8 SKILL 烟雾 | `scripts/smoke_test_8_skills.py` |
| 5 回合真实 LLM | `scripts/test_8_skills_real.py` |

---

## 📊 实测性能

### 5 回合真实 LLM 测试（v1.6.1）

| 指标 | 结果 |
|---|---|
| 叙事长度 | 254-885 字符 |
| SKILL-4 春税触发 | 6 次 |
| SKILL-5 内心独白 | 8 次 |
| 崩溃 | 0 |

### 5 玩家并发压力测试（v1.6.1）

| 指标 | 结果 |
|---|---|
| 并发玩家数 | 5 个同时 |
| 成功率 | **5/5（100%）** |
| 数据竞争 | 0 |

### v2.7 重放测试（L9）

| 指标 | 结果 |
|---|---|
| 抽 5 张卡重放 | 5 个 seed × 3 次 = 15 次一致 |
| 20 个 random 决策 | 完全相同 |
| 5 回合路径（5 移动 + 5 路遇 + 5 AP）| 完全相同 |
| 序列化-反序列化 | 完全一致 |

### KV 缓存节省

| 指标 | 当前 | 缓存后 | 节省 |
|---|---|---|---|
| 单回合 input tokens | ~5500 | ~1200 | 78% ↓ |
| 单局成本 | ~$0.0275 | ~$0.0075 | 73% ↓ |
| Cache 命中率 | — | 98% | — |

---

## 🛠️ 技术栈

| 组件 | 方案 |
|---|---|
| Python | 3.11+ |
| Agent 框架 | LangChain + LangGraph |
| 数据模型 | Pydantic 2.0（@dataclass）|
| LLM | Minimax M3（Anthropic 兼容）/ DeepSeek / OpenAI |
| 前端 | Svelte 5 + Vite + TypeScript |
| 前端测试 | Vitest |
| Web 服务 | Python `http.server`（无依赖）|
| 并发 | threading + Semaphore（标准库）|
| KV 缓存 | Anthropic `cache_control`（ephemeral 5min）|

---

## 📚 文档

| 文档 | 说明 |
|---|---|
| [docs/README.md](docs/README.md) | 文档索引 |
| [docs/log/2026-07-09_v2.5-v2.7-work-log.md](docs/log/2026-07-09_v2.5-v2.7-work-log.md) | 🆕 v2.5-v2.7 工作日志 |
| [docs/log/2026-07-07_v1.9.1-4-work-log.md](docs/log/2026-07-07_v1.9.1-4-work-log.md) | LLM 缓存 + Token 优化 |
| [docs/design/产品设计文档.md](docs/design/产品设计文档.md) | 主设计文档（现行版）|
| [docs/design/AI DM SKILL体系.md](docs/design/AI%20DM%20SKILL体系.md) | 8 SKILL 设计 |
| [docs/design/AI DM 节奏控制.md](docs/design/AI%20DM%20节奏控制.md) | 4 时间模式设计 |
| [docs/调研成果汇报.md](docs/调研成果汇报.md) | Disco Elysium 调研 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |

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
- 🌟 完善命运卡系统（图鉴、组合、排行榜）
- 🌟 单元测试覆盖（已达 66 个）
- 🌟 文档翻译

---

## 📜 License

MIT

---

## 🔗 相关链接

- 项目主页：http://localhost:5173/（前端）/ http://localhost:8765/（后端 API）
- 问题反馈：[GitHub Issues](https://github.com/your-org/history-footnote-engine/issues)
- 完整文档：[docs/](docs/)
- 工作总结：[docs/log/](docs/log/)
