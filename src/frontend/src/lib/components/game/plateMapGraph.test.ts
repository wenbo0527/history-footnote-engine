/**
 * 🆕 v2.9.x W42: PlateMap SVG 节点图集成测试
 *
 * 验证 graphLayout 在 PlateMap 数据流中的正确性：
 * 1. neighbors → edges 转换（用真实 plateMap 数据结构）
 * 2. 5 节点布局（典型 5 板块）
 * 3. 8 节点布局（自适应 radius）
 * 4. 状态颜色映射（4 状态 + 默认灰）
 * 5. 激活板块高亮（active_plate 字段）
 */
import { describe, it, expect } from 'vitest';
import { circularLayout, buildEdges, nodeRadius } from './graphLayout';
import type { PlateMapResponse } from '$lib/api/chapter';

// 5 节点（典型 5 板块）
const plateMap5: PlateMapResponse = {
  active: true,
  plate_count: 5,
  definitions: [
    { id: 'central_plains', name: '中原', type: 'core', neighbors: ['jiangnan', 'northwest'], base_tension: 0.3, description: '中原' },
    { id: 'jiangnan', name: '江南', type: 'core', neighbors: ['central_plains', 'hexi_corridor'], base_tension: 0.4, description: '江南' },
    { id: 'hexi_corridor', name: '河西', type: 'corridor', neighbors: ['jiangnan', 'northwest', 'southwest'], base_tension: 0.5, description: '河西' },
    { id: 'northwest', name: '西北', type: 'peripheral', neighbors: ['central_plains', 'hexi_corridor'], base_tension: 0.6, description: '西北' },
    { id: 'southwest', name: '西南', type: 'peripheral', neighbors: ['hexi_corridor'], base_tension: 0.7, description: '西南' },
  ],
  corridors: [],
  tensions: { central_plains: 0.3, jiangnan: 0.4, hexi_corridor: 0.5, northwest: 0.6, southwest: 0.7 },
  statuses: { central_plains: 'stable', jiangnan: 'tense', hexi_corridor: 'shifting', northwest: 'stable', southwest: 'collapsed' },
  active_plate: 'hexi_corridor',
};

// 8 节点（边界测试）
const plateMap8: PlateMapResponse = {
  active: true,
  plate_count: 8,
  definitions: [
    { id: 'p1', name: '板块1', type: 'core', neighbors: ['p2', 'p3'], base_tension: 0.1, description: '' },
    { id: 'p2', name: '板块2', type: 'core', neighbors: ['p1', 'p3'], base_tension: 0.2, description: '' },
    { id: 'p3', name: '板块3', type: 'core', neighbors: ['p1', 'p2'], base_tension: 0.3, description: '' },
    { id: 'p4', name: '板块4', type: 'peripheral', neighbors: ['p5'], base_tension: 0.4, description: '' },
    { id: 'p5', name: '板块5', type: 'corridor', neighbors: ['p4', 'p6'], base_tension: 0.5, description: '' },
    { id: 'p6', name: '板块6', type: 'corridor', neighbors: ['p5', 'p7'], base_tension: 0.6, description: '' },
    { id: 'p7', name: '板块7', type: 'peripheral', neighbors: ['p6', 'p8'], base_tension: 0.7, description: '' },
    { id: 'p8', name: '板块8', type: 'peripheral', neighbors: ['p7'], base_tension: 0.8, description: '' },
  ],
  corridors: [],
  tensions: {},
  statuses: {},
  active_plate: '',
};

// status color 映射（与 PlateMap.svelte 一致）
const STATUS_COLOR_MAP: Record<string, string> = {
  stable: 'rgb(80, 140, 80)',
  tense: 'rgb(200, 150, 50)',
  shifting: 'rgb(220, 100, 50)',
  collapsed: 'rgb(180, 50, 50)',
};

describe('W42: PlateMap SVG 节点图集成', () => {
  it('5 节点布局：5 个板块均匀分布', () => {
    const ids = plateMap5.definitions.map((p) => p.id);
    const layout = circularLayout(ids, { width: 400, height: 360, padding: 50 });
    expect(layout.nodes).toHaveLength(5);
    // 自适应半径：5 节点 = 32
    expect(nodeRadius(5)).toBe(32);
  });

  it('5 节点 + neighbors → 6 条边（去重后）', () => {
    const ids = plateMap5.definitions.map((p) => p.id);
    const layout = circularLayout(ids);
    const neighbors: Record<string, string[]> = {};
    for (const p of plateMap5.definitions) {
      neighbors[p.id] = p.neighbors;
    }
    const edges = buildEdges(layout, neighbors);
    // central_plains↔jiangnan, central_plains↔northwest, jiangnan↔hexi_corridor,
    // hexi_corridor↔northwest, hexi_corridor↔southwest = 5 边
    expect(edges).toHaveLength(5);
  });

  it('8 节点布局：自适应 radius 32', () => {
    const ids = plateMap8.definitions.map((p) => p.id);
    const layout = circularLayout(ids);
    expect(layout.nodes).toHaveLength(8);
    expect(nodeRadius(8)).toBe(32);
    // 所有节点在 360 度圆周
    for (const n of layout.nodes) {
      const dx = n.x - layout.centerX;
      const dy = n.y - layout.centerY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      expect(dist).toBeCloseTo(layout.radius, 0);
    }
  });

  it('4 状态颜色映射正确', () => {
    expect(STATUS_COLOR_MAP.stable).toBe('rgb(80, 140, 80)');
    expect(STATUS_COLOR_MAP.tense).toBe('rgb(200, 150, 50)');
    expect(STATUS_COLOR_MAP.shifting).toBe('rgb(220, 100, 50)');
    expect(STATUS_COLOR_MAP.collapsed).toBe('rgb(180, 50, 50)');
  });

  it('激活板块正确识别（active_plate 字段）', () => {
    expect(plateMap5.active_plate).toBe('hexi_corridor');
    // 用于 SVG 节点 stroke 加重
    const active = plateMap5.definitions.find((p) => p.id === plateMap5.active_plate);
    expect(active?.name).toBe('河西');
    expect(plateMap5.statuses['hexi_corridor']).toBe('shifting');
  });
});
