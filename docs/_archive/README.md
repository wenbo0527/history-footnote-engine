# 📦 docs/_archive/ · 项目级归档

> **目的**：归档**项目根目录**和 **docs/ 根目录**的过期 / 一次性文档
> **区别于**：`docs/<sub>/archive/` 是各子目录（如 architecture/、万历十五年/）自己的版本历史

---

## 📋 归档清单

### 根目录 → docs/_archive/

| 原文件 | 归档后 | 归档时间 | 原因 |
|---|---|---|---|
| `RELEASE_NOTES_v2.8.0.md` | [RELEASE_NOTES_v2.8.0.md](RELEASE_NOTES_v2.8.0.md) | 2026-07-15 | v2.8.0 release notes（已被 v2.10.x 超越） |
| `CREATE_GITHUB_RELEASE.md` | [CREATE_GITHUB_RELEASE_v2.8.0.md](CREATE_GITHUB_RELEASE_v2.8.0.md) | 2026-07-15 | v2.8.0 一次性 GitHub Release 操作说明 |
| `WORK_SUMMARY.md` | [WORK_SUMMARY_legacy.md](WORK_SUMMARY_legacy.md) | 2026-07-15 | v1.6+ 阶段总结（已被 docs/log/ 系列取代） |

### docs/ 根目录 → docs/_archive/

| 原文件 | 归档后 | 归档时间 | 原因 |
|---|---|---|---|
| `docs/WORK_SUMMARY.md` | 同上（重复） | 2026-07-15 | 同上 |
| `docs/CHANGELOG_v1.7.28_29.md` | [CHANGELOG_v1.7.28_29.md](CHANGELOG_v1.7.28_29.md) | 2026-07-15 | v1.7 阶段变更日志（主 CHANGELOG.md 已覆盖） |
| `docs/CHANGELOG_v1.7.30.md` | [CHANGELOG_v1.7.30.md](CHANGELOG_v1.7.30.md) | 2026-07-15 | 同上 |
| `docs/INTEGRATION_P2_v1.7.30.md` | [INTEGRATION_P2_v1.7.30.md](INTEGRATION_P2_v1.7.30.md) | 2026-07-15 | v1.7.30 集成方案 |
| `docs/INTEGRATION_TODO.md` | [INTEGRATION_TODO.md](INTEGRATION_TODO.md) | 2026-07-15 | 旧集成 TODO（已不在用） |
| `docs/stress_test_report_v1.7.28.md` | [stress_test_report_v1.7.28.md](stress_test_report_v1.7.28.md) | 2026-07-15 | v1.7.28 压测报告 |
| `docs/调研成果汇报.md` | [调研成果汇报.md](调研成果汇报.md) | 2026-07-15 | Disco Elysium 调研报告（已被 docs/log/unused-references/ 系列取代） |

---

## 🎯 归档原则

### 何时归档

- **版本已过时**：被 ≥2 个 minor 版本超越（如 v2.8.0 现在 → v2.10.8）
- **一次性文档**：操作说明、临时 TODO、阶段总结（不持续维护）
- **重复内容**：主 CHANGELOG.md / docs/log/ 已包含的细节
- **未维护的调研**：超过 30 天未更新的调研报告

### 何时**不**归档（保留在 docs/）

- 现行版文档（去掉 v 编号）
- 项目级 README / 索引
- API 规范（openapi.yaml / FIELD_REGISTRY.md）
- 当前版本的 release notes（v2.10.x）

### 归档目录分层

| 层级 | 用途 |
|---|---|
| `docs/_archive/` | 项目级归档（根目录 + docs/ 根） |
| `docs/architecture/archive/` | 架构文档历史版本 |
| `docs/eras/万历十五年/archive/` | 时代知识历史版本 |
| `docs/log/unused-references/` | 调研参考归档 |
| `docs/log/used-references/` | 已使用的调研 |

---

## 📊 归档统计

- **本次归档**：9 个文档（2026-07-15）
- **历史归档**：12 个 architecture/，4 个 万历十五年/，11 个 log/unused，3 个 log/used
- **总计**：39 个文档已归档

---

依据 v2.10.8 整理