<script lang="ts">
  /**
   * 🆕 v2.10.x — WorldMapContainer — 接入 gameStore 的容器组件
   *
   * 职责：
   * - 订阅 `game` store → 提取 city/visited/heard
   * - 调用 `gameActions.update()` 触发 travel
   * - 通知后端 /api/game/travel
   * - 从 narrative_history 解析玩家路径
   *
   * 用法：
   *   <WorldMapContainer />  <!-- 完整接入，自动跟 game 联动 -->
   *
   * 或（mock 模式）：
   *   <WorldMap :state={...} onCityClick={...} />  <!-- 之前的方式 -->
   */

  import { game, gameActions } from '$lib/stores/game';
  import { onMount } from 'svelte';
  import WorldMap from './WorldMap.svelte';
  import type { GameState } from '$lib/api/types';

  interface Props {
    showOverlay?: boolean;
    onClose?: () => void;
  }

  let { showOverlay = false, onClose }: Props = $props();

  // 从 narrative_history 解析"已访问城市"列表
  // (Narrative 类型只有 round + content, 没有 location_change 字段)
  // 简化：直接使用 heard_locations + 当前 city
  function parseVisitedCities(state: GameState | null): string[] {
    if (!state) return [];
    // 暂用 heard_locations 当作 visited（因为没有专门的 visited 字段）
    const heard = parseHeard(state);
    return heard.filter(c => c !== state.city);
  }

  // heard_locations 可能是 string[] 或 JSON string
  function parseHeard(state: GameState | null): string[] {
    if (!state) return [];
    const h = (state as any).heard_locations;
    if (Array.isArray(h)) return h;
    if (typeof h === 'string') {
      try { return JSON.parse(h); } catch { return []; }
    }
    return [];
  }

  // 从 narrative_history 解析"路径"（用于 Phase 8.4）
  // 简化：基于 timeline 事件或 random travel sample
  function parseTravelPath(state: GameState | null): Array<{ from: string; to: string; days: number; round?: number }> {
    if (!state) return [];
    // Narrative 只有 content (markdown)，需要正则提取 "前往 X" / "抵達 X"
    const path: Array<{ from: string; to: string; days: number; round?: number }> = [];
    let lastFrom = state.city;
    for (const n of state.narrative_history ?? []) {
      const match = n?.content?.match(/(?:前往|抵達|到達|來到|到)([^，。\s]+)/);
      if (match) {
        const to = match[1];
        path.push({
          from: lastFrom,
          to,
          days: 1,
          round: n.round,
        });
        lastFrom = to;
      }
    }
    return path;
  }

  // 派生：玩家状态
  const visitedCities = $derived(parseVisitedCities($game));
  const heardCities = $derived(parseHeard($game));
  const travelPath = $derived(parseTravelPath($game));

  // Travel action — 调后端 API
  async function handleTravel(cityId: string) {
    if (!$game) {
      console.warn('[WorldMapContainer] no game state, cannot travel');
      return;
    }
    if (cityId === $game.city) return;

    try {
      gameActions.setLoading(true);
      const response = await fetch('/api/game/travel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: $game.session_id,
          to_city: cityId,
        }),
      });
      if (!response.ok) {
        throw new Error(`Travel failed: ${response.statusText}`);
      }
      const newState: GameState = await response.json();
      gameActions.set(newState);
    } catch (err) {
      console.error('[WorldMapContainer] travel error:', err);
      gameActions.setError(err instanceof Error ? err.message : 'Travel failed');
    } finally {
      gameActions.setLoading(false);
    }
  }

  // 城市点击 — 仅弹窗（不直接 travel）
  function handleCityClick(cityId: string) {
    console.log('[WorldMapContainer] city clicked:', cityId);
  }
</script>

{#if $game}
  <WorldMap
    gameState={$game}
    {visitedCities}
    {heardCities}
    travelPath={travelPath}
    onCityClick={handleCityClick}
    onTravel={handleTravel}
  />
{:else}
  <div class="no-state">
    <p>載入中…或請先登入</p>
  </div>
{/if}

<style>
  .no-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #5a4a36;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 18px;
  }
</style>
