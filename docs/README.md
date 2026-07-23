# 📚 历史注脚 HFE · 文档索引

> **新开发者入口**：从 [`../README.md`](../README.md) 开始。
> **本目录**包含所有项目文档,按职责分层(v2.10.2 重新整理,v2.10.15 同步更新)。
>
> 🆕 **v2.10.9**: [ARCHIVE_INDEX.md](ARCHIVE_INDEX.md) — 5 个归档目录（_archive/architecture archive/eras archive/log used/unused-references）统一索引
>
> 🆕 **v2.10.11**: [plans/ROADMAP.md](plans/ROADMAP.md) — 后续版本路线图（v2.10.13 / v2.10.14 / v2.10.15 已完成, v2.10.16 backlog）
>
> 🆕 **v2.10.15**: [coherence/](coherence/) 子目录 — 稳定性 / 史实校验的"审计 + 实测 + 验证"三层文档

## 🆕 2026-07-22 v2.10.15 稳定性三大件 + 史实校验双升级

> **总结**:第三次跑 30 回合实测,**30/30 PASS** ✅。Anachronism Detector 实装 + 端点化 + 持久化。
> 详见 [CHANGELOG.md](../../CHANGELOG.md) (已升到 v2.10.15)
>
> **核心改动**:
> - **v2.10.13 Adaptive Timeout Ladder**: 30s → 60s → 90s → 120s + backoff,**把 9/30 stall kills 救回**
> - **v2.10.13 PREEMPTIVE COOLDOWN**: 滑动窗口 10 次失败率 ≥ 50% → 自动 5 分钟冷却
> - **v2.10.13 ERR-class 分流**: ProviderAllFailedError + 503 EXPECTED-FAIL vs 500 FATAL
> - **v2.10.13 现金对账自适应**:implicit_initial = cash - sum(log),从 +3/-1 漂移到 0
> - **v2.10.13 提示黑名单词**:"告知 vs 动作" 区分,防 DM 误触 fin.pay_tax
> - **v2.10.14 Anachronism Detector**: 三层分类概念级检测 (HARD/SOFT/UNCLEAR)
> - **v2.10.14 `/api/anachronisms` 端点**:dev/QA 查询史实校验报告
> - **v2.10.15 Reports 持久化**:写盘 → 重启不丢
> - **v2.10.15 玩家输入扫描**:`input_anachronism_hits` 字段,识别"现代思维玩法"
>
> **新文档（coherence/）**:
> - [coherence/2026-07-20-30r-coherence-check.md](coherence/2026-07-20-30r-coherence-check.md) — 第一轮 30 回合核对
> - [coherence/2026-07-20-p0-fix-verified.md](coherence/2026-07-20-p0-fix-verified.md) — P0 修复验证
> - [coherence/2026-07-21-final-stall-analysis.md](coherence/2026-07-21-final-stall-analysis.md) — Stall 终极分析
> - [coherence/2026-07-21-v21013-verified.md](coherence/2026-07-21-v21013-verified.md) — v2.10.13 实测验证
> - [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) — Anachronism 功能审计
>
> **关联 commit**: `a23f8c6` (v2.10.13) · `8b05135` (v2.10.14-prep) · `b0ea5cf` (v2.10.14 endpoint) · `f0c70e9` (v2.10.15)
>
> **新 marketing**:
> - [marketing/zhihu-promotion.md](marketing/zhihu-promotion.md) — Zhihu 推广文 + 6.5 工程笔记"怎么 debug 一个明朝游戏"

## 🆕 2026-07-19 v2.10.10-11 前端切换 + real e2e 测试套件

> 生产部署真切换到 SvelteKit + 30 回合真 LLM e2e 验证套件
> 详见 [log/2026-07-19-v2.10.11-fixes-and-followups.md](log/2026-07-19-v2.10.11-fixes-and-followups.md)
>
> **核心改动**:
> - v2.10.10 前端：生产部署从 v1.7.27 旧前端 → SvelteKit v2.x
> - v2.10.11 SPA fallback：修复 `start spa` 模式
> - 新增 `tests/test_v21011_30r_real_e2e.py`：跑真 minimax-anthropic 30 回合
>
> **新文档**:
> - [log/2026-07-19-v2.10.11-real-30r-e2e.md](log/2026-07-19-v2.10.11-real-30r-e2e.md)

## 🆕 2026-07-15 v2.10.8 移动端适配 + 文档归档整理

> 5 组件 mobile 适配 + dev-server.sh 一键启停 + 9 文档归档 + README/CHANGELOG 同步
> 详见 [log/2026-07-15-v2.10.8-mobile-cleanup.md](log/2026-07-15-v2.10.8-mobile-cleanup.md)
>
> **核心改动**：
> - v2.10.8 移动端 5 处：ActionPanel 删死代码 + iOS HIG 输入条 + GameView sidebar 折叠 + VoicePill popover 宽度 + ChapterIntro padding
> - v2.10.8-rc1 dev-server.sh：一键启停 8 命令（start/stop/restart/status/logs/open/build）
> - 文档归档：新建 [_archive/](_archive/README.md) 项目级目录，git mv 9 个过期文档
>
> **新文档**：
> - [log/2026-07-15-v2.10.8-mobile-cleanup.md](log/2026-07-15-v2.10.8-mobile-cleanup.md)
> - [_archive/README.md](_archive/README.md) — 项目级归档索引

## 🆕 2026-07-13 v2.10.3 + v2.10.4 整理

> 4 commits / 68 文件 / +2387 -6530 / 2 tag
> 详见 [log/2026-07-13-HFE-v2.10.3-4-总结.md](log/2026-07-13-HFE-v2.10.3-4-总结.md)
>
> **核心改动**：
> - v2.10.3 P1 全量：safe_route 装饰器 + dm_skills.py 拆分（1229→11 文件）+ unwrap 工具（as any 60→15）
> - v2.10.4 P3 持续：低风险 router 装饰器化 + game_state 拆分评估
>
> **新文档**：
> - [log/2026-07-13-HFE-v2.10.3-4-总结.md](log/2026-07-13-HFE-v2.10.3-4-总结.md)
> - [log/2026-07-13-HFE-game-state-split-assessment.md](log/2026-07-13-HFE-game-state-split-assessment.md)
> - [log/2026-07-12-HFE-W52-优化清单-v1.1.md](log/2026-07-12-HFE-W52-优化清单-v1.1.md) — 状态同步

## 🆕 2026-07-12 v2.10.2 W52 followup 整理

> 13 BUG 修 / 22 svelte-check errors 清 / 4 文档新增
> 详见 [log/2026-07-12-v2.10.2-followup-summary.md](log/2026-07-12-v2.10.2-followup-summary.md)

---

## 🗂️ 目录结构

```
docs/
├── README.md                       ← 本文件(顶层索引)
├── ARCHIVE_INDEX.md                ← 跨目录归档索引
├── 01-decision-log.md             ← 项目关键决策
│
├── coherence/                      ← 🆕 v2.10.15+ 稳定性/史实校验审计
│   ├── 2026-07-20-30r-coherence-check.md    ← 30 回合一致性核对
│   ├── 2026-07-20-p0-fix-verified.md         ← P0 修复验证
│   ├── 2026-07-21-final-stall-analysis.md    ← Stall 终极分析
│   ├── 2026-07-21-v21013-verified.md         ← v2.10.13 验证
│   └── 2026-07-22-anachronism-audit.md       ← Anachronism 功能审计
│
├── marketing/                      ← 🆕 v2.10.15+ Zhihu / 营销
│   └── zhihu-promotion.md
│
├── architecture/                  ← 引擎设计文档
│   ├── README.md
│   ├── 产品设计文档.md             ← 主文档
│   ├── 核心交付物合集.md
│   ├── AI DM SKILL体系.md
│   ├── AI DM 节奏控制.md
│   ├── DM 引导者行为模式.md
│   ├── Era Wiki Compiler 方案.md
│   ├── UI优化委托即梦指南.md
│   ├── EventId规范.md
│   ├── TriggerPatterns.md
│   ├── v2.10.1-W85-涌现式章节设计.md  ← 现行版
│   ├── v2.7.1-后续TODO.md
│   └── archive/                   ← 历史版本
│
├── eras/万历十五年/                ← 万历时代包知识
│   ├── README.md
│   ├── 支线路径Wiki.md
│   ├── 离乡路线Wiki.md
│   ├── 闲谈素材Wiki.md
│   ├── 城市Wiki.md
│   ├── 知识条目集.md
│   └── archive/
│
├── api/                           ← HTTP API 文档
│   ├── README.md
│   ├── FIELD_REGISTRY.md
│   └── openapi.yaml
│
├── operations/                    ← 运维操作
│   └── README.md
│
├── deploy/                        ← 部署 / 运维
│   ├── README.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── FRONTEND_MISMATCH_ANALYSIS.md  ← 🆕 v2.10.10
│
├── test/                          ← 测试 / 质量
│   ├── README.md
│   ├── v2.10.2-comprehensive-test.md       ← 综合测试
│   ├── v2.10.2-bug-prevention-analysis.md  ← BUG 模式分析
│   └── v2.10.2-frontend-audit.md          ← 前端审计
│
├── plans/                         ← v2.10.11+ 后续版本规划
│   └── ROADMAP.md                  ← v2.10.12 → v2.10.15 已完成, v2.10.16 backlog
│
├── release/                       ← 版本说明
│   ├── README.md
│   ├── v2.10.1-release-notes.md
│   └── v2.10.2-release-notes.md
│
└── log/                           ← 工作日志(按日期)
    ├── README.md                  ← 日志索引
    ├── 2026-07-22-v2.10.15-coherence-updates.md  ← 🆕 本次稳定性/史实校验工作
    ├── 2026-07-21-...                            ← v2.10.13 stall 实测
    ├── 2026-07-20-...                            ← 30 回合一致性
    ├── 2026-07-19-v2.10.11-real-30r-e2e.md
    ├── 2026-07-19-v2.10.11-fixes-and-followups.md
    ├── 2026-07-15-v2.10.8-mobile-cleanup.md
    ├── 2026-07-13-HFE-v2.10.3-4-总结.md
    ├── 2026-07-12-v2.10.2-followup-summary.md
    └── ...
```

---

## 🎯 快速定位

### 🚀 我是新开发者

| 我想了解... | 看这里 |
|---|---|
| **项目基础信息** | [`../README.md`](file:///Users/mac/Documents/trae_projects/history_footnote/README.md) |
| **架构与功能设计** | [architecture/产品设计文档.md](architecture/产品设计文档.md) |
| **HTTP API 字段规范** | [api/FIELD_REGISTRY.md](api/FIELD_REGISTRY.md) |
| **HTTP API 端点清单** | [api/openapi.yaml](api/openapi.yaml) |
| **时代背景与剧情知识** | [eras/万历十五年/](eras/万历十五年/) |
| **如何部署?** | [deploy/DEPLOYMENT_GUIDE.md](deploy/DEPLOYMENT_GUIDE.md) |
| **稳定性 & 史实校验 metric** | [coherence/](coherence/) |

### 🐛 排查 BUG

| 我想... | 看这里 |
|---|---|
| **了解 BUG 根因模式** | [test/v2.10.2-bug-prevention-analysis.md](test/v2.10.2-bug-prevention-analysis.md) |
| **查看测试覆盖** | [test/v2.10.2-comprehensive-test.md](test/v2.10.2-comprehensive-test.md) |
| **看前端旧代码** | [test/v2.10.2-frontend-audit.md](test/v2.10.2-frontend-audit.md) |
| **查 v2.10.13+ 稳定性 stall** | [coherence/2026-07-21-final-stall-analysis.md](coherence/2026-07-21-final-stall-analysis.md) |
| **查 Anachronism 漏/误触** | [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) |
| **报告问题** | [`../ISSUES.md`](file:///Users/mac/Documents/trae_projects/history_footnote/ISSUES.md) |

### 📅 看开发历史

| 时段 | 看这里 |
|---|---|
| **v2.10.13-15 (本周)** | [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) · [log/](log/) |
| **v2.10.10-11 (上周)** | [log/2026-07-19-v2.10.11-real-30r-e2e.md](log/2026-07-19-v2.10.11-real-30r-e2e.md) |
| **v2.10.8 (7-15)** | [log/2026-07-15-v2.10.8-mobile-cleanup.md](log/2026-07-15-v2.10.8-mobile-cleanup.md) |
| **v2.10.2 W52 followup** | [log/2026-07-12-v2.10.2-followup-summary.md](log/2026-07-12-v2.10.2-followup-summary.md) |
| **v2.8.0 (W85 涌现式章节)** | [log/2026-07-11_v2.8.0-段六-真LLM-收尾-work-log.md](log/2026-07-11_v2.8.0-段六-真LLM-收尾-work-log.md) |
| **v2.5-v2.7 (命运卡)** | [log/2026-07-09_v2.5-v2.7-work-log.md](log/2026-07-09_v2.5-v2.7-work-log.md) |
| **完整工作日志** | [log/](log/) |

### 🤖 AI DM 设计

| 主题 | 文档 |
|---|---|
| **SKILL 体系** | [architecture/AI DM SKILL体系.md](architecture/AI%20DM%20SKILL体系.md) |
| **节奏控制** | [architecture/AI DM 节奏控制.md](architecture/AI%20DM%20节奏控制.md) |
| **引导者行为** | [architecture/DM 引导者行为模式.md](architecture/DM%20引导者行为模式.md) |
| **W85 涌现式章节** | [architecture/v2.10.1-W85-涌现式章节设计.md](architecture/v2.10.1-W85-涌现式章节设计.md) |

### 🤖 LLM Provider 稳定性（v2.10.13+）

| 我想了解... | 看这里 |
|---|---|
| **Adaptive Timeout Ladder** | [coherence/2026-07-21-final-stall-analysis.md](coherence/2026-07-21-final-stall-analysis.md) |
| **PREEMPTIVE COOLDOWN** | [coherence/2026-07-21-final-stall-analysis.md](coherence/2026-07-21-final-stall-analysis.md) |
| **ProviderAllFailedError** | [coherence/2026-07-21-final-stall-analysis.md](coherence/2026-07-21-final-stall-analysis.md) |
| **Cash Reconciliation 自适应** | [coherence/2026-07-20-p0-fix-verified.md](coherence/2026-07-20-p0-fix-verified.md) |
| **30 回合实测数据** | [coherence/2026-07-20-30r-coherence-check.md](coherence/2026-07-20-30r-coherence-check.md) |

### 📜 史实校验（v2.10.14+）

| 我想了解... | 看这里 |
|---|---|
| **Anachronism Detector 设计** | [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) |
| **三层分类（HARD/SOFT/UNCLEAR）** | [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) |
| **史实校验端点 + 持久化** | [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) |
| **漏网 modern concept（白名单待修）** | [coherence/2026-07-22-anachronism-audit.md](coherence/2026-07-22-anachronism-audit.md) |

---

## 📐 文档约定

### 现行版 / 历史版规则

- **`子目录/` 内的现行版** — 去掉 v 编号,文件名只含概念(如 `支线路径Wiki.md`、`产品设计文档.md`)
- **`archive/` 子目录** — 所有 v 编号历史版本,前缀为 `<name>.v<N>.<M>.md`
- 一份文档原则上只维护最新一版;旧版仅在需要回顾历史决策时才参考

### 🆕 coherence 子目录规则（v2.10.15）

- `coherence/YYYY-MM-DD-<topic>.md` — 稳定性 / 史实校验 / 一致性的"实测 + 审计 + 验证"三层文档
- 这些是 **跑完 LLM 才有写的事实** — 跟设计文档（architecture/）分离
- 标记**解决 vs 待修** — 解决后归档到 `coherence/archive/`（如果需要回顾）

### 维护规则

- 新版本文档 = `git mv` 旧现行版到 `archive/<name>.v<N>.<M>.md`,再 git mv 旧 archive 中最新版为新现行版
- 改一条决策?→ 更新 `01-decision-log.md`(追加,不覆盖)
- 写新工作日内容?→ 追加到 `log/YYYY-MM-DD_<topic>.md`
- 修一批 BUG?→ 在 `log/2026-07-12-v2.10.2-followup-summary.md` 追加 + 更新 `test/` 文档
- 跑出实测数据 / 完成审计?→ 加新文档到 `coherence/`

### 跨文档链接约定

- 引用上层 README:本目录的 `../README.md`
- 引用同层文档:`./<doc>.md` 或 `./<subdir>/<doc>.md`
- 引用 archive:保持 `./archive/<file>.md`

---

## 🆕 v2.10.15 coherence 子目录引入

| 改动 | 文件数 | 说明 |
|---|---|---|
| 新增 `coherence/` 子目录 | 5 文档 | 30 回合核对 + P0 修复验证 + stall 终极分析 + v2.10.13 验证 + Anachronism 审计 |
| 新增 `marketing/` 子目录 | 1 文档 | Zhihu 推广文（含 6.5 工程笔记"debug 明代游戏"） |
| 新增 `deploy/FRONTEND_MISMATCH_ANALYSIS.md` | 1 文档 | v2.10.10 前后端对接分析 |
| 新增 `log/2026-07-19-...` | 2 文档 | v2.10.10-11 上线后 followup |
| 新增 `log/2026-07-20-22` | 5 文档 | v2.10.12-15 稳定性 + 史实校验工作 |

---

## 🆕 历次重构

| 版本 | 日期 | 改动 |
|---|---|---|
| **v2.10.15** | 2026-07-22 | 新增 `coherence/` + `marketing/`,5 篇 audit |
| **v2.10.2 W52** | 2026-07-12 | 新增 test/deploy/release,重写 README |
| **v1.7.29** | 早期 | 产品设计文档归档(4→1+3 archive) |
| **v1.7.29** | 早期 | 支线路径 Wiki 归档(5→1+4 archive) |
| **v1.7.29** | 早期 | 设计/能力文档聚类(5→ design/) |
| **v1.7.29** | 早期 | 时代知识聚类(4→ eras/万历十五年/) |

---

依据 v2.10.15 同步更新（commit `d833199` 之后）
