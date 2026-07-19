# 🆕 v2.10.9 docs/ 归档目录统一索引

> **何时查归档？**
> - 当前文档找不到你想了解的设计决策 → 查 `architecture/archive/`
> - 想看历史版本的 CHANGELOG → 查 `_archive/`
> - 想参考调研报告是否被项目采纳 → 查 `log/unused-references/` (未采纳) 或 `log/used-references/` (已采纳)
> - 想看历史时代包的设计稿 → 查 `eras/<era_id>/archive/`
> - 想看后续版本规划（v2.10.12+）→ 查 `plans/ROADMAP.md`

---

## 📦 五个归档目录速查

### 1. `docs/_archive/` — 历史里程碑记录（10 文件）

| 文件 | 用途 | 何时查 |
|---|---|---|
| `CHANGELOG_v1.7.28_29.md` | v1.7.28/29 变更日志 | 想了解 v1.7 末期做了什么 |
| `CHANGELOG_v1.7.30.md` | v1.7.30 变更日志 | 想了解 v1.7.30 重大重构 |
| `CREATE_GITHUB_RELEASE_v2.8.0.md` | v2.8.0 发布流程纪要 | 想了解 release 流程 |
| `INTEGRATION_P2_v1.7.30.md` | v1.7.30 P2 集成 | 想了解 P1/P2/P3 怎么落地 |
| `INTEGRATION_TODO.md` | 历史待办列表 | ~~不查（已废）~~ |
| `W33_VOICE_QA.md` | W33 周 QA | 想了解 voice 选项设计 |
| `WKHTMLTOPDF_NOTES.md` | wkhtmltopdf 笔记 | 想了解 PDF 生成方案 |
| ... | | |

> **当前 CHANGELOG** 看 `CHANGELOG.md`（项目根），不要看这里的旧 CHANGELOG。

### 2. `docs/architecture/archive/` — 架构决策历史（13 文件）

| 文件 | 用途 | 何时查 |
|---|---|---|
| `README.md` | archive 目录说明 | 想了解归档策略 |
| `v2.7-DM-agent性能分析.md` | DM agent 性能瓶颈分析 | 想了解为什么拆 skills |
| `v2.7-DM-agent拆分决策纪要.md` | DM agent 8 skill 拆分决策 | 想了解 skill 编排由来 |
| `v2.8-前端分流方案.md` | 流式响应方案 | 想了解 SSE 实现 |
| `v2.8-套餐计费方案.md` | 计费设计（未落地） | ~~不查（未实现）~~ |
| `v2.9-前端测试方案.md` | Vitest + Playwright 选型 | 想了解测试栈 |
| `v2.10.5-路由分层重构.md` | P0-1 重构纪要 | 想了解本次重构 |
| `v2.10.6-部署分析.md` | 部署方案分析 | 想了解部署背景 |
| `v2.10.8-Pydantic era 校验设计.md` | 🆕 v2.10.9 决策 | 想了解 P0-2 为何这么做 |
| ... | | |

> **当前架构文档** 看 `docs/architecture/` 顶层（不要看 archive）。

### 3. `docs/eras/万历十五年/archive/` — 时代包历史设计稿（5 文件）

| 文件 | 用途 | 何时查 |
|---|---|---|
| `README.md` | archive 目录说明 | 想了解归档策略 |
| `支线路径Wiki.v1.0.md` | 支线路径设计 v1 | 想看支线演化 |
| `支线路径Wiki.v2.0.md` | 支线路径设计 v2 | 想看支线演化 |
| `支线路径Wiki.v3.0.md` | 支线路径设计 v3（最终） | 想了解万历的支线 |
| `剧情钩子集合.md` | 初期剧情钩子集 | 想看创作早期素材 |

> **当前时代设计** 看 `docs/eras/万历十五年/README.md` 和 `eras/wanli1587/era.json`。

### 4. `docs/log/unused-references/` — 未采纳的调研（11 文件）

> **如何使用**：这些是项目评估过但**最终没有采纳**的方案或观点。
> 查这些文档能找到"为什么不用 X"，防止重新评估已否决的方案。

| 文件 | 用途 | 何时查 |
|---|---|---|
| `2026-07-07_research_review.md` | 当天研究综述 | 想看当天调研过什么 |
| `万历年间影响玩家的大事件：从盛泽织户视角看天下变局.md` | 万历时代素材调研 | 想看历史背景调研 |
| `分析报告：高自由度RPG引擎中AI与事件总线的边界划分.md` | AI/事件总线边界 | 想了解为什么不用某种方案 |
| `分析报告：Agent缓存选型对比.md` | KV cache 选型 | 想了解 cache 决策 |
| `调研报告：LangGraph适合做DM-Agent吗？.md` | LangGraph 评估 | 想了解为什么选 LangGraph |
| `调研报告：MiniMax-LLM-vs-Claude-vs-GPT4对比.md` | LLM provider 对比 | 想了解为什么支持多种 provider |
| `调研报告：Pydantic-vs-DataClass-for-era-json.md` | era schema 选型 | 想了解为什么 P0-2 用 Pydantic |
| ... | | |

> **配套目录** `docs/log/used-references/` 是已采纳的方案。

### 5. `docs/log/used-references/` — 已采纳的调研（3 文件）

> **如何使用**：这些是项目**实际采纳**的方案或落地路径。
> 想了解"项目怎么从调研变成代码"的链路，看这里。

| 文件 | 用途 | 何时查 |
|---|---|---|
| `2026-07-07-history-footnote-admin-auth-v2-方案-A-bcrypt-session-v1.0.md` | 管理员 auth v2 方案 A（bcrypt + session） | 想了解 admin auth 决策 |
| `2026-07-07-history-footnote-admin-auth-v2-方案-A-scrypt-session-v1.1.md` | 同上 v1.1（scrypt 替代 bcrypt） | 想了解密码 hash 升级 |
| `调研报告：特定场景下Agent越用Token消耗越少是否可能？.md` | Agent token 优化调研 | 想了解 KV cache 落地原因 |

---

## 🆕 v2.10.9 归档策略说明

### 归档原则

1. **不删除**：所有归档文件都保留（用 `git mv` 保留 git 历史）
2. **可恢复**：任何归档都能从 git log 找回
3. **可追溯**：归档文件加上迁移注释（`🆕 v2.x.y: 归档说明`）
4. **不引用**：当前文档不引用归档（防止循环）

### 何时归档

| 触发条件 | 归档位置 |
|---|---|
| 文档被新版本完全替代 | `_archive/` |
| 架构设计决策落地 >3 个月且有新方案 | `architecture/archive/` |
| 时代包设计稿被新版本替代 | `eras/<era>/archive/` |
| 调研报告评估完成 | `log/used-references/` (采纳) 或 `log/unused-references/` (否决) |

### 何时查阅

| 场景 | 查这里 |
|---|---|
| 当前文档找不到答案 | 所有 archive |
| 想了解决策历史 | `architecture/archive/` |
| 想了解调研结论 | `log/used-references/` + `log/unused-references/` |
| 想了解历史版本变更 | `_archive/CHANGELOG_v*` |

### 归档不能放什么

- ❌ 当前在用的文档（应放顶层）
- ❌ 测试用例（应放 `tests/`）
- ❌ 临时调试日志（应放 `.gitignore`）
- ❌ 大量图片/二进制（应放对象存储）

---

## 🔍 快速搜索技巧

```bash
# 查某个关键词在所有 archive 的出现
grep -rl "kwarg" docs/_archive docs/architecture/archive docs/eras/*/archive docs/log

# 找最近归档的文件
ls -lat docs/_archive/ | head -10

# 查 CHANGELOG 历史
ls docs/_archive/CHANGELOG_v*
```