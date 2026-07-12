/**
 * 🆕 v2.10.x W53: useMediaQuery + getBreakpoint 测试
 */
import { describe, it, expect } from 'vitest';
import { getBreakpoint } from './useMediaQuery';

describe('W53: getBreakpoint', () => {
  it('width < 640 → mobile', () => {
    expect(getBreakpoint(320)).toBe('mobile');
    expect(getBreakpoint(639)).toBe('mobile');
  });

  it('width 640-1024 → tablet', () => {
    expect(getBreakpoint(640)).toBe('tablet');
    expect(getBreakpoint(800)).toBe('tablet');
    expect(getBreakpoint(1024)).toBe('tablet');
  });

  it('width >= 1025 → desktop', () => {
    expect(getBreakpoint(1025)).toBe('desktop');
    expect(getBreakpoint(1920)).toBe('desktop');
  });

  it('boundary 639 vs 640', () => {
    expect(getBreakpoint(639)).toBe('mobile');
    expect(getBreakpoint(640)).toBe('tablet');
  });

  it('boundary 1024 vs 1025', () => {
    expect(getBreakpoint(1024)).toBe('tablet');
    expect(getBreakpoint(1025)).toBe('desktop');
  });
});
