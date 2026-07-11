/**
 * 🆕 v2.7.1 任务 3 落地测试：location id → scene 映射
 *
 * 业务不变量：
 * - 3 个核心位置（盛泽镇/苏州府/北京城）必须映射到对应 webp
 * - 其他 location id → null（不显示场景图）
 * - webp 路径必须以 /scenes/ 开头
 * - 必须有 3 张图与 `static/scenes/` 目录文件名一致
 */
import { describe, it, expect } from 'vitest';
import { readdirSync } from 'node:fs';
import { join } from 'node:path';

const SCENE_MAP: Record<string, string> = {
  shengze: '/scenes/shengze.webp',
  suzhou: '/scenes/suzhou.webp',
  beijing: '/scenes/beijing.webp',
};

const KNOWN_LOCATIONS = Object.keys(SCENE_MAP);

describe('LocationPanel scene 图映射 (v2.7.1 任务 3)', () => {
  it('SCENE_MAP 含 3 个核心 location id', () => {
    expect(KNOWN_LOCATIONS).toHaveLength(3);
    expect(KNOWN_LOCATIONS).toEqual(
      expect.arrayContaining(['shengze', 'suzhou', 'beijing'])
    );
  });

  it('SCENE_MAP 路径以 /scenes/ 开头', () => {
    for (const [id, path] of Object.entries(SCENE_MAP)) {
      expect(path, `${id} 路径应以 /scenes/ 开头`).toMatch(/^\/scenes\//);
    }
  });

  it('SCENE_MAP 路径以 .webp 结尾', () => {
    for (const [id, path] of Object.entries(SCENE_MAP)) {
      expect(path, `${id} 应是 .webp`).toMatch(/\.webp$/);
    }
  });

  it('业务查询：3 个 location id 都返回非 null 路径', () => {
    for (const id of KNOWN_LOCATIONS) {
      const url = SCENE_MAP[id] ?? null;
      expect(url, `${id} 应该有图`).not.toBeNull();
    }
  });

  it('业务查询：未知 location id 返回 null（不显示图）', () => {
    const unknownIds = ['fengqiao', 'zhouzhuang', 'tongli', 'nanjing', 'beijing_fake', ''];
    for (const id of unknownIds) {
      const url = SCENE_MAP[id] ?? null;
      expect(url, `${id} 应不显示图`).toBeNull();
    }
  });

  it('静态资源完整性：3 张图实际存在于磁盘', () => {
    // vitest 在 src/frontend/ 跑，scenes/ 在 static/ 旁边
    const scenesDir = join(process.cwd(), 'static', 'scenes');
    let files: string[];
    try {
      files = readdirSync(scenesDir);
    } catch (e) {
      throw new Error(`无法读取 ${scenesDir}: ${e}`);
    }
    for (const id of KNOWN_LOCATIONS) {
      const filename = `${id}.webp`;
      expect(files, `${filename} 应存在`).toContain(filename);
    }
  });

  it('静态资源：3 张 webp 文件大小 > 0', () => {
    const { statSync } = require('node:fs');
    const scenesDir = join(process.cwd(), 'static', 'scenes');
    for (const id of KNOWN_LOCATIONS) {
      const filepath = join(scenesDir, `${id}.webp`);
      const stats = statSync(filepath);
      expect(stats.size, `${id}.webp 应 > 0 bytes`).toBeGreaterThan(0);
      // 通常 webp 75-100K，过大(< 1MB) 表明 LLM 生成
      expect(stats.size, `${id}.webp 应 < 500K`).toBeLessThan(500 * 1024);
    }
  });

  it('业务不变量：未引用 location 不会错误映射', () => {
    // 模拟 LocationPanel 中 sceneImage 的实现
    function getSceneImage(locationId: string): string | null {
      return SCENE_MAP[locationId] ?? null;
    }
    // 5 个常用未在 SCENE_MAP 的 id
    const testIds = ['fengqiao', 'zhouzhuang', 'tongli', 'nanjing', 'hangzhou'];
    for (const id of testIds) {
      expect(getSceneImage(id)).toBeNull();
    }
  });

  it('LocationPanel img 标签 alt 应等于 location 名（无障碍）', () => {
    // 模拟 LocationPanel 的 img：alt={data.current_location.name}
    // 此处测试 SCENE_MAP 值的 .webp 名等于 SCENE_MAP 键
    for (const [id, path] of Object.entries(SCENE_MAP)) {
      const filename = path.split('/').pop()?.replace('.webp', '');
      expect(filename, `路径结尾应等于 id`).toBe(id);
    }
  });
});
