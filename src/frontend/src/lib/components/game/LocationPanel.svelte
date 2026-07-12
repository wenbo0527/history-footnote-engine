<script lang="ts">
  /**
   * LocationPanel - 当前位置 + 移动选项（v2.4 文字地图）
   *
   * 3 个子区块（紧凑布局）：
   *   1. 当前位置标识（带邻居按钮）
   *   2. 移动选项（横向胶囊 + AP 消耗）
   *   3. 听过没去过（折叠展示）
   */
  import { game, gameActions } from '$lib/stores';
  import { locationList, locationMove } from '$lib/api/location';
  import { toast } from '$lib/components/design-system/Toast.svelte';
  import type {
    LocationListResponse,
    LocationInfo,
    VoiceOption
  } from '$lib/api/types';
  import LocationMovePill from './LocationMovePill.svelte';

  interface Props {
    /** 已加载的 location data（由父组件传入） */
    data: LocationListResponse | null;
  }

  let { data }: Props = $props();

  let moving = $state(false);
  let showHeard = $state(false);

  async function handleMove(target: string) {
    if (moving || !$game) return;
    if (data?.current_location?.id === target) return;
    moving = true;
    try {
      const res = await locationMove($game.session_id, target);
      // 1) 移动叙事推到 narrative 区
      if (res.narrative) {
        const existing = $game.narrative || { round: 0, content: '' };
        gameActions.set({
          ...$game,
          narrative: {
            ...existing,
            content: res.narrative + (existing.content ? '\n\n' + existing.content : '')
          },
          action_points_current: res.new_ap,
          last_voice_options: res.new_voice_options
        } as any);
      }
      // 2) 通知 heard 新解锁
      if (res.newly_heard && res.newly_heard.length > 0) {
        toast.success(`你听说了新地方：${res.newly_heard.join('、')}`);
      }
      // 3) 通知父组件刷新 location data
      data = await locationList($game.session_id);
      toast.info(`已到 ${res.to_location_name}（消耗 ${res.ap_cost} AP）`);
    } catch (e) {
      const err = e as Error & { data?: any };
      const reason = err.data?.reason || err.message;
      toast.warning(reason || '移动失败');
    } finally {
      moving = false;
    }
  }

  // 当前位置 = data.current_location
  // 移动选项 = 当前 location 的 neighbors（已包含 heard）
  // 优先从 game.last_voice_options 里筛 is_move=true，否则从 data.visited 推断
  const moveOptions: VoiceOption[] = $derived(
    ($game?.last_voice_options ?? []).filter((v: VoiceOption) => v.is_move)
  );

  // 邻居地点 = data.current_location 的邻居（从 detail 接口拿）
  // 简化：从 data.visited + heard 推断可去的
  const allReachable: LocationInfo[] = $derived.by(() => {
    const d = data;
    if (!d) return [];
    const cur = d.current_location.id;
    return [...d.visited, ...d.heard].filter(l => l.id !== cur);
  });

  // 🆕 v2.7.1: 当前位置对应场景图（盛泽镇/苏州府/北京城）
  // 三张图由 minimax image-01 重新生成（白底透明化）
  const sceneImage = $derived.by(() => {
    if (!data) return null;
    const id = data.current_location.id;
    const sceneMap: Record<string, string> = {
      shengze: '/scenes/shengze.webp',
      suzhou: '/scenes/suzhou.webp',
      beijing: '/scenes/beijing.webp',
    };
    return sceneMap[id] ?? null;
  });
</script>

{#if data}
  <section class="location-panel" aria-label="当前位置">
    <!-- 1. 当前位置标识 -->
    <div class="location-current">
      <span class="location-pin" aria-hidden="true">📍</span>
      <span class="location-label">你在</span>
      <span class="location-name" title={data.current_location.description}>
        {data.current_location.name}
      </span>
      <span class="location-tier">L{data.current_location.tier.replace('L', '')}</span>
    </div>

    <!-- 🆕 v2.7.1 任务 3: 场景图（白底透明化的水墨画）-->
    {#if sceneImage}
      <div class="location-scene">
        <img
          src={sceneImage}
          alt={data.current_location.name}
          class="location-scene-img"
          loading="lazy"
          width="600"
          height="356"
        />
      </div>
    {/if}

    <!-- 🆕 v2.4.1: 该地 NPC -->
    {#if data.current_location.npcs_default && data.current_location.npcs_default.length > 0}
      <div class="location-npcs">
        <span class="location-npcs-label">在场：</span>
        {#each data.current_location.npcs_default as npc (npc)}
          <span class="location-npc-chip">{npc}</span>
        {/each}
      </div>
    {/if}

    <!-- 2. 移动选项（横向胶囊） -->
    {#if allReachable.length > 0}
      <div class="location-moves">
        <span class="location-moves-label">可去：</span>
        <div class="location-moves-rail">
          {#each allReachable as loc (loc.id)}
            {@const visited = data.visited.some(v => v.id === loc.id)}
            {@const heard = data.heard.some(h => h.id === loc.id)}
            <LocationMovePill
              location={loc}
              visited={visited}
              heard={heard}
              disabled={moving}
              onmove={handleMove}
            />
          {/each}
        </div>
      </div>
    {/if}

    <!-- 3. 听过没去过（折叠） -->
    {#if data.heard.length > 0}
      <button
        type="button"
        class="location-heard-toggle"
        onclick={() => (showHeard = !showHeard)}
      >
        <span class="location-heard-toggle-icon" aria-hidden="true">
          {showHeard ? '▾' : '▸'}
        </span>
        <span>听过但没去过（{data.heard.length}）</span>
      </button>
      {#if showHeard}
        <div class="location-heard-list">
          {#each data.heard as loc (loc.id)}
            <LocationMovePill
              location={loc}
              visited={false}
              heard={true}
              apCost="1.5 AP"
              disabled={moving}
              onmove={handleMove}
            />
          {/each}
        </div>
      {/if}
    {/if}
  </section>
{/if}

<style>
  .location-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-sm);
  }

  /* 当前位置标识 */
  .location-current {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-display);
    font-size: var(--text-sm);
  }

  /* 🆕 v2.7.1 任务 3: 场景图（白底透明化，叠加在 paper 背景上）*/
  .location-scene {
    margin: 6px 0 8px;
    border-radius: 6px;
    overflow: hidden;
    background: var(--color-paper, #faf6ed);
    line-height: 0;
  }

  .location-scene-img {
    display: block;
    width: 100%;
    height: auto;
    max-height: 180px;
    object-fit: cover;
    object-position: center;
    /* 关键：让透明背景显示底层 paper（"如墨在宣纸"效果）*/
    mix-blend-mode: multiply;
    opacity: 0.92;
    /* 微妙的水墨淡雅 */
    filter: saturate(0.85) contrast(1.05);
  }

  .location-pin {
    font-size: var(--text-md);
    flex: 0 0 auto;
  }

  .location-label {
    color: var(--color-ink-light);
    flex: 0 0 auto;
  }

  .location-name {
    color: var(--color-ink);
    font-weight: 600;
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .location-tier {
    flex: 0 0 auto;
    font-family: var(--font-numeric);
    font-size: 10px;
    color: var(--color-bronze);
    background: var(--color-paper-aged);
    padding: 1px 6px;
    border-radius: 8px;
  }

  /* 🆕 v2.4.1 NPC 显示 */
  .location-npcs {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
    padding: 2px 0;
  }

  .location-npcs-label {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    flex: 0 0 auto;
  }

  .location-npc-chip {
    font-size: var(--text-xs);
    font-family: var(--font-body);
    color: var(--color-bronze-dark);
    background: rgba(184, 134, 11, 0.1);
    padding: 1px 6px;
    border-radius: 8px;
    border: 1px solid rgba(184, 134, 11, 0.3);
  }

  /* 移动选项条 */
  .location-moves {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .location-moves-label {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    flex: 0 0 auto;
  }

  .location-moves-rail {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    gap: 4px;
    overflow-x: auto;
    overflow-y: visible;
    padding: 2px 0;
  }

  .location-moves-rail::-webkit-scrollbar {
    height: 3px;
  }
  .location-moves-rail::-webkit-scrollbar-thumb {
    background: var(--color-bronze);
    border-radius: 2px;
  }

  .location-move-pill {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: 14px;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .location-move-pill:hover:not(:disabled) {
    background: var(--color-bronze);
    border-color: var(--color-bronze-dark);
    color: var(--color-paper);
    transform: translateY(-1px);
  }

  .location-move-pill:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* 听过没去过的胶囊用青色（陌生感）*/
  .location-move-pill-heard {
    border-color: var(--color-cinnabar);
    background: rgba(165, 40, 40, 0.05);
  }

  .location-move-pill-heard:hover:not(:disabled) {
    background: var(--color-cinnabar);
  }

  .location-move-icon {
    font-size: var(--text-sm);
  }

  .location-move-name {
    white-space: nowrap;
  }

  /* 听过折叠区 */
  .location-heard-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 0;
    background: transparent;
    border: none;
    color: var(--color-ink-faint);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    cursor: pointer;
    text-align: left;
  }

  .location-heard-toggle:hover {
    color: var(--color-ink);
  }

  .location-heard-toggle-icon {
    flex: 0 0 auto;
  }

  .location-heard-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: var(--space-1) 0;
  }

  .location-heard-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: transparent;
    border: 1px dashed var(--color-ink-faint);
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    cursor: pointer;
    text-align: left;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .location-heard-item:hover:not(:disabled) {
    background: var(--color-paper-aged);
    border-style: solid;
    border-color: var(--color-cinnabar);
  }

  .location-heard-icon {
    flex: 0 0 auto;
  }

  .location-heard-name {
    flex: 1 1 auto;
  }

  .location-heard-ap {
    flex: 0 0 auto;
    font-family: var(--font-numeric);
    font-size: 10px;
    color: var(--color-cinnabar);
  }
</style>
