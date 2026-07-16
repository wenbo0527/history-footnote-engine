# 前端后端联调 TODO 清单

**当前状态**：❌ **未联调**
**最后更新**：2026-07-08

---

## P0 阻塞性（必须先做）

### 1. SvelteKit proxy 失效
**问题**：`vite.config.ts` 里的 `server.proxy` 对 SvelteKit 不生效（`curl :5173/api/start` 返回空）。

**修复方案**（二选一）：

#### 方案 A：用 `hooks.server.ts` 做 proxy（推荐）
```typescript
// src/hooks.server.ts
import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;
  if (path.startsWith('/api/')) {
    const targetUrl = `http://localhost:8765${path}${event.url.search}`;
    const body = ['POST', 'PUT', 'PATCH'].includes(event.request.method)
      ? await event.request.arrayBuffer()
      : undefined;
    const headers = new Headers(event.request.headers);
    // 转发请求
    const response = await fetch(targetUrl, {
      method: event.request.method,
      headers,
      body: body ? body : undefined,
    });
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    });
  }
  return resolve(event);
};
```

#### 方案 B：删掉 vite proxy，前端用绝对 URL
```typescript
// lib/api/client.ts
export const api = ofetch.create({
  baseURL: 'http://localhost:8765/api',  // 改用绝对 URL
  credentials: 'include',
});
```
**问题**：CORS。后端需要加 CORS headers。

---

## P1 重要（不做就不能用）

### 2. 游戏页用真实 API（去 mock）
**问题**：`game/+page.svelte:91` 只在 `demo=1` 用 mock，否则跳回首页。

**修复**：
```svelte
onMount(async () => {
  const sessionId = $page.url.searchParams.get('session') 
    ?? localStorage.getItem('session_id');
  
  if (!sessionId) {
    goto('/');
    return;
  }
  
  // 调 /api/state 拿真实 game state
  const state = await getState(sessionId);
  gameActions.set(state);
});
```

### 3. Session 持久化
**问题**：wizard 提交后只 `goto('/game')`，session_id 没传到 game 页。

**修复**：
```typescript
// lib/api/start.ts
export async function startGame(req: StartRequest) {
  const data = await call<GameState>('/start', { body: req });
  localStorage.setItem('session_id', data.session_id);
  return data;
}
```

### 4. Wizard → Game 数据流
**问题**：wizard 提交后跳到 game，但 game 拿不到 session_id（localStorage 也可能没存）。

**验证**：
```bash
# 1. 启动后端
python -m history_footnote

# 2. 启动前端
cd src/frontend && npm run dev

# 3. 浏览器测试
# http://localhost:5173/
# 点"入局" → 走完 3 步 wizard
# 提交后应该跳到 /game
# game 页应该自动加载真实 game state（不是 mock）
```

---

## P2 体验优化（做完可用，但建议做）

### 5. 账号系统接入
**问题**：完全没接 `/api/account/login` 等。

**修复**：
- 首页 "切换账户" 按钮 → 调 login
- localStorage 存 token
- 401 跳回首页

### 6. CORS 处理
**问题**：如果用绝对 URL 调后端，跨域。

**修复**：后端加 CORS headers（或者走 hooks.server.ts proxy）。

### 7. Loading 状态
**问题**：wizard 提交时 `submitting=true`，但前端没真后端 → 状态永远 false。

**修复**：v1.7.28 已经写好，验证即可。

### 8. 错误处理（toast）
**问题**：前端已经写好 400 错误处理，但没真后端 → 永远走不到。

**修复**：等联调通过后实测。

### 9. 弹层（Wiki/Recap/Glossary/Feedback/Settings）
**问题**：5 个弹层都调 API，但目前是 mock 数据。

**修复**：
```svelte
// CharacterWikiModal.svelte
onMount(async () => {
  wiki = await getCharacterWiki($game.session_id);
});
```

### 10. 存档 / 读档
**问题**：完全没接。

**修复**：
- 工具栏加"存档"按钮
- 调 `/api/archives/save`
- 首页"我的存档"调 `/api/archives/list`

---

## P3 进阶（生产级）

### 11. SSE 流式
**问题**：`/api/input_stream` 是流式输出，前端目前是 JSON 轮询。

**修复**：
- InputArea 改用 `EventSource` 或 ofetch stream
- narrative 边收边渲染

### 12. WebSocket
**问题**：没有实时推送。

### 13. SSR 兼容
**问题**：wizard reset 在 onMount 里（只在客户端），SSR 渲染会卡。

### 14. 性能优化
**问题**：每次提交都重新加载整个 game state。

**修复**：
- 增量更新（只更新变动的字段）
- 缓存 last_narrative / last_voice_options

---

## 验证清单

### 最小可用版本（MVP）
- [ ] SvelteKit proxy 修复（hooks.server.ts）
- [ ] wizard 提交 → 真实 /api/start
- [ ] game 页从 localStorage 拿 session_id 调 /api/state
- [ ] 完整跑通：首页 → wizard → game（3 步 + narrative 渲染）

### 完整版本
- [ ] 5 弹层都接真 API
- [ ] 存档 / 读档
- [ ] 错误 toast 测试（输入"嗯"/"手机" 等）
- [ ] 移动端实测

### 生产版本
- [ ] SSE 流式
- [ ] a11y
- [ ] 性能优化
- [ ] 部署

---

## 立即动手的最小步骤

1. 创建 `src/frontend/src/hooks.server.ts`（方案 A 的代码）
2. 重启前端 dev server
3. 测 `curl http://localhost:5173/api/eras` 是否能拿到数据
4. 在 wizard 提交按钮加 console.log，看是否真的发了请求
5. 在浏览器 F12 网络面板看 /api/* 请求是否走通

---

**联系**：联调问题随时反馈
