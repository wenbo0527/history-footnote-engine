/**
 * 🆕 v2.8.0 W22: chapter.ts 前端 API 客户端测试
 *
 * 目标：
 * - getChapterState / getChapterBlueprint / recordChapterChoice / getChapterHistory
 * - mock global.fetch → 验证 URL / method / body / 响应解析
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getChapterState,
  getChapterBlueprint,
  recordChapterChoice,
  getChapterHistory,
  type ChapterStateResponse,
  type ChapterBlueprintResponse,
} from './chapter';

// ofetch 包了一层 fetch；为简化测试，用 vi.mock 替换 api
import { api } from './client';
vi.mock('./client', () => ({
  api: vi.fn(),
}));
const mockedApi = vi.mocked(api);

describe('chapter API client (v2.8.0 段 UI)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getChapterState: 用 GET 请求 + session_id 参数', async () => {
    const fake: ChapterStateResponse = {
      active: true,
      current_chapter: 1,
      current_node: 2,
      node_count: 4,
      chapter_start_round: 1,
      round_number: 8,
      rounds_elapsed: 8,
      last_closure_status: 'CONTINUE',
      progress_pct: 50,
      player_build: '外望人',
      main_path_focus: 'main_tax_resistance',
      active_plate: 'jiangnan',
    };
    mockedApi.mockResolvedValueOnce(fake);

    const result = await getChapterState('sess-1');
    expect(mockedApi).toHaveBeenCalledWith('/chapter/state', {
      params: { session_id: 'sess-1' },
    });
    expect(result).toEqual(fake);
    expect(result.active).toBe(true);
    expect(result.progress_pct).toBe(50);
  });

  it('getChapterState: 老存档（active=false）也能正确返回', async () => {
    const fake: ChapterStateResponse = {
      active: false,
      current_chapter: 0,
      current_node: 1,
      node_count: 4,
      chapter_start_round: 1,
      round_number: 3,
      rounds_elapsed: 0,
      last_closure_status: 'INIT',
      progress_pct: 0,
      player_build: '',
      main_path_focus: '',
      active_plate: '',
    };
    mockedApi.mockResolvedValueOnce(fake);

    const result = await getChapterState('sess-2');
    expect(result.active).toBe(false);
    expect(result.current_chapter).toBe(0);
  });

  it('getChapterBlueprint: 解析节点数组', async () => {
    const fake: ChapterBlueprintResponse = {
      active: true,
      chapter_id: 1,
      chapter_title: '且听下回分解 · 春蚕',
      chapter_subtitle: '春风又绿',
      transition_hint: 'season',
      current_node: 1,
      nodes: [
        {
          index: 1,
          role: 'introduction',
          scene: '春市开张',
          npc_ids: ['fm_wife'],
          option_directions: [{ text: '赶集', path: 'main_tax_resistance' }],
        },
      ],
      meta: { act: 'departure', role: 'ordinary' },
    };
    mockedApi.mockResolvedValueOnce(fake);

    const result = await getChapterBlueprint('sess-3');
    expect(mockedApi).toHaveBeenCalledWith('/chapter/blueprint', {
      params: { session_id: 'sess-3' },
    });
    expect(result.nodes.length).toBe(1);
    expect(result.nodes[0].role).toBe('introduction');
    expect(result.meta.act).toBe('departure');
  });

  it('recordChapterChoice: POST + body', async () => {
    const fake = {
      recorded: true,
      path: 'side_silk_trade',
      recent_path_choices: ['side_silk_trade'],
    };
    mockedApi.mockResolvedValueOnce(fake);

    const result = await recordChapterChoice('sess-4', 'side_silk_trade');
    expect(mockedApi).toHaveBeenCalledWith('/chapter/record_choice', {
      method: 'POST',
      body: { session_id: 'sess-4', path: 'side_silk_trade' },
    });
    expect(result.recorded).toBe(true);
    expect(result.recent_path_choices).toContain('side_silk_trade');
  });

  it('getChapterHistory: 返回章节列表 + count', async () => {
    const fake = {
      count: 2,
      history: [
        {
          chapter: 1,
          summary: '暮色渐沉',
          closure_status: 'SOFT_READY',
        },
        {
          chapter: 2,
          summary: '举步维艰',
          closure_status: 'SOFT_READY',
        },
      ],
    };
    mockedApi.mockResolvedValueOnce(fake);

    const result = await getChapterHistory('sess-5');
    expect(mockedApi).toHaveBeenCalledWith('/chapter/history', {
      params: { session_id: 'sess-5' },
    });
    expect(result.count).toBe(2);
    expect(result.history).toHaveLength(2);
    expect(result.history[0].chapter).toBe(1);
  });
});
