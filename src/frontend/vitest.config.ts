/**
 * 🆕 v2.8.0 W21: Vitest 配置
 *
 * 适配 Svelte 5 + SvelteKit + vitest 的项目：
 * - 用 jsdom 模拟浏览器（API client 测试需要 window/document）
 * - 不测 .svelte 组件 mount（Svelte 5 + testing-library 5 已知兼容性问题
 *   需等 SvelteKit 升级 vite-plugin-svelte v3 → v4 后再解）
 * - 只测 API client + 业务不变量
 */
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

export default defineConfig({
  plugins: [svelte({ hot: false })],
  test: {
    environment: 'jsdom',
    globals: true,
    // 测 API + scene 映射 + plate 映射 + hooks + graphLayout + chapterHistory + chapterTimelineApi（不测 .svelte 组件 mount）
    include: [
      'src/lib/api/**/*.{test,spec}.{js,ts}',
      'src/lib/hooks/**/*.{test,spec}.{js,ts}',
      'src/lib/components/game/sceneMap.test.ts',
      'src/lib/components/game/plateMap.test.ts',
      'src/lib/components/game/graphLayout.test.ts',
      'src/lib/components/game/plateMapGraph.test.ts',
      'src/lib/components/game/chapterHistory.test.ts',
      'src/lib/components/game/chapterTimelineApi.test.ts',
      'src/lib/components/game/metricsPanel.test.ts',
      'src/lib/components/game/adminMode.test.ts',
      'src/lib/components/game/gameViewAdmin.test.ts',
    ],
    exclude: ['node_modules', '.svelte-kit', 'build', 'e2e', 'src/lib/components/**/*.svelte'],
    setupFiles: ['./vitest.setup.ts'],
  },
  resolve: {
    alias: {
      // $lib alias → src/lib（components/ 下的测试需要这个）
      $lib: resolve(__dirname, 'src/lib'),
    },
  },
});
