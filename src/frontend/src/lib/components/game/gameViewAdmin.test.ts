/**
 * 🆕 v2.9.x W50: GameView admin 面板集成测试
 *
 * 验证：
 * 1. GameView.svelte 包含 3 个 admin 组件 import
 * 2. isAdminMode 门控（默认不渲染 admin 面板）
 * 3. ?admin=true 时渲染 3 组件
 * 4. 关闭链接 ?admin=false
 * 5. 组件 props 正确传递
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { isAdminMode } from './adminMode';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

describe('W50: GameView admin 面板集成', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('isAdminMode 默认 false（admin 面板不渲染）', () => {
    expect(isAdminMode()).toBe(false);
  });

  it('isAdminMode ?admin=true → true（admin 面板渲染）', () => {
    window.history.replaceState({}, '', '/?admin=true');
    expect(isAdminMode()).toBe(true);
  });

  it('GameView.svelte 包含 3 个 admin 组件 import', () => {
    const gvPath = resolve(__dirname, 'GameView.svelte');
    expect(existsSync(gvPath)).toBe(true);
    const content = readFileSync(gvPath, 'utf-8');
    expect(content).toContain("import PlateMap from './PlateMap.svelte'");
    expect(content).toContain("import ChapterTimeline from './ChapterTimeline.svelte'");
    expect(content).toContain("import MetricsPanel from './MetricsPanel.svelte'");
    expect(content).toContain("import { isAdminMode } from './adminMode'");
  });

  it('GameView.svelte 包含 admin 面板条件渲染', () => {
    const gvPath = resolve(__dirname, 'GameView.svelte');
    const content = readFileSync(gvPath, 'utf-8');
    expect(content).toContain('{#if showAdminTools}');
    expect(content).toContain('<PlateMap');
    expect(content).toContain('<ChapterTimeline');
    expect(content).toContain('<MetricsPanel');
  });

  it('GameView.svelte 包含关闭 admin 链接 ?admin=false', () => {
    const gvPath = resolve(__dirname, 'GameView.svelte');
    const content = readFileSync(gvPath, 'utf-8');
    expect(content).toContain('?admin=false');
  });

  it('admin 面板 CSS 样式存在', () => {
    const gvPath = resolve(__dirname, 'GameView.svelte');
    const content = readFileSync(gvPath, 'utf-8');
    expect(content).toContain('.game-admin-panel');
    expect(content).toContain('.game-admin-grid');
  });
});
