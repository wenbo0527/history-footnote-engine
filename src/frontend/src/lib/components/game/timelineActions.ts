/**
 * 🆕 v2.10.x W55: 时间线增强 — 拖拽跳转 + 收藏
 *
 * 用法：useTimelineActions(history) 返 actions
 */
import type { TimelineNode } from './chapterHistory';

export interface TimelineAction {
  type: 'jump' | 'favorite' | 'bookmark';
  chapter: number;
  timestamp: number;
}

export interface FavoriteChapter {
  chapter: number;
  title: string;
  addedAt: string;
}

const FAV_KEY = 'hfe_favorite_chapters';

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

export function getFavorites(): FavoriteChapter[] {
  if (!isBrowser()) return [];
  try {
    const raw = localStorage.getItem(FAV_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addFavorite(chapter: number, title: string): void {
  if (!isBrowser()) return;
  const favs = getFavorites();
  if (favs.some((f) => f.chapter === chapter)) return;
  favs.push({ chapter, title, addedAt: new Date().toISOString() });
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify(favs));
  } catch { /* ignore */ }
}

export function removeFavorite(chapter: number): void {
  if (!isBrowser()) return;
  const favs = getFavorites().filter((f) => f.chapter !== chapter);
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify(favs));
  } catch { /* ignore */ }
}

export function isFavorite(chapter: number): boolean {
  return getFavorites().some((f) => f.chapter === chapter);
}

export function jumpToChapter(chapter: number, currentChapter: number): boolean {
  // 只能跳到已结束章节（past）
  return chapter < currentChapter;
}

export function canBookmark(node: TimelineNode): boolean {
  return node.status === 'past' && !!node.summary;
}

export function getTimelineActions(
  history: TimelineNode[],
  currentChapter: number
): { chapter: number; title: string; canJump: boolean; canBookmark: boolean }[] {
  return history
    .filter((n) => n.status === 'past')
    .map((n) => ({
      chapter: n.chapter,
      title: n.summary || `第 ${n.chapter} 章`,
      canJump: jumpToChapter(n.chapter, currentChapter),
      canBookmark: canBookmark(n),
    }));
}
