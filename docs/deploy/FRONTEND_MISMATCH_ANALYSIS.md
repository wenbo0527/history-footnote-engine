# 🆕 v2.10.9 前端错位深度诊断

> **结论先行**：项目里同时存在两套前端，**生产部署的是旧的 v1.7.27**（单 HTML + JS），
> **v1.7.32+ 的 SvelteKit 前端是死代码**（没人引用，修了等于没修）。
>
> **建议**：采用方案 A（删死代码）或方案 B（启用 Svelte）。本文帮你决策。

---

## 一、问题现场（实际审计）

我做了完整审计，下面是事实，不是猜测。

### 实际服务的版本：v1.7.27（旧）

| 文件 | 状态 |
|---|---|
| `src/history_footnote/web/templates/index.html` | v1.7.27（注释 v1.3.1，标签 v1.7.27） |
| `src/history_footnote/web/static/css/main.css` | v1.x 风格 |
| `src/history_footnote/web/static/js/main.js` | v1.x 风格 |
| **服务方** | `web_server/static_assets.py` 把 index.html 读到内存变量 `INDEX_HTML`，启动时一次性加载；`handler_base._serve_static()` 服务 `/static/*` |

### 实际死代码：v1.7.32+ SvelteKit

| 文件 | 状态 |
|---|---|
| `src/frontend/build/` | SvelteKit adapter-static 产物（v1.7.32+），没人读 |
| `src/frontend/static/` | character/fate/icons，**没人引** |
| `src/frontend/src/lib/api/mapper.ts` | v2.10.7 修的 Svelte 错误，**没人引** |
| `src/frontend/package.json` | 含 21 项 dev deps（@sveltejs/kit, vite, vitest, playwright, ...），**没人装** |
| `src/frontend/node_modules/` | ~300 MB，**算入了 git ignore 但每次 docker build 都重装** |

**！证据**：`grep -r "src/frontend" src/`
→ 只命中 `src/history_footnote/events/fate/cards.py`（代码注释里写了路径字符串），以及 `src/frontend/...` 自引用
→ **后端代码完全不依赖 src/frontend**

---

## 二、当前部署的真实效果

### Docker 部署（用户最可能用的方案）

```bash
docker build -t hfe-app .
docker run -d --name hfe --env-file .env hfe-app
```

实际发生：
1. **Stage 1 浪费**：`npm ci` + `npm run build` 产出 `src/frontend/build/`，**没人会读它**
2. **Stage 2 部分浪费**：`COPY src/frontend/build/ /app/static/` 也是浪费
3. **Stage 2 真正有效**：`COPY src/ ./src/` → 后端跑起来
4. 用户访问 → 后端返 INDEX_HTML（**v1.7.27**） → **用户看到的是 30+ 版本之前的 UI**

**Docker 镜像体积估算**：
- 不必要：node_modules ~300 MB + frontend build ~5 MB + frontend src ~3 MB = ~308 MB
- 必要：python deps ~200 MB + 项目代码 ~5 MB = ~205 MB
- **结果：~40% 体积浪费**

### deploy.sh 部署（systemd + nginx）

```bash
sudo bash deploy/deploy.sh
```

实际发生：
1. `build_frontend()`：`npm ci` + `npm run build`（**死代码构建**）
2. `rsync src/frontend/build/ /var/www/hfe/build/` ← **路径错！**
3. nginx `root /var/www/hfe`，`location /` → `try_files $uri $uri/ /index.html`
4. `/var/www/hfe/index.html` 不存在 → fallthrough 到同名文件 → **404**

**nginx 这条路完全 404！用户必须绕过 nginx 直接访问 `:8765`，看到的还是 v1.7.27。**

部署文件逻辑 bug 列表：
- `deploy/deploy.sh:138` — `rsync src/frontend/build/ /var/www/hfe/build/` 应该是 `/var/www/hfe/` 或删掉
- `deploy/nginx.conf` 的 `location /` 引用 SvelteKit adapter-static 产物（`/var/www/hfe/build/`），但部署脚本用的是 `/var/www/hfe/build/`，路径错配
- 实际上即使用户访问 `:8765`，后端 `INDEX_HTML` 指向 `src/history_footnote/web/templates/index.html`，不是 Svelte 产物

---

## 三、代价盘点

### 1. 用户体验错位

| 之前在做什么 | 用户实际看到 |
|---|---|
| v2.10.7 修 Svelte 错误（mapper.ts）| 没生效 |
| v1.7.32 移除 Google Fonts | 没生效 |
| v2.10.8 移动端 5 处适配 | 没生效 |
| v2.10.6 开局剧情带入 | 没生效 |
| v1.8+ cookie/session 安全 | 没生效 |

**生产部署的 UI 是 v1.7.27**（~30+ 版本之前）。

### 2. 资源浪费

- Docker 镜像 ~40% 体积多余
- CI build 多 5-10 分钟
- deploy.sh 多装 nodejs + npm ci

### 3. 误导新人

- README.md 让新人 `cd src/frontend && npm run dev` → 跑通了但和生产无关
- 前端 PR 合并后看不到生产效果
- `mapper.ts` 修了没人发现"修了等于没修"

---

## 四、问题根源（架构历史回放）

```
v1.3 (2025-09)        单 HTML + 静态 JS 前端 ← src/history_footnote/web/
v1.4 (~2025-11)        web_server.py 单文件后端
v1.6 (~2026-01)        src/frontend/ 立项 v2 Svelte
                       ↑ 但没同步改后端 INDEX_HTML 加载逻辑！
v1.7                   两套前端并行存在
v2.x                   持续在 src/frontend/ 加功能 ← 持续死代码
v2.10.9                我新写的 Dockerfile/deploy.sh 也假设了前端被用 ← 第 N 个接力的人！
```

**核心 bug**：v1.6 立项 Svelte 前端时，**没把 `static_assets.py` 从读 `web/templates/` 改成读 `src/frontend/build/`**。

这是个**30 个版本累积下来的架构债**。

---

## 五、三种解决路径

### 方案 A：删死代码（**最小改动，推荐**）

> 适用：短期不打算启用 Svelte 前端 / 优先保证部署一致

1. 删 `src/frontend/` 整个目录（~310 MB 镜像节省）
2. 删 Dockerfile 的 frontend-build stage
3. 删 `deploy/deploy.sh` 的 `build_frontend()` 函数
4. 删 `deploy/nginx.conf` 的前端相关 location（保留 `/api/` 和 `/static/`）
5. 删除 `npm` 依赖（package.json 不再被任何文件引）
6. 更新 README.md：不要让新人 `cd src/frontend`

**工作量**：~2 小时
**风险**：低（删除路径，不改后端逻辑）
**收益**：镜像 -40%、CI -10 分钟、文档与现实一致

### 方案 B：让 Svelte 前端真正接管（最大改动）

> 适用：要把 v2.x Svelte 前端当正式前端

1. 改 `src/history_footnote/web_server/static_assets.py`：
   ```python
   # 原：from history_footnote.web import TEMPLATES_DIR as _TPL_DIR
   # 改：
   from pathlib import Path
   _INDEX_HTML_PATH = Path(__file__).parent.parent.parent.parent / "frontend" / "build" / "index.html"
   ```
2. 改 `src/history_footnote/web_server/handler_base.py` 的 `_serve_static`：
   ```python
   # 原：from history_footnote.web import STATIC_DIR
   # 改：服务 src/frontend/build/ + src/frontend/static/
   ```
3. 删 `src/history_footnote/web/` 整个目录
4. 端到端测试（v2.10.9 单元测试没碰前端）
5. 浏览器实测 + Playwright e2e

**工作量**：1-2 天（含回归测试）
**风险**：高（涉及前后端集成点）
**收益**：v2.x UI 真正生效、移动端适配生效

### 方案 C：双前端双模式（中间方案）

> 适用：过渡期，A/B 切换

1. 加环境变量 `WEB_FRONTEND_MODE=legacy|svelte`
2. 后端按 env 选 INDEX_HTML 来源：
   ```python
   mode = os.environ.get("WEB_FRONTEND_MODE", "legacy")
   if mode == "svelte":
       _INDEX_HTML_PATH = SVELTE_BUILD_DIR / "index.html"
   else:
       _INDEX_HTML_PATH = LEGACY_WEB_DIR / "templates" / "index.html"
   ```
3. 同样让 _serve_static 按 mode 选 STATIC_DIR
4. 文档明确：默认 legacy，部署时要显式设 mode=svelte 才用 Svelte

**工作量**：半天
**风险**：中（环境变量配置可能漏）
**收益**：两边都能用，过渡平滑

---

## 六、立即建议

**建议先执行方案 A**（删死代码），把架构债清掉。

如果要保留 Svelte 作为开发中版本（不想删代码），用方案 C。

**绝对不建议**保持现状：每次部署都在假装部署了一个不存在的前端 + 浪费 40% 资源。

---

## 七、修复 checklist（A 方案）

- [ ] 备份 Svelte 前端到 `git checkout -b archive/svelte-frontend`
- [ ] `git rm -r src/frontend/`
- [ ] `git rm .dockerignore`（Dockerfile 改完后没必要）
- [ ] 改 [Dockerfile](../../Dockerfile)：
  - 删 frontend-build stage
  - Stage 2 删 `COPY --from=frontend-build /build/build/ ./static/`
  - 删 `node` 依赖注释
- [ ] 改 [deploy/deploy.sh](../../deploy/deploy.sh)：
  - 删 `build_frontend()` 函数（行 127-145）
  - 删 install 中 `if ! command -v node` 块
  - 删 update 中的 `build_frontend` 调用
- [ ] 改 [deploy/nginx.conf](../../deploy/nginx.conf)：
  - `location /` 改成 `proxy_pass http://127.0.0.1:8765;`（让后端服务旧前端）
  - 删 `location ~* \.(js|css|woff2?|...)`（后端已经服务）
- [ ] 改 [Dockerfile](../../Dockerfile) `VOLUME` 指令
- [ ] 更新 [README.md](../../README.md)：删 `cd src/frontend` 指引
- [ ] 更新 [CHANGELOG.md](../../CHANGELOG.md) — v2.10.10 一条条目说明删除死代码
- [ ] 加 git tag `v2.10.10-dead-code-removal`

预期结果：
- Docker 镜像 ~250 MB（-40%）
- CI build 快 5-10 分钟
- README 与现实一致
- 部署用户看到的就是代码里写的

---

## 八、归档定位

如果决定方案 A + 想要保留 Svelte 代码作为备份：
- 全目录 `git mv src/frontend/ scripts/_archive/frontend_v2/`
- 加 `_archive/frontend_v2/README.md` 说明何时归档、为何不用
- 在 README.md 加归档说明

---

**优先级**：🟡 中等（不影响功能，但每次部署都在做无用功 + 误导新人）
**建议时间**：本周内清掉
