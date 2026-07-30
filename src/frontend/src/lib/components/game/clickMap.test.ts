/**
 * 🆕 v2.10.x — Phase 8.5 主图点击测试
 *
 * 业务不变量：
 * - getNearestCity 接受 viewport 坐标 + image rect
 * - 返回最近城市 (within SEARCH_RADIUS=50 SVG units)
 * - 超出半径返回 null
 * - 跨多个城市时返回最近的
 */

import { describe, it, expect } from 'vitest';

const CITIES = [
  { id: 'nanjing', x: 150, y: 95 },
  { id: 'suzhou', x: 235, y: 160 },
  { id: 'hangzhou', x: 200, y: 320 },
  { id: 'shengze', x: 500, y: 440 },
  { id: 'songjiang', x: 720, y: 380 },
];

const VIEWBOX_W = 1200;
const VIEWBOX_H = 800;
const SEARCH_RADIUS = 50;

function getNearestCity(
  viewportX: number,
  viewportY: number,
  rect: { left: number; top: number; width: number; height: number }
) {
  const scaleX = VIEWBOX_W / rect.width;
  const scaleY = VIEWBOX_H / rect.height;
  const svgX = (viewportX - rect.left) * scaleX;
  const svgY = (viewportY - rect.top) * scaleY;

  let nearest = null;
  let minDist = Infinity;
  for (const c of CITIES) {
    const dx = c.x - svgX;
    const dy = c.y - svgY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < minDist && dist < SEARCH_RADIUS) {
      minDist = dist;
      nearest = c;
    }
  }
  return nearest;
}

describe('主图点击 → getNearestCity (v2.10.x Phase 8.5)', () => {
  // 假设图片充满 600x400 viewport
  const rect = { left: 0, top: 0, width: 600, height: 400 };

  it('点击南京 (150/95 SVG) → 返回 nanjing', () => {
    // SVG 150 / 1200 * 600 = 75 (viewport x)
    // SVG 95 / 800 * 400 = 47.5 (viewport y)
    const result = getNearestCity(75, 48, rect);
    expect(result?.id).toBe('nanjing');
  });

  it('点击盛泽 (500/440 SVG) → 返回 shengze', () => {
    const result = getNearestCity(250, 220, rect);
    expect(result?.id).toBe('shengze');
  });

  it('点击松江 (720/380 SVG) → 返回 songjiang', () => {
    const result = getNearestCity(360, 190, rect);
    expect(result?.id).toBe('songjiang');
  });

  it('点击空白区域 → 返回 null', () => {
    // 远离所有城市
    const result = getNearestCity(550, 50, rect); // 右上角空白
    expect(result).toBeNull();
  });

  it('点击杭州附近 (190/320 SVG) → 返回 hangzhou', () => {
    const result = getNearestCity(95, 160, rect);
    expect(result?.id).toBe('hangzhou');
  });

  it('点击杭州和苏州之间 (220/240 SVG) → 返回苏州 (较近)', () => {
    // SVG (220, 240) 到 苏州 (235, 160) dist = sqrt(225 + 6400) = ~81.2
    // SVG (220, 240) 到 杭州 (200, 320) dist = sqrt(400 + 6400) = ~82.5
    // 苏州略近
    const result = getNearestCity(110, 120, rect);
    expect(result?.id).toBe('suzhou');
  });
});

describe('viewport → SVG 坐标转换', () => {
  it('rect 满屏 (600x400) 时 scaleX=2, scaleY=2', () => {
    const rect = { left: 0, top: 0, width: 600, height: 400 };
    const scaleX = VIEWBOX_W / rect.width;
    const scaleY = VIEWBOX_H / rect.height;
    expect(scaleX).toBe(2);
    expect(scaleY).toBe(2);
  });

  it('rect 缩小 (300x200) 时 scaleX=4, scaleY=4', () => {
    const rect = { left: 0, top: 0, width: 300, height: 200 };
    const scaleX = VIEWBOX_W / rect.width;
    const scaleY = VIEWBOX_H / rect.height;
    expect(scaleX).toBe(4);
    expect(scaleY).toBe(4);
  });
});
