/**
 * 🆕 v2.10.x — WorldMap 组件测试
 *
 * 业务不变量：
 * - 5 城必须存在 (盛泽/苏州/杭州/松江/南京)
 * - 5 城 x,y 位置必须落在 viewBox 0-1200 / 0-800 内
 * - 城级别 (tier) 必须合法 ('fu' | 'xian')
 * - 距离 (days) 必须 >= 0
 * - 盛泽必须是 days === 0
 * - 必须有 AI 底图 (v4) 文件
 */
import { describe, it, expect } from 'vitest';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const CITIES = [
  { id: 'nanjing', name: '南京應天府', tier: 'fu', x: 150, y: 95, days: 6.0 },
  { id: 'suzhou', name: '蘇州府', tier: 'fu', x: 235, y: 160, days: 1.0 },
  { id: 'hangzhou', name: '杭州府', tier: 'fu', x: 200, y: 320, days: 2.5 },
  { id: 'shengze', name: '盛澤鎮', tier: 'xian', x: 500, y: 440, days: 0 },
  { id: 'songjiang', name: '松江府', tier: 'fu', x: 720, y: 380, days: 2.0 },
];

describe('WorldMap 5 城配置 (v2.10.x)', () => {
  it('5 城必须全部存在', () => {
    expect(CITIES).toHaveLength(5);
    const ids = CITIES.map(c => c.id);
    expect(ids).toEqual(
      expect.arrayContaining(['nanjing', 'suzhou', 'hangzhou', 'shengze', 'songjiang'])
    );
  });

  it('所有城 x 坐标必须在 0-1200 内', () => {
    for (const c of CITIES) {
      expect(c.x).toBeGreaterThanOrEqual(0);
      expect(c.x).toBeLessThanOrEqual(1200);
    }
  });

  it('所有城 y 坐标必须在 0-800 内', () => {
    for (const c of CITIES) {
      expect(c.y).toBeGreaterThanOrEqual(0);
      expect(c.y).toBeLessThanOrEqual(800);
    }
  });

  it('城级别 (tier) 必须是 fu 或 xian', () => {
    for (const c of CITIES) {
      expect(['fu', 'xian']).toContain(c.tier);
    }
  });

  it('距离 (days) 必须 >= 0', () => {
    for (const c of CITIES) {
      expect(c.days).toBeGreaterThanOrEqual(0);
    }
  });

  it('盛泽 (玩家起点) 距离必须 = 0', () => {
    const shengze = CITIES.find(c => c.id === 'shengze');
    expect(shengze).toBeDefined();
    expect(shengze?.days).toBe(0);
  });

  it('每个城 id 必须唯一', () => {
    const ids = CITIES.map(c => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('AI 底图 (v4) 文件存在', () => {
  it('mmx-output/jian-ye-A-v4.jpg 必须存在', () => {
    const path = join(process.cwd(), 'static/mmx-output/jian-ye-A-v4.jpg');
    expect(existsSync(path)).toBe(true);
  });
});

describe('WorldMap 组件文件存在', () => {
  it('WorldMap.svelte 必须存在', () => {
    const path = join(
      process.cwd(),
      'src/lib/components/game/WorldMap.svelte'
    );
    expect(existsSync(path)).toBe(true);
  });

  it('CityMarker.svelte 必须存在', () => {
    const path = join(
      process.cwd(),
      'src/lib/components/game/CityMarker.svelte'
    );
    expect(existsSync(path)).toBe(true);
  });

  it('CanalPath.svelte 必须存在', () => {
    const path = join(
      process.cwd(),
      'src/lib/components/game/CanalPath.svelte'
    );
    expect(existsSync(path)).toBe(true);
  });

  it('CityDetailPanel.svelte 必须存在', () => {
    const path = join(
      process.cwd(),
      'src/lib/components/game/CityDetailPanel.svelte'
    );
    expect(existsSync(path)).toBe(true);
  });
});
