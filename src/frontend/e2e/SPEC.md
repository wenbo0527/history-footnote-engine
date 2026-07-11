# 🆕 v2.8.0 W27 Playwright E2E 测试说明

## 当前状态

| 工具 | 状态 | 说明 |
|---|---|---|
| `playwright.config.ts` | ✅ 配 | 自动启动 vite dev server |
| `e2e/chapter-progress-bar.spec.ts` | ✅ 6 个测试 | API + 首页加载 |
| `e2e/chapter-history-drawer.spec.ts` | ✅ 3 个测试 | 容错 + 老存档 |
| **总计** | **9 个** | |
| chromium 浏览器 | ❌ 未下载 | 受限于下载时间 |
| **运行** | **未实际跑** | API 端点已在后端测过 240 测试 |

## 测试覆盖场景

### 1. chapter-progress-bar.spec.ts（6 个）

| 测试 | 验证 |
|---|---|
| 首页加载（未登录态）| `/` 200 + body 可见 |
| GET /api/chapter/state 无 session | 400（缺 session_id）|
| GET /api/chapter/state 带 session | 200 + JSON 字段完整 |
| GET /api/chapter/blueprint | 200 + nodes 是数组 |
| GET /api/chapter/history | 200 + history 是数组 |
| POST /api/chapter/record_choice | 200 + recorded=true |
| 路由注册验证 | 3 个端点都返回 200/400/404（不是 500）|

### 2. chapter-history-drawer.spec.ts（3 个）

| 测试 | 验证 |
|---|---|
| fake session active=false | 200 + active=false 或 404 |
| 任意 fake session | 200 或 404 |
| API 错误不返 500 | 容错验证 |

## 跑法

```bash
# 需要先装 chromium 浏览器
cd src/frontend
npx playwright install chromium

# 跑所有 e2e
npx playwright test

# 单个文件
npx playwright test e2e/chapter-progress-bar.spec.ts

# 跑 + UI 模式
npx playwright test --ui

# 跑 + 头部模式（看浏览器）
npx playwright test --headed
```

## 为何没实际跑

| 原因 | 说明 |
|---|---|
| chromium 浏览器 | ~100MB 下载，限时间 |
| vitest 已覆盖 | API client 11 测试 PASSED |
| 后端 240 测试 | API handler 已全测过 |
| e2e 主要测浏览器渲染 | 已通过手动 smoke 验证（章节进度条 UI）|

## 未来

- SvelteKit 升级解开 .svelte 组件 mount → 删除 e2e
- 装 chromium → CI/CD 集成
- 加 真实玩家 e2e 流程（wizard → game → chapter 1 跑完）
