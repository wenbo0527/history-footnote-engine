# 📚 历史注脚体验引擎 · 文档索引

> **新开发者入口**：从 [`../README.md`](../README.md) 开始。
> **本目录**包含所有项目文档，按职责分层。

---

## 🗂️ 目录结构

```
docs/
├── README.md                       ← 本文件（顶层索引）
├── 01-decision-log.md              ← 项目关键决策记录（保留）
├── WORK_SUMMARY.md                 ← v1.6+ 阶段工作总结（保留）
├── 调研成果汇报.md                  ← Disco Elysium 模式调研（保留）
│
├── design/                         ← 引擎设计文档
│   ├── README.md
│   ├── 产品设计文档.md              ← 主文档（现行版）
│   ├── 核心交付物合集.md            ← 主文档全集
│   ├── AI DM SKILL体系.md
│   ├── AI DM 节奏控制.md
│   ├── DM 引导者行为模式.md
│   ├── Era Wiki Compiler 方案.md
│   └── archive/                    ← 历史版本
│       ├── 产品设计文档.v1.0.md
│       ├── 产品设计文档.v2.0.md
│       └── 产品设计文档.v3.0.md
│
├── eras/万历十五年/                  ← 万历时代包知识
│   ├── README.md
│   ├── 支线路径Wiki.md              ← 现行版（综合 v1.0~v5.0）
│   ├── 离乡路线Wiki.md
│   ├── 闲谈素材Wiki.md
│   ├── 知识条目集.md                ← Era Wiki Compiler 输入产物
│   └── archive/                    ← 历史版本
│       ├── 支线路径Wiki.v1.0.md
│       ├── 支线路径Wiki.v2.0.md
│       ├── 支线路径Wiki.v3.0.md
│       └── 支线路径Wiki.v4.0.md
│
├── api/                            ← HTTP API 文档
│   ├── FIELD_REGISTRY.md
│   └── openapi.yaml                ← 自动生成（scripts/generate_api_doc.py）
│
└── log/                            ← 工作日志（按日期）
    ├── README.md
    ├── 2026-07-05_v1.7.20-26-work-log.md
    ├── 2026-07-06_structured-io-analysis.md
    └── 2026-07-09_v2.5-v2.7-work-log.md  ← 🆕 命运卡完整闭环
```

---

## 🎯 快速定位

| 我想了解... | 看这里 |
|---|---|
| **项目基础信息** | `../README.md` |
| **架构与功能设计** | [design/产品设计文档.md](design/产品设计文档.md) |
| **AI DM 行为细节** | [design/DM 引导者行为模式.md](design/DM%20引导者行为模式.md) + [design/AI%20DM%20SKILL体系.md](design/AI%20DM%20SKILL体系.md) |
| **HTTP API 字段规范** | [api/FIELD_REGISTRY.md](api/FIELD_REGISTRY.md) |
| **HTTP API 端点清单** | [api/openapi.yaml](api/openapi.yaml) |
| **时代背景与剧情知识** | [eras/万历十五年/](eras/万历十五年/) |
| **历史决策与原因** | [01-decision-log.md](01-decision-log.md) |
| **本项目调研结论** | [调研成果汇报.md](调研成果汇报.md) |
| **阶段性工作总结** | [WORK_SUMMARY.md](WORK_SUMMARY.md) |
| **近期变更日志** | [log/](log/) |

---

## 📐 文档约定

### 现行版 / 历史版规则

- **`子目录/` 内的现行版** — 去掉 v 编号，文件名只含概念（如 `支线路径Wiki.md`、`产品设计文档.md`）
- **`archive/` 子目录** — 所有 v 编号历史版本，前缀为 `<name>.v<N>.<M>.md`
- 一份文档原则上只维护最新一版；旧版仅在需要回顾历史决策时才参考

### 维护规则

- 新版本文档 = `git mv` 旧现行版到 `archive/<name>.v<N>.<M>.md`，再 git mv 旧 archive 中最新版为新现行版
- 改一条决策？→ 更新 `01-decision-log.md`（追加，不覆盖）
- 写新工作日内容？→ 追加到 `log/YYYY-MM-DD_<topic>.md`

### 一些跨文档链接的约定

- 引用上层 README：本目录的 `../README.md`
- 引用同层文档：`./<doc>.md` 或 `./<subdir>/<doc>.md`
- 引用 archive：保持`./archive/<file>.md`

---

## 🆕 最近一次重构（v1.7.29）

| 改动 | 文件数 | 说明 |
|---|---|---|
| 产品设计文档归档 | 4 → 1 + 3 archive | v1.0/v2.0/v3.0 移到 `design/archive/`，v3.1 → `设计文档.md` |
| 支线路径 Wiki 归档 | 5 → 1 + 4 archive | v1.0~v4.0 移到 `eras/万历十五年/archive/`，v5.0 → `支线路径Wiki.md` |
| 设计/能力文档聚类 | 5 散落 → `design/` 子目录 | DM/SKILL/节奏/Compiler 等集中 |
| 时代知识聚类 | 4 散落 → `eras/万历十五年/` 子目录 | 支线/离乡/闲谈/知识条目集集中 |

---

## 🆕 v2.5-v2.7 · 命运卡完整闭环（2026-07-09）

> **范围**：13 个 commit · 66 个测试 · 0 回归 · 详见 [log/2026-07-09_v2.5-v2.7-work-log.md](log/2026-07-09_v2.5-v2.7-work-log.md)

### 4 大主题

| 主题 | 涉及版本 | 关键价值 |
|---|---|---|
| **命运卡基础** | v2.5 + v2.6 | 抽卡 + 主动使用 + 应急弹出 |
| **双向感知** | v2.6.1 + v2.6.2 | DM 知道玩家用过 + 玩家知道影响 |
| **完全可重放** | v2.7 (L9) | LLM temperature=0 + seed 100% 复现 |
| **测试基础设施** | v2.7 (L1-L4, L9) | 整合+边界+E2E+重放+温度= 39 个新测试 |

### 命运卡"感知闭环"成就

```
玩家抽卡    →  用卡    →  DM 知道    →  玩家看见影响    →  同 seed 重玩
v2.5 抽     v2.6 主动   v2.6.1 prompt  v2.6.2 档案     v2.7 100%
```

### 测试规模

| 类别 | 数量 |
|---|---|
| 后端单元 (v2.5 之前) | 22 |
| L1 整合 (v2.7) | 12 |
| L2 E2E mock (v2.7) | 5 |
| L3 E2E 真实 LLM (v2.7) | 3 |
| L4 边界 (v2.7) | 8 |
| L9 重放 (v2.7) | 5 |
| temperature 控制 (v2.7) | 5 |
| 前端 vitest (v2.7) | 6 |
| **总计** | **66** |

### 修的 3 个真 BUG

| BUG | 原因 | 修复 |
|---|---|---|
| CharCard 命运卡段不显示 | mapper.ts 漏字段 | `fa8fdbf` |
| 加载存档命运卡丢失 | session 创建后没 save_state | `ab3cbf7` |
| 同 seed 输出不同 | LLM temperature 默认 | `2bcaa52` |
