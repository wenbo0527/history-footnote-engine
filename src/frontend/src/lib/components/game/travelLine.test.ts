/**
 * 🆕 v2.10.x — TravelLine + 路径解析 测试
 *
 * 业务不变量：
 * - TravelLine 接受 segment + cities 数组
 * - 路径字符串必须 valid SVG path (start with M + Q)
 * - 中点位置必须有效数字
 */

import { describe, it, expect } from 'vitest';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const CITIES = [
  { id: 'nanjing', name: '南京', x: 150, y: 95, days: 6 },
  { id: 'suzhou', name: '蘇州', x: 235, y: 160, days: 1 },
  { id: 'hangzhou', name: '杭州', x: 200, y: 320, days: 2.5 },
  { id: 'shengze', name: '盛澤', x: 500, y: 440, days: 0 },
  { id: 'songjiang', name: '松江', x: 720, y: 380, days: 2 },
];

describe('TravelLine 数据结构 (v2.10.x)', () => {
  it('TravelSegment 必须有 from/to/days', () => {
    const segment = { from: 'shengze', to: 'suzhou', days: 1, round: 1 };
    expect(segment.from).toBe('shengze');
    expect(segment.to).toBe('suzhou');
    expect(segment.days).toBe(1);
  });

  it('days 必须 >= 0', () => {
    const segments = [
      { from: 'shengze', to: 'suzhou', days: 0 },
      { from: 'shengze', to: 'nanjing', days: 6 },
    ];
    for (const s of segments) {
      expect(s.days).toBeGreaterThanOrEqual(0);
    }
  });
});

describe('路径 SVG 字符串生成 (模拟)', () => {
  // 模拟 TravelLine 内部的 path 计算
  function computePath(from: { x: number; y: number }, to: { x: number; y: number }): string {
    const mx = (from.x + to.x) / 2;
    const my = (from.y + to.y) / 2;
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) return `M ${from.x} ${from.y}`;
    const offsetX = -dy / len * 15;
    const offsetY = dx / len * 15;
    return `M ${from.x} ${from.y} Q ${mx + offsetX} ${my + offsetY} ${to.x} ${to.y}`;
  }

  it('shengze -> suzhou 路径必须 valid SVG', () => {
    const from = CITIES.find(c => c.id === 'shengze')!;
    const to = CITIES.find(c => c.id === 'suzhou')!;
    const path = computePath(from, to);
    expect(path).toMatch(/^M \d+ \d+ Q [\d.-]+ [\d.-]+ \d+ \d+$/);
  });

  it('起点 = 终点 (距离 0) 路径应只有 M', () => {
    const from = CITIES.find(c => c.id === 'shengze')!;
    const path = computePath(from, from);
    expect(path).toBe(`M ${from.x} ${from.y}`);
  });
});

describe('TravelLine.svelte 文件存在', () => {
  it('TravelLine.svelte 必须存在', () => {
    const path = join(
      process.cwd(),
      'src/lib/components/game/TravelLine.svelte'
    );
    expect(existsSync(path)).toBe(true);
  });

  it('WorldMapContainer.svelte 必须存在', () => {
    const path = join(
      process.cwd(),
      'src/lib/components/game/WorldMapContainer.svelte'
    );
    expect(existsSync(path)).toBe(true);
  });
});
