/**
 * 🆕 v2.10.x W55: timelineActions 测试
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  getFavorites,
  addFavorite,
  removeFavorite,
  isFavorite,
  jumpToChapter,
  canBookmark,
  getTimelineActions,
} from './timelineActions';
import type { TimelineNode } from './chapterHistory';

const makeNode = (overrides: Partial<TimelineNode>): TimelineNode => ({
  chapter: 1,
  summary: '',
  core_event: '',
  key_choice: '',
  build_summary: '',
  path_summary: '',
  rounds_in_chapter: 0,
  ended_at_round: 0,
  ended_at: '',
  transition: '',
  closure_status: '',
  isFirst: false,
  isLast: false,
  durationLabel: '',
  closureLabel: '',
  status: 'past',
  ...overrides,
});

describe('W55: 收藏管理', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('初始无收藏', () => {
    expect(getFavorites()).toEqual([]);
  });

  it('addFavorite 添加', () => {
    addFavorite(3, '第 3 章');
    expect(getFavorites()).toHaveLength(1);
    expect(getFavorites()[0].chapter).toBe(3);
  });

  it('addFavorite 重复不增加', () => {
    addFavorite(3, 'Title 1');
    addFavorite(3, 'Title 2');
    expect(getFavorites()).toHaveLength(1);
  });

  it('removeFavorite 移除', () => {
    addFavorite(3, 'X');
    removeFavorite(3);
    expect(getFavorites()).toHaveLength(0);
  });

  it('isFavorite 检查', () => {
    addFavorite(3, 'X');
    expect(isFavorite(3)).toBe(true);
    expect(isFavorite(5)).toBe(false);
  });
});

describe('W55: jumpToChapter', () => {
  it('jump 只能到 past', () => {
    expect(jumpToChapter(3, 5)).toBe(true);
    expect(jumpToChapter(5, 5)).toBe(false); // current
    expect(jumpToChapter(7, 5)).toBe(false); // future
  });
});

describe('W55: canBookmark', () => {
  it('past + summary → canBookmark', () => {
    const node = makeNode({ status: 'past', summary: 'x' });
    expect(canBookmark(node)).toBe(true);
  });

  it('future → cannot bookmark', () => {
    const node = makeNode({ status: 'future', summary: 'x' });
    expect(canBookmark(node)).toBe(false);
  });

  it('past + empty summary → cannot bookmark', () => {
    const node = makeNode({ status: 'past', summary: '' });
    expect(canBookmark(node)).toBe(false);
  });
});

describe('W55: getTimelineActions', () => {
  it('只返 past 章节', () => {
    const history = [
      makeNode({ chapter: 1, summary: 'S1', status: 'past' }),
      makeNode({ chapter: 2, summary: 'S2', status: 'current' }),
      makeNode({ chapter: 3, summary: 'S3', status: 'future' }),
    ];
    const actions = getTimelineActions(history, 2);
    expect(actions).toHaveLength(1);
    expect(actions[0].chapter).toBe(1);
  });

  it('canJump / canBookmark 正确', () => {
    const history = [
      makeNode({ chapter: 1, summary: 'S1', status: 'past' }),
    ];
    const actions = getTimelineActions(history, 5);
    expect(actions[0].canJump).toBe(true);
    expect(actions[0].canBookmark).toBe(true);
  });
});
