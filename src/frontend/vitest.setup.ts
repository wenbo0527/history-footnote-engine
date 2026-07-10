/**
 * 🆕 v2.8.0 W21: Vitest 启动 hook
 *
 * 目的：
 * - jsdom 模拟浏览器（fetch / window / document）
 * - 在每个 test 前清空 mock
 */
import { afterEach, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';

// 每个测试后清空 mock 调用历史
afterEach(() => {
  vi.clearAllMocks();
});
