<script lang="ts">
  /**
   * PlateCell - 单个板块卡片（PlateMap 子组件）
   *
   * 拆出理由：原 PlateMap.svelte 625 行
   * - grid mode 中每个板块卡 ~42 行（行 258-299）
   * - 含状态色点 + 张力条 + 详情展开
   * - 拆出后 PlateMap 减重 ~45 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { PlateDefinition } from '$lib/api/chapter';

  interface Props {
    plate: PlateDefinition;
    status: string;
    tension: number;
    expanded: boolean;
    statusColor: (s: string) => string;
    statusLabel: (s: string) => string;
    typeLabel: (t: string) => string;
    tensionWidth: (t: number) => string;
    ontoggle: (id: string) => void;
  }

  let {
    plate,
    status,
    tension,
    expanded,
    statusColor,
    statusLabel,
    typeLabel,
    tensionWidth,
    ontoggle,
  }: Props = $props();

  const isShifting = $derived(status === 'shifting');
  const isCollapsed = $derived(status === 'collapsed');
  const tensionPct = $derived(`${(tension * 100).toFixed(0)}%`);
</script>

<article
  class="plate-cell"
  class:plate-cell-shifting={isShifting}
  class:plate-cell-collapsed={isCollapsed}
  onclick={() => ontoggle(plate.id)}
  onkeydown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      ontoggle(plate.id);
    }
  }}
  role="button"
  tabindex="0"
  aria-label={`${plate.name} 板块，${statusLabel(status)}`}
>
  <header class="plate-cell-header">
    <span class="plate-cell-name">{plate.name}</span>
    <span class="plate-cell-type" data-type={plate.type}>{typeLabel(plate.type)}</span>
  </header>
  <div class="plate-cell-status" style="--status-color: {statusColor(status)};">
    <span class="plate-cell-dot" aria-hidden="true"></span>
    <span class="plate-cell-status-label">{statusLabel(status)}</span>
  </div>
  <div class="plate-cell-tension" aria-label={`张力 ${tensionPct}`}>
    <div class="plate-cell-tension-bar" style="width: {tensionWidth(tension)}"></div>
  </div>
  <div class="plate-cell-tension-label">张力 {tensionPct}</div>

  {#if expanded}
    <div class="plate-cell-detail">
      <p class="plate-cell-desc">{plate.description}</p>
      {#if plate.neighbors.length > 0}
        <div class="plate-cell-neighbors">
          <span class="plate-cell-neighbors-label">邻接:</span>
          {#each plate.neighbors as nid (nid)}
            <span class="plate-cell-neighbor-chip">{nid}</span>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</article>

<style>
  .plate-cell {
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--status-color, var(--color-ink-faint));
    border-radius: var(--radius-sm);
    transition: all var(--duration-normal) var(--ease-ink);
    cursor: pointer;
  }
  .plate-cell:hover {
    background: var(--color-paper-aged);
    transform: translateX(2px);
    box-shadow: var(--shadow-1);
  }
  .plate-cell-shifting {
    background: linear-gradient(180deg, var(--color-paper) 0%, rgba(220, 100, 50, 0.05) 100%);
    border-color: rgba(220, 100, 50, 0.3);
  }
  .plate-cell-collapsed {
    background: rgba(180, 50, 50, 0.05);
    border-color: rgba(180, 50, 50, 0.4);
    opacity: 0.75;
  }
  .plate-cell-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-1);
  }
  .plate-cell-name {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink);
    font-weight: 600;
  }
  .plate-cell-type {
    font-size: var(--text-xs);
    padding: 1px 6px;
    border-radius: var(--radius-sm);
    background: var(--color-paper-aged);
    color: var(--color-ink-light);
  }
  .plate-cell-type[data-type="political"] {
    background: rgba(165, 40, 40, 0.1);
    color: var(--color-cinnabar);
  }
  .plate-cell-type[data-type="economic"] {
    background: rgba(184, 134, 11, 0.1);
    color: var(--color-bronze-dark);
  }
  .plate-cell-type[data-type="social"] {
    background: rgba(80, 140, 80, 0.1);
    color: rgb(80, 140, 80);
  }
  .plate-cell-status {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: var(--space-1);
    font-size: var(--text-xs);
  }
  .plate-cell-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--status-color, var(--color-ink-faint));
  }
  .plate-cell-status-label {
    color: var(--color-ink-light);
  }
  .plate-cell-tension {
    width: 100%;
    height: 4px;
    background: var(--color-ink-faint);
    border-radius: 2px;
    overflow: hidden;
  }
  .plate-cell-tension-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--color-bronze) 0%, var(--color-cinnabar) 100%);
    transition: width var(--duration-slow) var(--ease-ink);
  }
  .plate-cell-tension-label {
    font-size: 10px;
    color: var(--color-ink-faint);
    text-align: right;
    margin-top: 2px;
  }
  .plate-cell-detail {
    margin-top: var(--space-2);
    padding-top: var(--space-2);
    border-top: 1px dashed var(--color-ink-faint);
  }
  .plate-cell-desc {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    line-height: 1.5;
    margin: 0 0 var(--space-1);
  }
  .plate-cell-neighbors {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
  }
  .plate-cell-neighbors-label {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }
  .plate-cell-neighbor-chip {
    font-size: 10px;
    padding: 1px 4px;
    background: var(--color-paper-aged);
    border-radius: 2px;
    color: var(--color-ink-light);
  }
</style>