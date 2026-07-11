/**
 * 🆕 v2.8.0 W27: Playwright E2E 配置
 *
 * 适配 SvelteKit 5 + chapter 制 UI 测试：
 * - 自动启动 vite dev server（baseURL: http://localhost:5173）
 * - chromium only（节省 CI 时间）
 * - 失败自动截图 + trace
 *
 * 跑：npx playwright test
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
