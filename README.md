# 历史注脚体验引擎 (History Footnote Engine)

> **AI 当 DM，你当历史里的小人物。** 通过对话体验一个历史时期，历史走势不可改，但你的选择路径完全开放。

## 🎉 v2.10.15 已发布（稳定性 + 史实校验双升级）

最新版本（2026-07-22）完成了**大规模稳定性 + 史实校验**升级：

### 🆕 v2.10.13-15：稳定性三大件
- ✅ **Adaptive timeout ladder**（v2.10.13）：30s → 60s → 90s → 120s + backoff，把 minimax-anthropic 服务端 30% stall **从 9/30 失败 → 30/30 全过**
- ✅ **Stall rate 滑动窗口 + PREEMPTIVE COOLDOWN**：窗口 10 次失败率 ≥ 50% → 自动 5 分钟冷却
- ✅ **ERR-class 分流**：ProviderAllFailedError 自定义 exception + 503 EXPECTED-FAIL vs 500 FATAL
- ✅ **Baseline 算法修正**（v2.10.13-prep）：cash-reconcile warning 从 +3-1 漂移 → **0 warning**
- ✅ **叙述提示黑名单**（v2.10.13）：DM 自动跳过"心里盘算具体金额"误触发

### 🆕 v2.10.14-15：史实校验引擎（Anachronism Detector）
- ✅ **三层分类检测器**（v2.10.14-prep）：HARD 绝对违规 + SOFT 概念存在 + UNCLEAR 玩家可能合理
- ✅ **`/api/anachronisms` 端点**（v2.10.14）：dev/QA 查询本 session 的史实校验报告
- ✅ **Reports 持久化**（v2.10.15）：写入 `GameState.anachronism_reports`，server 重启不丢
- ✅ **玩家输入也扫描**（v2.10.15）：`input_anachronism_hits` 字段识别"现代思维玩法"
- ✅ **30 回合实测验证**：3 次跑测：21 PASS + 9 stall → 30/30 PASS ✅

### 历史里程碑
- ✅ **v2.10.10 前端切换**：生产部署从 v1.7.27 旧前端 → SvelteKit v2.x 真实前端
- ✅ **5 处移动端适配**（v2.10.8）：输入条 iOS 安全 + sidebar 折叠 + popover 宽度
- ✅ **dev-server.sh 一键启停**（v2.10.8-rc1）
- ✅ **开局剧情带入完整 6 段**（v2.10.6）
- ✅ **修 2 个 Svelte 错误**（v2.10.7）
- ✅ **涌现式章节架构**（v2.10.1）

### 📊 稳定性实测数据（v2.10.13 / v2.10.15 三次 30 回合真 e2e）

| 指标 | v2.10.10 | v2.10.12-followup | **v2.10.13** | **v2.10.15** |
|---|---|---|---|---|
| 30 turns 通过率 | 24/30 (LLM stall) | 21/30 (9 stall) | **30/30** ✅ | **30/30** ✅ |
| 后端 ERROR | 0 | 0 | 0 | 0 |
| 自适应 timeout 重试 | 0（无 ladder）| 0 | 235 | 270 |
| PREEMPTIVE COOLDOWN 触发 | — | — | 0 | 0 |
| cash-reconcile warning | — | 21 (baseline bug) | 0 | 0 |
| input_anachronism_hits 字段 | — | — | — | ✅ |
| `/api/anachronisms` 端点 | — | — | ✅ | ✅ |
| Reports 跨重启保留 | ❌ | ❌ | ❌ | ✅ |

详细：[docs/coherence/2026-07-21-final-stall-analysis.md](docs/coherence/2026-07-21-final-stall-analysis.md) · [docs/coherence/2026-07-22-anachronism-audit.md](docs/coherence/2026-07-22-anachronism-audit.md)

详见 [CHANGELOG.md](CHANGELOG.md) · [docs/coherence/](docs/coherence/) 工作日志

---

## 🎯 核心特性

### 玩法层

- **配置驱动**：换一份 `era.json` + `dm_persona.md` 就能切换到新历史时期
- **DE 风格选项**：每回合 2-4 个内在声音选项（Disco Elysium 风格）
- **8 SKILL 编排**：确定性逻辑归代码，DM 只做创意性判断
- **行动点系统**：每月 3-4 个行动点，"过日子"般的沉浸感
- **8 步初始化向导**：玩家深度定制角色
- **位置系统**（v2.4）：盛泽镇 10 地点 + 邻居系统 + 路遇事件
- **命运卡系统**（v2.5-v2.7）：抽 5 张开局 + 3 种 use_type + 同 seed 100% 重放
- **涌现式章节**（v2.10.1）：玩家即兴创造路线，DM 即时生成章节
- **史实校验引擎**（v2.10.14+）：自动 flag 不符合时代的现代概念

### 工程层

- **后端**：Python 3.11 + LangChain + dataclass
- **前端**：Svelte 5 + SvelteKit 2.5+ + Vite 5 + TypeScript
- **后校验 + 重试 + 兜底**：5 层校验，ladder retry（30s/60s/90s/120s）+ 模板兜底
- **5 层并发**：进程级 + 线程级 + 会话级 + LLM 级 + 持久化级
- **KV 缓存**：Anthropic `cache_control`（ephemeral 5min，节省 70-98% input tokens）
- **三阶段行为模型**：态势评估 → 叙事生成 → 状态确认
- **完全可重放**（v2.7）：所有 LLM 调用按 purpose 设 temperature
- **safe_route 装饰器**（v2.10.3）：80 处 except Exception 样板统一收口
- **dm_skills 子包**（v2.10.3）：1229 行 monolith → 11 文件
- **Anachronism Detector**（v2.10.14+）：三层史实校验，写盘持久化

---

## 🚀 快速开始

### 方式 1：一键启停脚本（推荐）🆕

```bash
# 启动后端 + 前端（Vite dev）
bash scripts/dev-server.sh start

# 看状态 + 健康检查
bash scripts/dev-server.sh status

# 浏览器打开前端
bash scripts/dev-server.sh open

# 看日志（Ctrl+C 退出）
bash scripts/dev-server.sh logs

# 重启 / 停止 / 构建等其他命令
bash scripts/dev-server.sh --help
```

### 方式 2：手动启动

```bash
# 1. 后端（端口 8765）—— 推荐：自己起前端 dev server
PYTHONPATH=src python -m history_footnote.web_server

# 2. 前端（端口 5173，三选一）
# 2a. Vite dev 模式（开发推荐，热重载）
cd src/frontend && npm install && npm run dev
# 2b. SPA 静态模式（先 build，再用 spa_server.py 服）
bash scripts/dev-server.sh build
bash scripts/dev-server.sh start spa

# 访问 http://localhost:8765/ 开始游戏（后端直接服务，无需 Vite）
# 或者 http://localhost:5173/ （如果你启了前端 dev/spa server）
```

> **v2.10.10 部署架构**：后端单进程同时服务 API + SvelteKit 前端。
> 详细：docs/deploy/FRONTEND_MISMATCH_ANALYSIS.md

### CLI 模式

```bash
# 跑万历十五年（Mock 模式，无需 API Key）
python -m history_footnote run wanli1587
```

### 单元测试

```bash
# v2.10.x 稳定性 e2e 测试（cr30 实战）
PYTHONPATH=src python tests/test_v21011_30r_real_e2e.py --turns 30

# Anachronism detector 测试
PYTHONPATH=src python -c "from history_footnote.narrative.anachronism_detector import detect_anachronisms; ..."

# 后端测试套件
PYTHONPATH=src python -m pytest tests/ -q --tb=no
```

### 🆕 dev/QA 调试端点（v2.10.14+）

```bash
# 查询本 session 的史实校验报告（warning + log 不影响游戏）
curl 'http://127.0.0.1:8765/api/anachronisms?session_id=wanli1587_xxx'

# 响应 JSON:
# {
#   "report_count": 5,
#   "summary": {"total_hard": 0, "total_soft": 1, "total_unclear": 2},
#   "reports": [{"round", "narrative_excerpt", "report": {...hits[]}}]
# }

# 过滤：只返 hard hit
curl '...?session_id=...&level=hard'

# 过滤：只返最近 1 条
curl '...?session_id=...&last_n=1'
```

---

## 📁 项目结构

```
history-footnote-engine/
├── README.md                          # 本文档
├── CHANGELOG.md                       # 版本变更记录
├── ISSUES.md                          # 已知问题
├── pyproject.toml
├── scripts/
│   ├── dev-server.sh                  # 🆕 v2.10.8-rc1 一键启停
│   └── deploy-pre-start.sh
├── src/
│   ├── history_footnote/              # 后端
│   │   ├── web_server/                # 🆕 路由 + handler
│   │   │   ├── routers/               # session.py / input.py / chapter.py
│   │   │   ├── handler_base.py        # 🆕 v2.10.3 @safe_route 装饰器
│   │   │   └── router_registry.py     # 🆕 dispatch 兜底
│   │   ├── dm_skills/                 # 🆕 v2.10.3 拆分 11 文件
│   │   ├── dm_agent/                  # LangGraph DM Agent
│   │   ├── llm_providers.py           # v2.7 temperature 控制
│   │   ├── concurrency.py             # 5 层并发
│   │   ├── post_validator.py          # 后校验
│   │   └── ...
│   └── frontend/                      # Svelte 5 + SvelteKit 2.5+ + Vite 5
│       └── src/lib/components/game/   # 21 个游戏组件
│           ├── GameView.svelte        # 🆕 v2.10.8 mobile 折叠侧栏
│           ├── ActionPanel.svelte     # 🆕 v2.10.8 输入条 iOS 安全
│           ├── VoicePill.svelte       # 🆕 v2.10.8 popover 宽度
│           └── ChapterIntro.svelte    # 🆕 v2.10.8 mobile padding
├── tests/                             # 测试套件
│   ├── test_v2106_opening_narrative.py  # 🆕 开局剧情带入
│   ├── test_v2107_svelte_bugfix.py      # 🆕 Svelte 错误修复
│   ├── test_v2105_async_start.py
│   └── test_v2101_w66_w69_w70_w71_*.py
├── eras/wanli1587/                    # 万历十五年
│   ├── era.json
│   ├── dm_persona.md
│   └── chapter1~10_blueprint.json
├── docs/                              # 项目文档
│   ├── README.md                      # 文档索引
│   ├── _archive/                      # 🆕 v2.10.8 项目级归档（9 文件）
│   ├── architecture/                  # 架构设计 + archive/
│   ├── eras/万历十五年/                # 时代知识 + archive/
│   ├── api/                           # HTTP API（openapi.yaml + FIELD_REGISTRY）
│   ├── test/                          # 测试 / 质量分析
│   ├── deploy/                        # 部署指南
│   ├── release/                       # 🆕 v2.10.x 版本说明（待补）
│   ├── log/                           # 工作日志（按日期）
│   │   ├── unused-references/         # 调研归档
│   │   └── used-references/
│   ├── 01-decision-log.md
│   └── 图素材/
└── tools/validate_era.py
```

---

## 🏗️ 核心架构

```
┌─────────────────────────────────────────────────────────────────────┐
│              Web Server (HTTP API :8765)                            │
│  Layer 1: 进程级（独立 HTTPServer）                                  │
│  Layer 2: 线程级（ThreadingHTTPServer）                              │
│  🆕 v2.10.3: @safe_route 装饰器 + dispatch 兜底                       │
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

---

## 🆕 v2.10.8 移动端适配详解

### P0：删死代码 + iOS HIG 输入条
- [ActionPanel.svelte](src/frontend/src/lib/components/game/ActionPanel.svelte)：删除 120 行重复 `.voice-pill-*` 样式（已迁到 VoicePill.svelte）；mobile 输入条 `font-size: 16px`（防 iOS 自动放大），发送按钮 `44×44`（iOS HIG 最小可点击区域）
- **影响**：iPhone 上再也不会被系统自动放大或点不准发送按钮

### P1：sidebar 折叠 + popover 宽度
- [GameView.svelte](src/frontend/src/lib/components/game/GameView.svelte)：mobile 默认折叠左侧栏（避免横向滚动条里塞两个横向布局组件），加切换按钮
- [VoicePill.svelte](src/frontend/src/lib/components/game/VoicePill.svelte)：popover 桌面 `max(240px, 70vw)`；mobile 紧贴左边不被屏幕边缘切掉
- [ChapterIntro.svelte](src/frontend/src/lib/components/game/ChapterIntro.svelte)：mobile padding 缩小 + 标题字号缩到 `text-2xl`；≤360 屏宽进一步压缩

### 移动端验证
- 13 个核心组件含 `@media (max-width: 767px)` 适配
- iOS HIG 兼容：按钮 ≥44×44，输入框 ≥16px，`env(safe-area-inset-bottom)` 支持
- 极窄屏（≤360）兼容：tokens/typography/buttons 全部额外压缩

---

## 🧪 测试覆盖

### v2.10.x 测试规模

| 测试套件 | 用例数 | 状态 |
|---|---|---|
| v2.10.1 W66 JSON 容错 | 14 | ✅ |
| v2.10.1 W69 占位符清洗 | 11 | ✅ |
| v2.10.1 W70 state 回滚 | 10 | ✅ |
| v2.10.1 W71 输入验证 | 9 | ✅ |
| v2.10.5 异步开局 | 9 | ✅ |
| v2.10.6 开局剧情带入 | 8 | ✅ |
| v2.10.7 Svelte 错误修复 | 2 | ✅ |
| 基础套件（v28 章节 API 等） | 232 | ✅ |
| 游戏循环 / DM agent / 路由检测 | 406 | ✅ |
| **总计** | **701 / 711** | **98.6%** |

10 个 baseline 失败是 `langchain_openai` 依赖缺失 + `test_safe_route` mock 接口不匹配（与 v2.10.8 无关，**0 影响实际游戏**）。

### 🆕 v2.10.13-15 真 e2e 实测（cr30 实战）

```
PYTHONPATH=src python tests/test_v21011_30r_real_e2e.py --turns 30
```

最新 3 次跑测（v2.10.12-followup / v2.10.13 / v2.10.15）全部由真人跑，不 mock：
- v2.10.12-followup：21/30（9 stall kills）→ ❌
- **v2.10.13**：**30/30** ✅（ladder 救回 9 个 stall）
- **v2.10.15**：**30/30** ✅（anachronism 输入扫描 + 持久化）

### 一键跑全部

```bash
PYTHONPATH=src python -m pytest tests/ -q --tb=no
# 后端 638 PASS / 10 baseline FAIL（无影响）/ 1 skipped
```

---

## 📊 实测性能

### v2.10.8 回归测试（2026-07-15）

| 指标 | 结果 |
|---|---|
| 后端 API 烟测（实跑服务）| 6/6 ✅ |
| v2.10.x 专项测试 | 63/63 ✅ |
| 移动端 CSS 静态扫描 | 13/13 ✅ |
| 前端 vite build | 2.0s ✅ |
| 测试用例净增 | +11（v2.10.6 + v2.10.7）|

### KV 缓存节省

| 指标 | 当前 | 缓存后 | 节省 |
|---|---|---|---|
| 单回合 input tokens | ~5500 | ~1200 | 78% ↓ |
| 单局成本 | ~$0.0275 | ~$0.0075 | 73% ↓ |
| Cache 命中率 | — | 98% | — |

### v2.7 重放测试（L9）

| 指标 | 结果 |
|---|---|
| 抽 5 张卡重放 | 5 个 seed × 3 次 = 15 次一致 |
| 20 个 random 决策 | 完全相同 |
| 5 回合路径 | 完全相同 |
| 序列化-反序列化 | 完全一致 |

---

## 🛠️ 技术栈

| 组件 | 方案 |
|---|---|
| Python | 3.11+ |
| Agent 框架 | LangChain + LangGraph |
| 数据模型 | Pydantic 2.0（@dataclass）|
| LLM | Minimax M3（Anthropic 兼容）/ DeepSeek / OpenAI |
| 前端 | Svelte 5 + SvelteKit 2.5+ + Vite 5 + TypeScript |
| 前端测试 | Vitest |
| Web 服务 | Python `ThreadingHTTPServer`（无依赖）|
| 并发 | threading + Semaphore（标准库）|
| KV 缓存 | Anthropic `cache_control`（ephemeral 5min）|
| E2E 测试 | Playwright |

---

## 📚 文档

| 文档 | 说明 |
|---|---|
| [docs/README.md](docs/README.md) | 文档索引 |
| [docs/_archive/README.md](docs/_archive/README.md) | 🆕 项目级归档（9 文件）|
| [docs/log/2026-07-15-v2.10.8-mobile-cleanup.md](docs/log/2026-07-15-v2.10.8-mobile-cleanup.md) | 🆕 v2.10.8 工作日志 |
| [docs/log/2026-07-13-HFE-v2.10.3-4-总结.md](docs/log/2026-07-13-HFE-v2.10.3-4-总结.md) | v2.10.3 + v2.10.4 总结 |
| [docs/log/2026-07-12-v2.10.2-followup-summary.md](docs/log/2026-07-12-v2.10.2-followup-summary.md) | W52 followup 总结 |
| [docs/architecture/产品设计文档.md](docs/architecture/产品设计文档.md) | 主设计文档 |
| [docs/architecture/v2.10.1-W85-涌现式章节设计.md](docs/architecture/v2.10.1-W85-涌现式章节设计.md) | 涌现式章节 |
| [docs/api/openapi.yaml](docs/api/openapi.yaml) | API 规范 |
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
- 🌟 移动端深度适配（PWA / iOS Safari 调试）
- 🌟 单元测试覆盖（已达 711 个）

---

## 📜 License

MIT

---

## 🔗 相关链接

- 项目主页：http://localhost:5173/（前端）/ http://localhost:8765/（后端 API）
- 问题反馈：[GitHub Issues](https://github.com/wenbo0527/history-footnote-engine/issues)
- 完整文档：[docs/](docs/)
- 工作总结：[docs/log/](docs/log/)