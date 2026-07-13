# 📚 历史注脚 HFE · 文档索引

> **新开发者入口**：从 [`../README.md`](../README.md) 开始。
> **本目录**包含所有项目文档,按职责分层(v2.10.2 重新整理)。

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
│   ├── v2.10.1-W85-涌现式章节设计.md  ← 🆕 现行版
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
├── test/                          ← 🆕 测试 / 质量
│   ├── README.md
│   ├── v2.10.2-comprehensive-test.md       ← 综合测试
│   ├── v2.10.2-bug-prevention-analysis.md  ← BUG 模式分析
│   └── v2.10.2-frontend-audit.md          ← 前端审计
│
├── deploy/                        ← 🆕 部署 / 运维
│   └── DEPLOYMENT_GUIDE.md        ← 5 步 + 10 问题
│
├── release/                       ← 🆕 版本说明
│   ├── README.md
│   ├── v2.10.1-release-notes.md
│   └── v2.10.2-release-notes.md
│
├── log/                           ← 工作日志(按日期)
│   ├── README.md
│   ├── 2026-07-12-v2.10.2-followup-summary.md  ← 🆕 W52 followup 全量总结
│   ├── 2026-07-12-HFE-W52-优化清单-v1.0.md
│   ├── 2026-07-12-W85-Phase23-真LLM-smoke.md
│   ├── 2026-07-11_v2.8.0-段六-真LLM-收尾-work-log.md
│   ├── 2026-07-10_v2.8.0-段一-work-log.md
│   ├── 2026-07-09_v2.5-v2.7-work-log.md
│   ├── 2026-07-07_v1.9.1-4-work-log.md
│   ├── 2026-07-06_structured-io-analysis.md
│   └── 2026-07-05_v1.7.20-26-work-log.md
│
├── 01-decision-log.md             ← 项目关键决策
├── WORK_SUMMARY.md                ← v1.6+ 阶段总结
├── ISSUES.md                      ← 已知问题
├── CHANGELOG.md                   ← 完整变更日志
├── INTEGRATION_TODO.md            ← 集成 TODO
├── stress_test_report_v1.7.28.md  ← 压测报告
└── 调研成果汇报.md                ← Disco Elysium 调研
```

---

## 🎯 快速定位

### 🚀 我是新开发者

| 我想了解... | 看这里 |
|---|---|
| **项目基础信息** | [`../README.md`](../README.md) |
| **架构与功能设计** | [architecture/产品设计文档.md](architecture/产品设计文档.md) |
| **HTTP API 字段规范** | [api/FIELD_REGISTRY.md](api/FIELD_REGISTRY.md) |
| **HTTP API 端点清单** | [api/openapi.yaml](api/openapi.yaml) |
| **时代背景与剧情知识** | [eras/万历十五年/](eras/万历十五年/) |
| **如何部署?** | [deploy/DEPLOYMENT_GUIDE.md](deploy/DEPLOYMENT_GUIDE.md) |

### 🐛 排查 BUG

| 我想... | 看这里 |
|---|---|
| **了解 BUG 根因模式** | [test/v2.10.2-bug-prevention-analysis.md](test/v2.10.2-bug-prevention-analysis.md) |
| **查看测试覆盖** | [test/v2.10.2-comprehensive-test.md](test/v2.10.2-comprehensive-test.md) |
| **看前端旧代码** | [test/v2.10.2-frontend-audit.md](test/v2.10.2-frontend-audit.md) |
| **报告问题** | [`../ISSUES.md`](../ISSUES.md) |

### 📅 看开发历史

| 时段 | 看这里 |
|---|---|
| **v2.10.2 W52 followup (今天)** | [log/2026-07-12-v2.10.2-followup-summary.md](log/2026-07-12-v2.10.2-followup-summary.md) |
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

---

## 📐 文档约定

### 现行版 / 历史版规则

- **`子目录/` 内的现行版** — 去掉 v 编号,文件名只含概念(如 `支线路径Wiki.md`、`产品设计文档.md`)
- **`archive/` 子目录** — 所有 v 编号历史版本,前缀为 `<name>.v<N>.<M>.md`
- 一份文档原则上只维护最新一版;旧版仅在需要回顾历史决策时才参考

### 维护规则

- 新版本文档 = `git mv` 旧现行版到 `archive/<name>.v<N>.<M>.md`,再 git mv 旧 archive 中最新版为新现行版
- 改一条决策?→ 更新 `01-decision-log.md`(追加,不覆盖)
- 写新工作日内容?→ 追加到 `log/YYYY-MM-DD_<topic>.md`
- 修一批 BUG?→ 在 `log/2026-07-12-v2.10.2-followup-summary.md` 追加 + 更新 `test/` 文档

### 跨文档链接约定

- 引用上层 README:本目录的 `../README.md`
- 引用同层文档:`./<doc>.md` 或 `./<subdir>/<doc>.md`
- 引用 archive:保持 `./archive/<file>.md`

---

## 🆕 v2.10.2 W52 followup 整理(2026-07-12)

| 改动 | 文件数 | 说明 |
|---|---|---|
| 新增 test/ 子目录 | 3 文档 | BUG 根因 / 综合测试 / 前端审计 |
| 新增 deploy/ 子目录 | 1 文档 | 5 步部署 + 10 问题 |
| 新增 release/ 子目录 | 2 文档 | v2.10.1 / v2.10.2 release notes |
| 新增 log/2026-07-12 followup | 1 总结 | W52 followup 全量 |
| 移动 architecture/ | 3 个设计文档 | 从 docs/ 移到 docs/architecture/ |
| 移动 design/ → architecture/ | 整个目录改名 | 语义更准 |

---

## 🆕 历次重构

| 版本 | 日期 | 改动 |
|---|---|---|
| **v2.10.2 W52** | 2026-07-12 | 新增 test/deploy/release,重写 README |
| **v1.7.29** | 早期 | 产品设计文档归档(4→1+3 archive) |
| **v1.7.29** | 早期 | 支线路径 Wiki 归档(5→1+4 archive) |
| **v1.7.29** | 早期 | 设计/能力文档聚类(5→ design/) |
| **v1.7.29** | 早期 | 时代知识聚类(4→ eras/万历十五年/) |

---

依据 v2.10.2 W52 followup 重构
