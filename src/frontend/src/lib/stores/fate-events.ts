/**
 * fate-events.ts - 命运卡事件总线（v2.7）
 *
 * 设计动机：CharCard 命运卡 chip 点击 → 跳到侧栏对应卡
 *
 * 用法：
 *   // CharCard 点 chip
 *   fateEvents.scrollToCard('windfall');
 *
 *   // FateHandPanel 监听
 *   $effect(() => {
 *     const cardId = fateEvents.scrollToCardId;
 *     if (cardId) {
 *       // 滚动 + 高亮
 *     }
 *   });
 */
import { writable } from 'svelte/store';

interface FateEvents {
  scrollToCardId: string | null;  // 要滚动到的卡 id
  useCardId: string | null;        // 一键使用的卡 id
  highlightCardId: string | null;  // 高亮的卡 id（脉冲）
  lastUpdate: number;              // 时间戳（用于触发响应）
}

function createFateEvents() {
  const { subscribe, set, update } = writable<FateEvents>({
    scrollToCardId: null,
    useCardId: null,
    highlightCardId: null,
    lastUpdate: 0,
  });

  return {
    subscribe,
    scrollToCard(cardId: string) {
      set({
        scrollToCardId: cardId,
        useCardId: null,
        highlightCardId: cardId,
        lastUpdate: Date.now(),
      });
    },
    useCard(cardId: string) {
      set({
        scrollToCardId: cardId,
        useCardId: cardId,
        highlightCardId: cardId,
        lastUpdate: Date.now(),
      });
    },
    clear() {
      set({
        scrollToCardId: null,
        useCardId: null,
        highlightCardId: null,
        lastUpdate: 0,
      });
    },
  };
}

export const fateEvents = createFateEvents();
