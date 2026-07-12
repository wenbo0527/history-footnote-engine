/**
 * 🆕 v2.10.x W54: 首屏加载优化 — 懒加载 + 预取
 *
 * 工具函数：
 * - lazyImport: 动态 import 包装
 * - prefetch: 预取（hover 触发）
 * - onIdle: 浏览器 idle 时执行
 */

export function lazyImport<T>(
  importFn: () => Promise<{ default: T }>,
  onError?: (e: any) => void
): () => Promise<T> {
  return async () => {
    try {
      const mod = await importFn();
      return mod.default;
    } catch (e) {
      onError?.(e);
      throw e;
    }
  };
}

export function prefetch(url: string): void {
  if (typeof document === 'undefined') return;
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.href = url;
  link.as = 'fetch';
  link.crossOrigin = 'anonymous';
  document.head.appendChild(link);
}

export function onIdle(callback: () => void, timeout: number = 2000): void {
  if (typeof window === 'undefined') return;
  if ('requestIdleCallback' in window) {
    (window as any).requestIdleCallback(callback, { timeout });
  } else {
    setTimeout(callback, 100);
  }
}

export interface PerformanceMetrics {
  FCP?: number;  // First Contentful Paint
  LCP?: number;  // Largest Contentful Paint
  TTI?: number;  // Time to Interactive
  TBT?: number;  // Total Blocking Time
}

export function getWebVitals(): Promise<PerformanceMetrics> {
  return new Promise((resolve) => {
    const metrics: PerformanceMetrics = {};
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
      resolve(metrics);
      return;
    }
    try {
      // FCP
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            metrics.FCP = entry.startTime;
          }
        }
      }).observe({ type: 'paint', buffered: true });
    } catch {}
    setTimeout(() => resolve(metrics), 100);
  });
}
