/**
 * 🆕 v2.9.x W49: admin mode 辅助函数测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { isAdminMode, setAdminMode } from './adminMode';

describe('W49: admin mode 切换', () => {
  beforeEach(() => {
    // reset URL
    window.history.replaceState({}, '', '/');
  });

  it('isAdminMode: 默认 false', () => {
    expect(isAdminMode()).toBe(false);
  });

  it('isAdminMode: ?admin=true → true', () => {
    window.history.replaceState({}, '', '/?admin=true');
    expect(isAdminMode()).toBe(true);
  });

  it('isAdminMode: ?admin=false → false', () => {
    window.history.replaceState({}, '', '/?admin=false');
    expect(isAdminMode()).toBe(false);
  });

  it('setAdminMode(true): 添加 admin=true', () => {
    setAdminMode(true);
    expect(window.location.search).toContain('admin=true');
    expect(isAdminMode()).toBe(true);
  });

  it('setAdminMode(false): 移除 admin', () => {
    window.history.replaceState({}, '', '/?admin=true');
    setAdminMode(false);
    expect(window.location.search).not.toContain('admin');
  });
});
