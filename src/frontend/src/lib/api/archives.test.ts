/**
 * 🆕 v2.10.x W51: 存档列表 API 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  listArchives,
  sortByRecent,
  groupByEra,
  type ArchiveSession,
} from './archives';
import { api } from './client';

vi.mock('$lib/api/client', () => ({
  api: vi.fn(),
}));
const mockedApi = vi.mocked(api);

const sampleArchives: ArchiveSession[] = [
  {
    session_id: 's1',
    era_id: 'wanli1587',
    current_round: 5,
    current_date: '万历十五年三月',
    summary: '初入盛泽',
    created_at: '2026-07-10T10:00:00',
    updated_at: '2026-07-11T15:00:00',
  },
  {
    session_id: 's2',
    era_id: 'wanli1587',
    current_round: 12,
    current_date: '万历十五年五月',
    summary: '茶馆遇文衡',
    created_at: '2026-07-09T08:00:00',
    updated_at: '2026-07-11T10:00:00',
  },
  {
    session_id: 's3',
    era_id: 'hongwu1399',
    current_round: 3,
    current_date: '洪武二年',
    summary: '应天开局',
    created_at: '2026-07-08T12:00:00',
    updated_at: '2026-07-09T20:00:00',
  },
];

describe('W51: listArchives', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('调 /archives 端点', async () => {
    mockedApi.mockResolvedValueOnce({ count: 1, sessions: [sampleArchives[0]] });
    await listArchives();
    expect(mockedApi).toHaveBeenCalledWith('/archives', { params: {} });
  });

  it('带 account 参数', async () => {
    mockedApi.mockResolvedValueOnce({ count: 0, sessions: [] });
    await listArchives('user-123');
    expect(mockedApi).toHaveBeenCalledWith('/archives', {
      params: { account: 'user-123' },
    });
  });

  it('include_archived=true 时加参数', async () => {
    mockedApi.mockResolvedValueOnce({ count: 0, sessions: [] });
    await listArchives('user-1', true);
    expect(mockedApi).toHaveBeenCalledWith('/archives', {
      params: { account: 'user-1', include_archived: 1 },
    });
  });

  it('网络错处理', async () => {
    mockedApi.mockRejectedValueOnce(new Error('Network error'));
    await expect(listArchives()).rejects.toThrow('Network error');
  });
});

describe('sortByRecent', () => {
  it('按 updated_at 倒序', () => {
    const sorted = sortByRecent(sampleArchives);
    expect(sorted[0].session_id).toBe('s1');  // 最新
    expect(sorted[1].session_id).toBe('s2');
    expect(sorted[2].session_id).toBe('s3');  // 最旧
  });

  it('fallback to created_at', () => {
    const noUpdated = sampleArchives.map((s) => ({ ...s, updated_at: undefined }));
    const sorted = sortByRecent(noUpdated);
    expect(sorted[0].session_id).toBe('s1');  // 最新 created_at
  });

  it('不修改原数组', () => {
    const original = [...sampleArchives];
    sortByRecent(sampleArchives);
    expect(sampleArchives).toEqual(original);
  });

  it('空数组', () => {
    expect(sortByRecent([])).toEqual([]);
  });
});

describe('groupByEra', () => {
  it('按 era_id 分组', () => {
    const grouped = groupByEra(sampleArchives);
    expect(Object.keys(grouped)).toEqual(['wanli1587', 'hongwu1399']);
    expect(grouped['wanli1587']).toHaveLength(2);
    expect(grouped['hongwu1399']).toHaveLength(1);
  });

  it('空数组返空', () => {
    expect(groupByEra([])).toEqual({});
  });

  it('缺 era_id → unknown', () => {
    const noEra: ArchiveSession[] = [{ ...sampleArchives[0], era_id: '' }];
    const grouped = groupByEra(noEra);
    expect(grouped['unknown']).toHaveLength(1);
  });
});
