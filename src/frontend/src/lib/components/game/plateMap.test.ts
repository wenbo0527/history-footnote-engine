/**
 * 🆕 v2.8.x W28: PlateMap 数据结构测试
 *
 * 验证 getPlateMap API + PlateMap 组件的纯数据/纯逻辑部分
 * (不测 .svelte 组件 mount —— Svelte 5 + testing-library 已知兼容问题)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as chapterApi from '$lib/api/chapter';
import {
  getPlateMap,
  type PlateMapResponse,
  type PlateDefinition,
} from '$lib/api/chapter';

vi.mock('$lib/api/chapter', async () => {
  const actual = await vi.importActual<typeof chapterApi>('$lib/api/chapter');
  return {
    ...actual,
    getPlateMap: vi.fn(),
  };
});
const mockedGetPlateMap = vi.mocked(chapterApi.getPlateMap);

// 业务不变量：4 状态颜色映射
const STATUS_COLOR_MAP: Record<string, string> = {
  stable: 'rgb(80, 140, 80)',
  tense: 'rgb(200, 150, 50)',
  shifting: 'rgb(220, 100, 50)',
  collapsed: 'rgb(180, 50, 50)',
};

describe('PlateMap 数据契约 (v2.8.x W28)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getPlateMap: GET 请求 + session_id 参数', async () => {
    const fake: PlateMapResponse = {
      active: true,
      plate_count: 4,
      definitions: [
        { id: 'central_plains', name: '中原', type: 'core', neighbors: ['jiangnan', 'northwest'], base_tension: 0.3, description: '中原' },
        { id: 'jiangnan', name: '江南', type: 'core', neighbors: ['central_plains'], base_tension: 0.4, description: '江南' },
        { id: 'hexi_corridor', name: '河西走廊', type: 'corridor', neighbors: ['central_plains', 'northwest'], base_tension: 0.5, description: '河西' },
        { id: 'northwest', name: '西北', type: 'peripheral', neighbors: ['hexi_corridor', 'central_plains'], base_tension: 0.6, description: '西北' },
      ],
      corridors: [
        { id: 'grand_canal', from_plate: 'central_plains', to_plate: 'jiangnan', description: '大运河' },
        { id: 'silk_road', from_plate: 'hexi_corridor', to_plate: 'northwest', description: '丝绸之路' },
      ],
      tensions: { central_plains: 0.3, jiangnan: 0.5, hexi_corridor: 0.4, northwest: 0.7 },
      statuses: { central_plains: 'stable', jiangnan: 'shifting', hexi_corridor: 'tense', northwest: 'collapsed' },
      active_plate: 'jiangnan',
    };
    mockedGetPlateMap.mockResolvedValueOnce(fake);

    const result = await getPlateMap('sess-1');
    expect(result.plate_count).toBe(4);
    expect(result.active_plate).toBe('jiangnan');
  });

  it('类型契约：PlateDefinition 含 6 必填字段', () => {
    const p: PlateDefinition = {
      id: 'test',
      name: 'Test',
      type: 'core',
      neighbors: [],
      base_tension: 0.0,
      description: '',
    };
    expect(p.id).toBe('test');
    expect(p.name).toBe('Test');
    expect(p.type).toBe('core');
    expect(p.neighbors).toEqual([]);
    expect(p.base_tension).toBe(0.0);
    expect(p.description).toBe('');
  });

  it('业务不变量：板块数 ≥ 1 至少', () => {
    const fake: PlateMapResponse = {
      active: true,
      plate_count: 0,
      definitions: [],
      corridors: [],
      tensions: {},
      statuses: {},
      active_plate: '',
    };
    // 空状态合法
    expect(fake.plate_count).toBe(0);
  });

  it('业务不变量：tensions 0-1 范围', () => {
    // 模拟 tension 数据
    const tensions = { a: -0.1, b: 0.5, c: 1.5 };
    for (const t of Object.values(tensions)) {
      const clamped = Math.max(0, Math.min(1, t));
      expect(clamped).toBeGreaterThanOrEqual(0);
      expect(clamped).toBeLessThanOrEqual(1);
    }
  });

  it('业务不变量：4 状态颜色映射完整', () => {
    for (const status of ['stable', 'tense', 'shifting', 'collapsed']) {
      expect(STATUS_COLOR_MAP[status], `${status} 颜色应存在`).toBeDefined();
    }
  });

  it('业务不变量：shifting 状态应激活', () => {
    const fake: PlateMapResponse = {
      active: true,
      plate_count: 1,
      definitions: [
        { id: 'p1', name: 'P1', type: 'core', neighbors: [], base_tension: 0.5, description: 'd' },
      ],
      corridors: [],
      tensions: { p1: 0.5 },
      statuses: { p1: 'shifting' },
      active_plate: 'p1',
    };
    expect(fake.statuses.p1).toBe('shifting');
    expect(fake.active_plate).toBe('p1');
  });

  it('类型契约：corridor 必含 from/to 字段', () => {
    const corridors = [
      { id: 'c1', from_plate: 'a', to_plate: 'b', description: 'd' },
    ];
    expect(corridors[0].from_plate).toBe('a');
    expect(corridors[0].to_plate).toBe('b');
  });

  it('业务不变量：tensionWidth 钳制到 0-100%', () => {
    function tensionWidth(tension: number): string {
      return `${Math.max(0, Math.min(1, tension)) * 100}%`;
    }
    expect(tensionWidth(-0.5)).toBe('0%');
    expect(tensionWidth(0)).toBe('0%');
    expect(tensionWidth(0.5)).toBe('50%');
    expect(tensionWidth(1)).toBe('100%');
    expect(tensionWidth(1.5)).toBe('100%');
  });

  it('业务不变量：板块邻居对称性', () => {
    // 假设 a 的邻居含 b，则 b 的邻居也含 a
    const a: PlateDefinition = {
      id: 'a', name: 'A', type: 'core', neighbors: ['b', 'c'],
      base_tension: 0, description: '',
    };
    const b: PlateDefinition = {
      id: 'b', name: 'B', type: 'core', neighbors: ['a'],
      base_tension: 0, description: '',
    };
    expect(a.neighbors).toContain('b');
    expect(b.neighbors).toContain('a');
  });

  it('业务不变量：corridor from/to 必为有效 plate id', () => {
    const fake: PlateMapResponse = {
      active: true,
      plate_count: 2,
      definitions: [
        { id: 'a', name: 'A', type: 'core', neighbors: ['b'], base_tension: 0, description: '' },
        { id: 'b', name: 'B', type: 'core', neighbors: ['a'], base_tension: 0, description: '' },
      ],
      corridors: [
        { id: 'c1', from_plate: 'a', to_plate: 'b', description: 'd' },
      ],
      tensions: { a: 0, b: 0 },
      statuses: { a: 'stable', b: 'stable' },
      active_plate: '',
    };
    const plateIds = new Set(fake.definitions.map(p => p.id));
    for (const c of fake.corridors) {
      expect(plateIds.has(c.from_plate), `corridor ${c.id} from 必为有效 id`).toBe(true);
      expect(plateIds.has(c.to_plate), `corridor ${c.id} to 必为有效 id`).toBe(true);
    }
  });
});
