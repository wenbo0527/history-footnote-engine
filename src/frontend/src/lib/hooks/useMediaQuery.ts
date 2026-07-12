/**
 * 🆕 v2.10.x W53: useMediaQuery hook
 *
 * 响应式断点检测（用于自适应布局）
 * - mobile: < 640px
 * - tablet: 640-1024px
 * - desktop: > 1024px
 */
import { readable, type Readable } from 'svelte/store';

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function';
}

export type Breakpoint = 'mobile' | 'tablet' | 'desktop';

export function useMediaQuery(query: string): Readable<boolean> {
  if (!isBrowser()) return readable(false);
  const mql = window.matchMedia(query);
  return readable(mql.matches, (set) => {
    const handler = (e: MediaQueryListEvent) => set(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  });
}

export const isMobile = (): Readable<boolean> =>
  useMediaQuery('(max-width: 639px)');

export const isTablet = (): Readable<boolean> =>
  useMediaQuery('(min-width: 640px) and (max-width: 1024px)');

export const isDesktop = (): Readable<boolean> =>
  useMediaQuery('(min-width: 1025px)');

export function getBreakpoint(width: number): Breakpoint {
  if (width < 640) return 'mobile';
  if (width < 1025) return 'tablet';
  return 'desktop';
}
