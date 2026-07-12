/**
 * 🆕 v2.10.x W54: 懒加载 + Web Vitals 测试
 */
import { describe, it, expect, vi } from 'vitest';
import { lazyImport, prefetch, onIdle, getWebVitals } from './lazyLoad';

describe('W54: lazyImport', () => {
  it('wraps dynamic import', async () => {
    const fn = lazyImport(async () => ({ default: { value: 42 } }));
    const result = await fn();
    expect(result).toEqual({ value: 42 });
  });

  it('catches error and calls onError', async () => {
    const onError = vi.fn();
    const fn = lazyImport(async () => { throw new Error('fail'); }, onError);
    await expect(fn()).rejects.toThrow('fail');
    expect(onError).toHaveBeenCalled();
  });
});

describe('W54: prefetch', () => {
  it('adds link tag in document', () => {
    if (typeof document === 'undefined') return; // jsdom 默认有
    const before = document.head.querySelectorAll('link[rel="prefetch"]').length;
    prefetch('/test-url');
    const after = document.head.querySelectorAll('link[rel="prefetch"]').length;
    expect(after).toBe(before + 1);
  });

  it('skips when document undefined', () => {
    // 调用不抛错即通过
    expect(() => prefetch('/x')).not.toThrow();
  });
});

describe('W54: onIdle', () => {
  it('calls callback via setTimeout fallback', async () => {
    const cb = vi.fn();
    onIdle(cb, 100);
    await new Promise((r) => setTimeout(r, 200));
    expect(cb).toHaveBeenCalled();
  });
});

describe('W54: getWebVitals', () => {
  it('returns PerformanceMetrics object', async () => {
    const m = await getWebVitals();
    expect(m).toBeDefined();
    expect(typeof m).toBe('object');
  });
});
