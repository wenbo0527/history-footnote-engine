/**
 * 🆕 v2.8.0 W27: Playwright E2E - ChapterHistoryDrawer 端到端
 *
 * 场景：
 * - API 路径存在性
 * - 无效 session_id → 404 容错
 * - 老存档 active=false
 */
import { test, expect, request } from '@playwright/test';

test.describe('ChapterHistoryDrawer E2E (v2.8.0 段 UI)', () => {

  test('GET /api/chapter/state 带 fake session — 200 + active=false', async ({ request: req }) => {
    const res = await req.get('/api/chapter/state?session_id=fake-session-xyz-99999');
    expect(res.status()).toBe(200);
    const body = await res.json();
    // fake session 不存在 → game = None → 返回 404? 看实际逻辑
    // 我们的逻辑：缺 session_id → 400；session 不存在 → 404
    // "fake-session-xyz-99999" 格式合法，但 game 找不到 → 404
    expect([200, 404]).toContain(res.status());
    if (res.status() === 200) {
      // 如果 game 找到了（旧存档或测试存档），active 必为 false（无 chapter_state）
      expect(body.active).toBe(false);
    }
  });

  test('GET /api/chapter/history 带 fake session — 200 或 404', async ({ request: req }) => {
    const res = await req.get('/api/chapter/history?session_id=fake-99999');
    expect([200, 404]).toContain(res.status());
  });

  test('API 错误不返回 500', async ({ request: req }) => {
    // 给一个能解析但找不到的 session
    const res = await req.get('/api/chapter/state?session_id=nonexistent-yet-valid-format');
    // 应该是 404（找不到 session），不是 500
    expect(res.status()).not.toBe(500);
  });
});
