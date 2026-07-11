/**
 * 🆕 v2.9.x W45: chapterHistory 辅助函数测试
 */
import { describe, it, expect } from 'vitest';
import {
  toTimeline,
  buildDurationLabel,
  buildClosureLabel,
  progressPercent,
  chapterDotX,
  type ChapterRecord,
  type ChapterHistoryResponse,
} from './chapterHistory';

const sampleHistory: ChapterHistoryResponse = {
  count: 3,
  history: [
    {
      chapter: 1,
      summary: '初入盛泽，偶遇琴师',
      core_event: '遇周文衡',
      key_choice: '驻足倾听',
      build_summary: '外望人身份展示',
      path_summary: '文士路线',
      rounds_in_chapter: 5,
      ended_at_round: 5,
      ended_at: '2026-07-11T10:00:00',
      transition: '琴声牵出夜航船',
      closure_status: 'SOFT_READY',
    },
    {
      chapter: 2,
      summary: '茶馆夜谈，明史风云',
      core_event: '茶馆议政',
      key_choice: '执笔记录',
      build_summary: '文士技能 +1',
      path_summary: '文士+史官',
      rounds_in_chapter: 8,
      ended_at_round: 13,
      ended_at: '2026-07-11T10:08:00',
      transition: '至 河西走廊',
      closure_status: 'HARD_FORCED',
    },
    {
      chapter: 3,
      summary: '河西遇商队',
      core_event: '商队冲突',
      key_choice: '调解',
      build_summary: '调停 +1',
      path_summary: '商路',
      rounds_in_chapter: 6,
      ended_at_round: 19,
      ended_at: '2026-07-11T10:15:00',
      transition: '至 西北',
      closure_status: 'SOFT_READY',
    },
  ],
};

describe('buildDurationLabel', () => {
  it('formats rounds + range', () => {
    const rec: ChapterRecord = {
      ...sampleHistory.history[0],
      rounds_in_chapter: 5,
      ended_at_round: 5,
    };
    expect(buildDurationLabel(rec)).toBe('5 轮 (round 1-5)');
  });

  it('handles multi-round range', () => {
    const rec: ChapterRecord = {
      ...sampleHistory.history[1],
      rounds_in_chapter: 8,
      ended_at_round: 13,
    };
    expect(buildDurationLabel(rec)).toBe('8 轮 (round 6-13)');
  });

  it('returns 未开始 for empty', () => {
    const rec: ChapterRecord = {
      ...sampleHistory.history[0],
      rounds_in_chapter: 0,
    };
    expect(buildDurationLabel(rec)).toBe('未开始');
  });
});

describe('buildClosureLabel', () => {
  it('translates SOFT_READY to 软收束', () => {
    expect(buildClosureLabel('SOFT_READY')).toBe('软收束');
  });

  it('translates HARD_FORCED to 强制收尾', () => {
    expect(buildClosureLabel('HARD_FORCED')).toBe('强制收尾');
  });

  it('returns original for unknown', () => {
    expect(buildClosureLabel('UNKNOWN')).toBe('UNKNOWN');
  });
});

describe('toTimeline', () => {
  it('marks first and last', () => {
    const tl = toTimeline(sampleHistory, 4, 10);
    const ch1 = tl.find((n) => n.chapter === 1)!;
    const ch10 = tl.find((n) => n.chapter === 10)!;
    expect(ch1.isFirst).toBe(true);
    expect(ch10.isLast).toBe(true);
  });

  it('sets status based on current chapter', () => {
    const tl = toTimeline(sampleHistory, 4, 10);
    expect(tl.find((n) => n.chapter === 1)!.status).toBe('past');
    expect(tl.find((n) => n.chapter === 2)!.status).toBe('past');
    expect(tl.find((n) => n.chapter === 3)!.status).toBe('past');
    expect(tl.find((n) => n.chapter === 4)!.status).toBe('current');
    expect(tl.find((n) => n.chapter === 5)!.status).toBe('future');
  });

  it('fills future placeholders for missing chapters', () => {
    const tl = toTimeline(sampleHistory, 4, 10);
    // 应该有 10 个节点（1-10）
    expect(tl).toHaveLength(10);
    // 章节 4 应是 current 但 history 中没有（占位）
    const ch4 = tl.find((n) => n.chapter === 4)!;
    expect(ch4.summary).toBe(''); // 空 summary（占位）
    expect(ch4.status).toBe('current');
  });

  it('attaches durationLabel and closureLabel', () => {
    const tl = toTimeline(sampleHistory, 4, 10);
    const ch1 = tl.find((n) => n.chapter === 1)!;
    expect(ch1.durationLabel).toBe('5 轮 (round 1-5)');
    expect(ch1.closureLabel).toBe('软收束');
    const ch2 = tl.find((n) => n.chapter === 2)!;
    expect(ch2.closureLabel).toBe('强制收尾');
  });

  it('handles empty history (chapter 1 future)', () => {
    const tl = toTimeline({ count: 0, history: [] }, 1, 10);
    expect(tl).toHaveLength(10);
    // 全部是 future (except 1 = current)
    expect(tl.filter((n) => n.status === 'future')).toHaveLength(9);
    expect(tl.find((n) => n.chapter === 1)!.status).toBe('current');
  });
});

describe('progressPercent', () => {
  it('returns 0 for chapter 0', () => {
    expect(progressPercent(0, 10)).toBe(0);
  });

  it('returns 50 for chapter 5 of 10', () => {
    expect(progressPercent(5, 10)).toBe(50);
  });

  it('caps at 100', () => {
    expect(progressPercent(15, 10)).toBe(100);
  });

  it('handles 0 total gracefully', () => {
    expect(progressPercent(5, 0)).toBe(0);
  });
});

describe('chapterDotX', () => {
  it('first dot at 0', () => {
    expect(chapterDotX(1, 10, 100)).toBe(0);
  });

  it('last dot at full width', () => {
    expect(chapterDotX(10, 10, 100)).toBe(100);
  });

  it('middle dot at half', () => {
    expect(chapterDotX(5, 10, 100)).toBeCloseTo(44.44, 1);
  });

  it('handles 1 chapter total', () => {
    expect(chapterDotX(1, 1, 100)).toBe(0);
  });
});
