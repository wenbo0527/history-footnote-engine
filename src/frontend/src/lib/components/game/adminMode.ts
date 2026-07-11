/**
 * 🆕 v2.9.x W49: Admin 模式辅助函数
 *
 * 通过 URL 参数 ?admin=true 启用 admin 模式
 * - 显示 PlateMap / ChapterTimeline / MetricsPanel
 * - 默认不启用（普通用户看不到）
 *
 * 用法：
 *   const admin = isAdminMode();
 *   if (admin) { showAdminTools = true; }
 */

// 浏览器检测（兼容 SSR + 单元测试，不依赖 SvelteKit $app/environment）
function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.location !== 'undefined';
}

export function isAdminMode(): boolean {
  if (!isBrowser()) return false;
  const params = new URLSearchParams(window.location.search);
  return params.get('admin') === 'true';
}

export function setAdminMode(enabled: boolean): void {
  if (!isBrowser()) return;
  const url = new URL(window.location.href);
  if (enabled) {
    url.searchParams.set('admin', 'true');
  } else {
    url.searchParams.delete('admin');
  }
  window.history.replaceState({}, '', url.toString());
}

export interface AdminToolsProps {
  sessionId: string;
  currentChapter: number;
  totalChapters: number;
}
