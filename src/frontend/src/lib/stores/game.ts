/**
 * Game 状态 - 当前游戏状态
 */
import { writable, derived, type Readable, type Writable } from 'svelte/store';
import type { GameState, Narrative, VoiceOption } from '$lib/api/types';

export const game: Writable<GameState | null> = writable(null);
export const isLoading: Writable<boolean> = writable(false);
export const lastError: Writable<string | null> = writable(null);

// 派生：narrative 列表
export const narrativeHistory: Readable<Narrative[]> = derived(
  game,
  ($game) => $game?.narrative_history ?? []
);

// 派生：当前回合 narrative
export const currentNarrative: Readable<Narrative | null> = derived(
  game,
  ($game) => $game?.narrative ?? null
);

// 派生：当前 voice options
export const voiceOptions: Readable<VoiceOption[]> = derived(
  game,
  ($game) => $game?.last_voice_options ?? []
);

export const gameActions = {
  set(state: GameState) {
    game.set(state);
    lastError.set(null);
  },

  update(partial: Partial<GameState>) {
    game.update((g) => g ? { ...g, ...partial } : g);
  },

  setLoading(v: boolean) {
    isLoading.set(v);
  },

  setError(msg: string | null) {
    lastError.set(msg);
  },

  reset() {
    game.set(null);
    isLoading.set(false);
    lastError.set(null);
  }
};
