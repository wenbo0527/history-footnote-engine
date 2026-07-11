/**
 * 🆕 v2.9.x W41: 板块图布局算法测试
 */
import { describe, it, expect } from 'vitest';
import {
  circularLayout,
  findNode,
  buildEdges,
  nodeRadius,
  type LayoutOptions,
} from './graphLayout';

describe('circularLayout', () => {
  it('layouts N nodes around a circle', () => {
    const ids = ['a', 'b', 'c', 'd'];
    const layout = circularLayout(ids, { width: 400, height: 300 });
    expect(layout.nodes).toHaveLength(4);
    expect(layout.nodes[0].id).toBe('a');
    // 所有节点在半径上（中心到节点距离约等于 radius）
    for (const n of layout.nodes) {
      const dx = n.x - layout.centerX;
      const dy = n.y - layout.centerY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      expect(dist).toBeCloseTo(layout.radius, 0);
    }
  });

  it('returns stable positions for same input', () => {
    const ids1 = ['x', 'y', 'z'];
    const ids2 = ['x', 'y', 'z'];
    const l1 = circularLayout(ids1);
    const l2 = circularLayout(ids2);
    expect(l1.nodes[0].x).toBe(l2.nodes[0].x);
    expect(l1.nodes[1].y).toBe(l2.nodes[1].y);
  });

  it('handles 1 node (degenerate case)', () => {
    const layout = circularLayout(['only'], { width: 200, height: 200 });
    expect(layout.nodes).toHaveLength(1);
    // 1 节点从 12 点钟方向（-π/2）开始
    // x = 100 + 60*cos(-π/2) = 100
    // y = 100 + 60*sin(-π/2) = 100 - 60 = 40
    expect(layout.nodes[0].x).toBe(100);
    expect(layout.nodes[0].y).toBe(40);
  });

  it('handles 0 nodes', () => {
    const layout = circularLayout([], { width: 200, height: 200 });
    expect(layout.nodes).toHaveLength(0);
  });

  it('respects custom width/height/padding', () => {
    const opts: LayoutOptions = { width: 500, height: 500, padding: 50 };
    const layout = circularLayout(['a', 'b'], opts);
    expect(layout.width).toBe(500);
    expect(layout.height).toBe(500);
    expect(layout.centerX).toBe(250);
    expect(layout.centerY).toBe(250);
    // 半径 = min(500,500)/2 - 50 = 200
    expect(layout.radius).toBe(200);
  });
});

describe('findNode', () => {
  it('finds node by id', () => {
    const layout = circularLayout(['a', 'b', 'c']);
    expect(findNode(layout, 'b')?.id).toBe('b');
  });

  it('returns undefined for missing id', () => {
    const layout = circularLayout(['a', 'b']);
    expect(findNode(layout, 'zzz')).toBeUndefined();
  });
});

describe('buildEdges', () => {
  it('builds edges from neighbors (deduplicated)', () => {
    const layout = circularLayout(['a', 'b', 'c']);
    const neighbors = {
      a: ['b', 'c'],
      b: ['a', 'c'],
      c: ['a', 'b'],
    };
    const edges = buildEdges(layout, neighbors);
    // 3 个节点全连接：3 条边（去重后）
    expect(edges).toHaveLength(3);
  });

  it('skips edges to missing nodes', () => {
    const layout = circularLayout(['a', 'b']);
    const neighbors = { a: ['b', 'ghost'] };
    const edges = buildEdges(layout, neighbors);
    expect(edges).toHaveLength(1);
    expect(edges[0].to).toBe('b');
  });

  it('handles empty neighbors', () => {
    const layout = circularLayout(['a', 'b']);
    const edges = buildEdges(layout, {});
    expect(edges).toHaveLength(0);
  });

  it('edges have correct coordinates', () => {
    const layout = circularLayout(['a', 'b']);
    const a = findNode(layout, 'a')!;
    const b = findNode(layout, 'b')!;
    const edges = buildEdges(layout, { a: ['b'] });
    expect(edges[0].fromX).toBe(a.x);
    expect(edges[0].toX).toBe(b.x);
  });
});

describe('nodeRadius', () => {
  it('returns small radius for few nodes', () => {
    expect(nodeRadius(2)).toBe(28);
    expect(nodeRadius(4)).toBe(28);
  });

  it('returns medium radius for 5-8 nodes', () => {
    expect(nodeRadius(5)).toBe(32);
    expect(nodeRadius(8)).toBe(32);
  });

  it('returns large radius for 9+ nodes', () => {
    expect(nodeRadius(9)).toBe(36);
    expect(nodeRadius(20)).toBe(36);
  });
});
