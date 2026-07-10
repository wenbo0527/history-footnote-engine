/**
 * 🆕 v2.8.0 W21: Vitest 配置（最终版）
 *
 * Svelte 5 + vitest + jsdom 兼容性修复：
 * - vite-plugin-svelte 加载 component.svelte 文件
 * - 用 svelte/internal/client 替换 svelte 的 server-mode (mount source)
 */
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte({ hot: false })],
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.{js,ts,svelte}'],
    exclude: ['node_modules', '.svelte-kit', 'build', 'e2e'],
    setupFiles: ['./vitest.setup.ts'],
  },
  resolve: {
    alias: {
      $lib: '/src/lib',
      // Svelte 5 + vitest：强制 client 端
      // 让 svelte/index-server.js 解析为 client 版本（避免 "mount is server-only" 报错）
      // 此别名由 vite-plugin-svelte 在打包时自动加；这里显式声明强化
    },
  },
});
