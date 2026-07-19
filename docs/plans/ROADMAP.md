# 🗺️ v2.10.11+ 后续版本路线图

> **更新时间**：2026-07-19
> **基于**：v2.10.11 已上线 `origin/main`（commit `5f1b7d4`）
> **作者**：Trae IDE + history_footnote 工程
> **目的**：把"未规划的事"沉淀成可评审路线图，方便 PR / 决策 / 排期
>
> **如何用本路线图？**
> - 看到某个版本想动手 → 复制成 `docs/plans/vX.Y.Z.md`
> - 路线有调整 → 更新本文件
> - 完成后 → 在 CHANGELOG 写一条，把状态（草案 / 进行中 / 已完成）改

---

## 📊 现状快照（v2.10.11 后）

**已上线**：v2.10.11（含 v2.10.10 前端切换 + v2.10.11 SPA fallback）

| 项 | 状态 | 来源 |
|---|---|---|
| 静态资源 character | ✅ 7/7 完成 | TODO v2.7.1 |
| 静态资源 fate card | ✅ 40/40 完成（超 36 计划） | TODO v2.7.1 |
| 静态资源 scene | ✅ 3/3 米黄背景 | TODO v2.7.1（可考虑透明升级） |
| 防回归测试 | ✅ v2.10.10 静态回归测试 | test_v21010_sveltekit_index_html.py |
| E2E HTTP 测试 | ✅ 9 场景 | test_v21010_e2e_http_smoke.py |
| CI 接 e2e | ❌ CI.yml 只跑 pytest tests/，缺 conda 装 + e2e 集成 | ci.yml |
| CI 接 scripts/tests | ❌ 101 个 scripts/test_*.py 没被 CI 跑 | 调查发现 |
| 可观测 / 结构化日志 | ❌ 当前用 stdlib logging | docs/architecture/archive |
| 多时代扩展 | ❌ 仅 wanli1587 一个时代 | docs/eras/ |
| OpenTelemetry / 性能监控 | ⚠️ 仅有 analytics.py 局部代码，未串联 | 调查 |
| 部署 workflow | ✅ v2.10.9 已配 | deploy.yml |

---

## 🎯 版本优先级（按 ROI 排序）

### ⭐⭐⭐⭐⭐ v2.10.12 — CI/CD 增强（**建议立即开始**）

**估时**：3-5 天
**动机**：e2e 已经证明（v2.10.11）这类自动化测试能找到真 bug，**让所有 push 都跑这测试** 才能防 regression。

**P0（必做）**：
1. **CI.yml 接 e2e HTTP 测试**
   - 安装 conda + langchain（参考 deploy.yml 的 setup-python）
   - `tests/test_v21010_e2e_http_smoke.py` 9 场景全跑
   - fail-fast：1 个失败 → merge 阻塞
2. **CI.yml 接 scripts/test_\*.py（offline 部分）**
   - 用 `grep -L "minimax\|deepseek\|api\."` 过滤不需 LLM 的
   - 跑 `python scripts/test_X.py`，exit code 计入
3. **Coverage 报告**
   - pytest 加 `--cov=src --cov-report=term-missing --cov-fail-under=70`
   - threshold 放 70 起步，逐步 +5 提
4. **Release Drafter 自动化**
   - 用 `.github/release-drafter.yml`
   - 自动归纳"Next version"

**P1（待商榷）**：
- [ ] `tests/` 子目录分组（按 v2.10.X），方便 review
- [ ] OpenAPI drift-check（防 API 改了但 docs 漏）
- [ ] Draft Release 模板（vs. 直接 release 切 tag）

**验收**：
- PR 触发 CI，全绿才可 merge
- Coverage ≥ 70%
- 接下来的 push 任何 break，都被 CI 拦住

---

### ⭐⭐⭐⭐ v2.10.13 — 可观测 + 性能

**估时**：5-7 天
**动机**：上线后用户反馈"加载慢 / 502"时，**无 metric 没法定位**。

**P0**：
1. **结构化日志**：替换 stdlib `logging` 为 `structlog`
   - 所有 `logger.info(...)` 改 `log.info(event="xxx", key=value)`
   - 输出 JSON，便于 ELK / Loki 收
2. **OpenTelemetry trace**：
   - 包 LLM invoke（minimax / deepseek 真实耗时）
   - 包 router dispatch（路由到 handler 的耗时）
   - 包 session.get / session.set（session pool 性能）
3. **Prometheus /metrics 端点**：
   - verify 现有 `routers/admin_settings.py` 是否有 `/metrics`
   - 加：LLM call count / latency / token usage
4. **Web Vitals 上报**：
   - FCP / LCP / TTI / CLS
   - SvelteKit hooks.server.ts 已部分实现，verify 上报通路

**P1**：
- [ ] Alerting 规则：5xx > 1% / LLM P95 > 30s / 首页 P95 > 3s
- [ ] **Admin 面板 RUM**（v2.10.9 W47 已有雏形，看完善度）

---

### ⭐⭐⭐⭐ v2.11.0 — 第二个时代包

**估时**：2-3 周
**动机**：wanli1587 是单一年份/事件，扩时代包 = 直接增加游戏可玩性 / 重玩价值

**候选时代**（按 ROI）：

| 朝代 | 戏剧冲突 | 兼容性 |
|---|---|---|
| **崇祯二年（1629）** | 农民起义 + 后金入侵 + 饥荒，明亡前夜 | ⭐⭐⭐⭐⭐ |
| **永乐年间（1403）** | 郑和下西洋、万国来朝，史诗感 | ⭐⭐⭐⭐ |
| **景泰年间（1450）** | 土木堡之变后、英宗复辟、夺门之变 | ⭐⭐⭐ |
| **嘉靖年间（1560）** | 海瑞罢官、严嵩专权 | ⭐⭐⭐ |

**建议先做**：`崇祯二年（1629）` —— 戏剧张力最大 + 玩家决策影响最明显（可"救明"或"加入"）

**P0**：
1. EraValidator schema 校验（事件、role、skill 复用 wanli1587）
2. EraLoader 改 multi-root（同时挂载多 era）
3. UI 加 `EraPicker`（首次进入游戏时选时代，存档 era 持久化）
4. 5-10 个关键事件 mock（不到 100+，先 MVP）
5. Document：`docs/eras/chongzhen1629/README.md`

**P1**：
- [ ] 第二次上线 e2e 加场景："用户选崇祯 → 进入游戏"
- [ ] 时代切换时的 state 重置逻辑

---

### ⭐⭐⭐ v3.0.0-A 多语言支持

**估时**：1-1.5 月
**动机**：海外用户 / 英文社群拓展

**P0**：
- [ ] 提取中文字符串到 `i18n/zh.json` / `i18n/en.json`
- [ ] svelte-i18n 集成（前后端共用 key）
- [ ] `lang` query param / cookie
- [ ] LLM prompt 根据语言切换

**P1**：
- [ ] 第三时代：英文（wanli1587_en 为起手）
- [ ] 语言切换 ad-hoc 检测（IP / browser）

---

### ⭐⭐⭐ v3.0.0-B PWA + 离线

**估时**：2-3 周
**动机**：用户网络不稳地区（明朝玩家普遍处于移动端？），离线存档继续游戏

**P0**：
- [ ] Service Worker（前端 SvelteKit 已部分支持）
- [ ] IndexedDB 离线存档
- [ ] 离线模式"本地 mock LLM"
- [ ] PWA manifest.json + icon

---

### ⭐⭐ v3.0.0-C 多玩家协作

**估时**：2-3 月
**动机**：单 DM 一玩家已经 9/9 pass e2e，扩展性瓶颈在互动深度

**P0**：
- [ ] WebSocket 后端（替代单方向 HTTP/SSE）
- [ ] 房间系统：玩家同处一时代
- [ ] DM Agent 多玩家输入适配
- [ ] 共同结局 + 个人结局

**风险高**（路由、并发、一致性），建议延后到 v2.11 后看玩家反馈再决定

---

## 📝 决策待解（需用户/PM 拍板）

1. **v2.10.12 CI conda 装环境**，还是直接 docker 化 CI？
   - 现有 CI 是 `setup-python@v5` + pip
   - 装 conda 在 CI 增加复杂度，但 e2e 强依赖 conda
   - 改 docker 跑（项目已有 Dockerfile）一致性更高
2. **v2.11.0 选哪个时代**？（已建议崇祯，等业务确认）
3. **v3.0 路线 A/B/C 优先级**？（出海 / 离线 / 多人）
4. **是否本地 mock voice 音频**？（目前后端调 minimax TTS，可考虑本地 espeak）

---

## 🗓 建议排期

**本周 (2026-07-19 ~ 2026-07-25)**
- v2.10.12 启动
- CI 接入 e2e test_v21010_e2e_http_smoke.py
- 接 scripts/test_*.py（offline 子集）

**下周 (2026-07-26 ~ 2026-08-01)**
- Coverage 上 70%
- Release Drafter 配上

**8 月上旬**
- v2.10.13 可观测
- 8/15 上 v2.10.13 到 staging

**8 月中旬 - 9 月中旬**
- v2.11.0 第二个时代（崇祯二年）
- 9/30 v2.11.0 GA

**Q4 (10-12 月)**
- v3.0.0 多语言/PWA/多玩家 三选一

---

## 🛠 PR / Commit 模板

**v2.10.x 修复型**：
```
fix(<scope>): <一句话>

根因：...
修复：...

回归测试：tests/test_v21010_xxx.py
```

**v2.10.x 功能型**：
```
feat(<scope>): <一句话>

新增：...
影响：...

e2e 覆盖：tests/test_v21010_xxx.py
```

**v3.0 重大**：
```
<type>(scope): !

docs/plans/v3.0.0-x.md 是 RFC 记录
迁移指南：docs/MIGRATION.md
```

---

## 📚 相关文档

- [CHANGELOG.md](../../CHANGELOG.md) — 历史变更
- [ISSUES.md](../../ISSUES.md) — 问题与解决
- [docs/architecture/v2.7.1-后续TODO.md](../architecture/v2.7.1-后续TODO.md) — 旧版 TODO（已部分完成）
- [docs/deploy/DEPLOYMENT_GUIDE.md](../deploy/DEPLOYMENT_GUIDE.md) — 部署指南
- [docs/deploy/FRONTEND_MISMATCH_ANALYSIS.md](../deploy/FRONTEND_MISMATCH_ANALYSIS.md) — 前端 mismatch 分析（v2.10.10 修复）

---

## ✅ 决策日志

| 日期 | 决策 | 影响 |
|---|---|---|
| 2026-07-19 | **v2.10.12 优先开始**（CI/CD 增强） | 防 regression，覆盖 e2e 发现的核心价值 |
| 2026-07-19 | 路线图文档化到 docs/plans/ROADMAP.md | 后续决策有参照 |
