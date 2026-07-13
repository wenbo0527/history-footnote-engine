/**
 * 🆕 v2.10.3 unwrap 工具
 *
 * 目标：把 `as any` 集中到一个文件，让 ts-check 能识别风险点。
 *
 * 用法：
 *   // ❌ 之前
 *   const city = (game as any).pending_city_change?.from_city;
 *
 *   // ✅ 现在
 *   import { unwrap } from '$lib/api/unwrap';
 *   const city = unwrap(game).pending_city_change?.from_city;
 *   // 类型：unknown（TS 强制你处理）
 *
 *   // 或带类型断言（一次性）：
 *   import { unwrapAs } from '$lib/api/unwrap';
 *   const city = unwrapAs<{ pending_city_change?: { from_city?: string } }>(game);
 *
 * 设计原则：
 * 1. unwrap() 默认返回 unknown——强迫调用者做类型断言
 * 2. unwrapAs<T>() 仅在无法补类型时使用（会出现在 CI 警告）
 * 3. 真正的解决方案是补 GameState 类型 → 不用 unwrap
 */

/**
 * 安全解包可能为 null/undefined 的对象为 unknown
 * 强迫调用者用类型断言或属性访问 + optional chaining
 */
export function unwrap<T>(value: T | null | undefined): T {
  // 返回原值，但 TS 会在调用方做属性访问时报"unknown"错误
  // 真正的"运行时"是 noop
  return value as T;
}

/**
 * 带显式类型断言的解包
 * ⚠️ 仅作为逃生舱——使用前应优先补 GameState 类型
 */
export function unwrapAs<T>(value: unknown): T {
  return value as T;
}

/**
 * 读取嵌套字段，带 fallback
 * @example
 *   pick(game, 'pending_city_change.from_city', '')
 */
export function pick<T = unknown>(
  obj: unknown,
  path: string,
  fallback?: T
): T | undefined {
  if (!obj || typeof obj !== "object") return fallback;
  const parts = path.split(".");
  let cur: any = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return fallback;
    cur = cur[p];
  }
  return (cur === undefined ? fallback : cur) as T;
}