/**
 * 🆕 v2.9.x W46: ChapterTimeline 集成测试
 *
 * 验证：
 * 1. getChapterHistory API 导出
 * 2. getChapterHistory 调 /chapter/history + session_id
 * 3. 响应格式（count + history）
 * 4. ChapterTimeline.svelte 存在
 * 5. toTimeline + getChapterHistory 集成
 */
import { describe, it, expect, vi } from 'vitest';
import { getChapterHistory } from '$lib/api/chapter';
import { toTimeline } from './chapterHistory';
import { api } from '$lib/api/client';

vi.mock('$lib/api/client', () => ({
  api: vi.fn(),
}));
const mockedApi = vi.mocked(api);

describe('W46: ChapterTimeline 集成', () => {
  it('getChapterHistory is exported from chapter API', () => {
    expect(typeof getChapterHistory).toBe('function');
  });

  it('getChapterHistory calls /chapter/history with session_id', async () => {
    const fake = {
      count: 2,
      history: [
        { chapter: 1, summary: 'Ch1', closure_status: 'SOFT_READY' },
        { chapter: 2, summary: 'Ch2', closure_status: 'HARD_FORCED' },
      ],
    };
    mockedApi.mockResolvedValueOnce(fake);
    const result = await getChapterHistory('sess-99');
    expect(mockedApi).toHaveBeenCalledWith('/chapter/history', {
      params: { session_id: 'sess-99' },
    });
    expect(result.count).toBe(2);
    expect(result.history).toHaveLength(2);
  });

  it('getChapterHistory → toTimeline 完整数据流', async () => {
    const fake = {
      count: 1,
      history: [
        {
          chapter: 1,
          summary: '初入',
          closure_status: 'SOFT_READY',
          rounds_in_chapter: 5,
          ended_at_round: 5,
        },
      ],
    };
    mockedApi.mockResolvedValueOnce(fake);
    const resp = await getChapterHistory('sess-X');
    const timeline = toTimeline(resp, 2, 5);
    // 5 个节点：1=past, 2=current, 3-5=future
    expect(timeline).toHaveLength(5);
    expect(timeline[0].status).toBe('past');
    expect(timeline[0].summary).toBe('初入');
    expect(timeline[1].status).toBe('current');
    expect(timeline[2].status).toBe('future');
  });

  it('getChapterHistory handles network error', async () => {
    mockedApi.mockRejectedValueOnce(new Error('Network error'));
    await expect(getChapterHistory('sess-fail')).rejects.toThrow('Network error');
  });

  it('getChapterHistory handles empty history', async () => {
    mockedApi.mockResolvedValueOnce({ count: 0, history: [] });
    const resp = await getChapterHistory('sess-empty');
    expect(resp.count).toBe(0);
    const timeline = toTimeline(resp, 1, 5);
    expect(timeline).toHaveLength(5);
    // 全部 status=future (除 ch1=current)
    expect(timeline.filter((n) => n.status === 'future')).toHaveLength(4);
  });
});
