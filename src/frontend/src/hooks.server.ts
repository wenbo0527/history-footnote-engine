/**
 * 🆕 v1.7.30 SvelteKit server hooks
 *
 * 作用：把 /api/* 请求代理到后端 (http://localhost:8765)
 *
 * 为什么不用 vite.config.ts 的 server.proxy？
 *   - SvelteKit 用自己的 hooks 系统
 *   - vite dev server 的 proxy 不一定穿透到 SvelteKit 路由
 *   - 实测 :5173/api/* 返回空响应
 *
 * 这个 hooks 是 SvelteKit 官方推荐的 proxy 方式
 */
import type { Handle } from '@sveltejs/kit';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8765';

export const handle: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;

  // 只代理 /api/* 路径
  if (path.startsWith('/api/')) {
    const targetUrl = `${BACKEND_URL}${path}${event.url.search}`;

    // 读取 body（POST/PUT/PATCH 才有）
    let body: ArrayBuffer | undefined;
    if (['POST', 'PUT', 'PATCH'].includes(event.request.method)) {
      body = await event.request.arrayBuffer();
    }

    // 复制 headers（排除 host）
    const headers = new Headers(event.request.headers);
    headers.delete('host');
    headers.delete('content-length');   // fetch 会自动算

    try {
      const response = await fetch(targetUrl, {
        method: event.request.method,
        headers,
        body: body && body.byteLength > 0 ? body : undefined,
      });

      // 复制响应 headers
      const responseHeaders = new Headers(response.headers);
      // 跨域需要：去掉限制
      // responseHeaders.delete('access-control-allow-origin');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      console.error(`[proxy] ${path} failed:`, err);
      return new Response(
        JSON.stringify({
          error: 'backend_unreachable',
          message: `后端 ${BACKEND_URL} 连不上`,
          path,
        }),
        {
          status: 502,
          headers: { 'content-type': 'application/json' },
        }
      );
    }
  }

  // 非 /api/* 走 SvelteKit 正常路由
  return resolve(event);
};
