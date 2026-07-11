<script lang="ts">
  /**
   * 🆕 v2.8.x W28 + v2.9.x W42: PlateMap — 板块格局矩阵图 + SVG 节点图
   *
   * W42 新增：
   * - SVG 节点图（圆周布局 + 连线）
   * - 视图切换 tab（grid ↔ graph）
   * - 状态颜色根据 tension + status 动态
   *
   * 视觉效果（grid 模式）：
   *   ┌────────┐ ──走廊──┌────────┐
   *   │  中原  │         │  江南  │
   *   │ core   │         │ core   │
   *   │ ▮▮▯▯  │         │ ▮▮▮▮  │
   *   │ tension│         │        │
   *   └────────┘         └────────┘
   *
   * 视觉效果（SVG 节点图模式）：
   *         中原
   *       /     \
   *   江南 ── 河西
   *       \     /
   *         西北
   *
   * 4 状态颜色：
   * - stable: 绿色 (rgb(80, 140, 80))
   * - tense: 黄色 (rgb(200, 150, 50))
   * - shifting: 橙色 (rgb(220, 100, 50))  ← 闪烁动画
   * - collapsed: 红色 (rgb(180, 50, 50))
   *
   * 张力条：横向 bar（tension 0-1）
   * 走廊：板块之间用线段表示
   */
  import { onMount } from 'svelte';
  import { getPlateMap, type PlateMapResponse, type PlateDefinition } from '$lib/api/chapter';
  import { circularLayout, buildEdges, findNode, nodeRadius } from './graphLayout';

  interface Props {
    sessionId: string;
  }

  let { sessionId }: Props = $props();

  let plateMap = $state<PlateMapResponse | null>(null);
  let error = $state<string | null>(null);
  let showDetail = $state<string | null>(null); // 当前查看的板块 id
  let viewMode = $state<'grid' | 'graph'>('grid'); // 🆕 W42: 视图模式

  async function refresh() {
    if (!sessionId) return;
    try {
      error = null;
      plateMap = await getPlateMap(sessionId);
    } catch (e) {
      error = (e as Error).message;
      plateMap = {
        active: true,
        plate_count: 0,
        definitions: [],
        corridors: [],
        tensions: {},
        statuses: {},
        active_plate: '',
      };
    }
  }

  onMount(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  });

  // 状态颜色映射
  function statusColor(status: string): string {
    const map: Record<string, string> = {
      stable: 'rgb(80, 140, 80)',
      tense: 'rgb(200, 150, 50)',
      shifting: 'rgb(220, 100, 50)',
      collapsed: 'rgb(180, 50, 50)',
    };
    return map[status] ?? 'rgb(150, 150, 150)';
  }

  // 类型缩写
  function typeLabel(type: string): string {
    const map: Record<string, string> = {
      core: '核心',
      peripheral: '边缘',
      corridor: '走廊',
    };
    return map[type] ?? type;
  }

  // 状态中文
  function statusLabel(status: string): string {
    const map: Record<string, string> = {
      stable: '稳定',
      tense: '紧张',
      shifting: '变化',
      collapsed: '崩溃',
    };
    return map[status] ?? status;
  }

  // tension 进度条宽度
  function tensionWidth(tension: number): string {
    return `${Math.max(0, Math.min(1, tension)) * 100}%`;
  }

  // 🆕 W42: SVG 节点图派生数据
  let svgLayout = $derived.by(() => {
    if (!plateMap || plateMap.definitions.length === 0) return null;
    const ids = plateMap.definitions.map((p) => p.id);
    return circularLayout(ids, { width: 400, height: 360, padding: 50 });
  });

  let svgEdges = $derived.by(() => {
    if (!plateMap || !svgLayout) return [];
    const neighbors: Record<string, string[]> = {};
    for (const p of plateMap.definitions) {
      neighbors[p.id] = p.neighbors || [];
    }
    return buildEdges(svgLayout, neighbors);
  });

  let svgNodeR = $derived(nodeRadius(plateMap?.plate_count || 0));
</script>

{#if plateMap}
  <section class="plate-map" aria-label="板块格局">
    <header class="plate-map-header">
      <span class="plate-map-icon" aria-hidden="true">🗺️</span>
      <h3 class="plate-map-title">板块格局</h3>
      <span class="plate-map-count">{plateMap.plate_count} 块</span>
      {#if plateMap.active_plate}
        <span class="plate-map-active">激变中: {plateMap.active_plate}</span>
      {/if}
      <!-- 🆕 W42: 视图模式切换 -->
      <div class="plate-map-tabs" role="tablist" aria-label="视图模式">
        <button
          type="button"
          class="plate-map-tab"
          class:plate-map-tab-active={viewMode === 'grid'}
          role="tab"
          aria-selected={viewMode === 'grid'}
          onclick={() => (viewMode = 'grid')}
        >
          网格
        </button>
        <button
          type="button"
          class="plate-map-tab"
          class:plate-map-tab-active={viewMode === 'graph'}
          role="tab"
          aria-selected={viewMode === 'graph'}
          onclick={() => (viewMode = 'graph')}
        >
          节点图
        </button>
      </div>
    </header>

    <!-- 🆕 W42: SVG 节点图模式 -->
    {#if viewMode === 'graph' && svgLayout}
      <div class="plate-map-svg-wrap">
        <svg
          class="plate-map-svg"
          viewBox="0 0 {svgLayout.width} {svgLayout.height}"
          role="img"
          aria-label="板块格局节点图"
        >
          <!-- 连线 -->
          {#each svgEdges as e (`edge-${e.from}-${e.to}`)}
            <line
              class="plate-map-edge"
              x1={e.fromX}
              y1={e.fromY}
              x2={e.toX}
              y2={e.toY}
              stroke="rgba(143, 75, 40, 0.4)"
              stroke-width="1.5"
            />
          {/each}

          <!-- 节点 -->
          {#each plateMap.definitions as plate (`node-${plate.id}`)}
            {@const node = findNode(svgLayout, plate.id)}
            {@const status = plateMap.statuses[plate.id] ?? 'stable'}
            {@const isActive = plateMap.active_plate === plate.id}
            {@const isShifting = status === 'shifting'}
            {#if node}
              <g
                class="plate-map-node"
                class:plate-map-node-active={isActive}
                class:plate-map-node-shifting={isShifting}
                onclick={() => (showDetail = showDetail === plate.id ? null : plate.id)}
                onkeydown={(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    showDetail = showDetail === plate.id ? null : plate.id;
                  }
                }}
                role="button"
                tabindex="0"
                aria-label={`${plate.name} 板块，${statusLabel(status)}`}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={svgNodeR}
                  fill={statusColor(status)}
                  fill-opacity={isActive ? 0.95 : 0.75}
                  stroke={isActive ? 'var(--color-crimson)' : 'rgba(255,255,255,0.6)'}
                  stroke-width={isActive ? 3 : 1.5}
                />
                <text
                  x={node.x}
                  y={node.y}
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="11"
                  font-weight="600"
                  style="pointer-events: none;"
                >
                  {plate.name}
                </text>
              </g>
            {/if}
          {/each}
        </svg>
        {#if showDetail}
          {@const detail = plateMap.definitions.find((p) => p.id === showDetail)}
          {#if detail}
            <div class="plate-map-svg-detail">
              <strong>{detail.name}</strong> · {typeLabel(detail.type)} ·
              {statusLabel(plateMap.statuses[detail.id] ?? 'stable')}
              <p>{detail.description}</p>
              <button
                type="button"
                class="plate-map-svg-close"
                onclick={() => (showDetail = null)}
              >
                关闭
              </button>
            </div>
          {/if}
        {/if}
      </div>
    {:else}
    <div class="plate-map-grid">
      {#each plateMap.definitions as plate (`plate-${plate.id}`)}
        {@const status = plateMap.statuses[plate.id] ?? 'stable'}
        {@const tension = plateMap.tensions[plate.id] ?? 0}
        {@const isShifting = status === 'shifting'}
        {@const isCollapsed = status === 'collapsed'}
        <article
          class="plate-cell"
          class:plate-cell-shifting={isShifting}
          class:plate-cell-collapsed={isCollapsed}
          onclick={() => (showDetail = showDetail === plate.id ? null : plate.id)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              showDetail = showDetail === plate.id ? null : plate.id;
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
          <div class="plate-cell-tension" aria-label={`张力 ${(tension * 100).toFixed(0)}%`}>
            <div class="plate-cell-tension-bar" style="width: {tensionWidth(tension)}"></div>
          </div>
          <div class="plate-cell-tension-label">张力 {(tension * 100).toFixed(0)}%</div>

          {#if showDetail === plate.id}
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
      {/each}
    </div>
    {/if}

    {#if plateMap.corridors.length > 0}
      <div class="plate-map-corridors">
        <h4>走廊（板块间通道）</h4>
        <ul class="plate-map-corridor-list">
          {#each plateMap.corridors as c (`corridor-${c.id}`)}
            <li class="plate-map-corridor-item">
              <span class="plate-map-corridor-from">{c.from_plate}</span>
              <span class="plate-map-corridor-arrow" aria-hidden="true">──→</span>
              <span class="plate-map-corridor-to">{c.to_plate}</span>
              <span class="plate-map-corridor-desc">{c.description}</span>
            </li>
          {/each}
        </ul>
      </div>
    {/if}

    {#if error}
      <div class="plate-map-error">⚠️ 板块数据加载失败: {error}</div>
    {/if}
  </section>
{/if}

<style>
  .plate-map {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    background: linear-gradient(135deg, rgba(143, 75, 40, 0.04) 0%, rgba(70, 130, 100, 0.04) 100%);
    border: 1px solid rgba(143, 75, 40, 0.2);
    border-radius: var(--radius-md);
  }

  .plate-map-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .plate-map-icon { font-size: var(--text-md); }
  .plate-map-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink);
    font-weight: 600;
  }
  .plate-map-count {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
    padding: 1px 8px;
    background: rgba(218, 165, 32, 0.1);
    border-radius: var(--radius-full);
  }
  .plate-map-active {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-crimson-dark);
    padding: 1px 8px;
    background: rgba(180, 50, 50, 0.1);
    border-radius: var(--radius-sm);
    animation: plate-pulse 1.5s ease-in-out infinite;
  }

  @keyframes plate-pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.5; }
  }

  .plate-map-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: var(--space-2);
  }

  .plate-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: var(--space-2);
    background: rgba(255, 255, 255, 0.5);
    border: 1px solid rgba(143, 75, 40, 0.2);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .plate-cell:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .plate-cell-shifting {
    border-color: rgb(220, 100, 50);
    animation: plate-cell-glow 2s ease-in-out infinite;
  }

  .plate-cell-collapsed {
    background: rgba(180, 50, 50, 0.05);
    border-color: rgb(180, 50, 50);
  }

  @keyframes plate-cell-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(220, 100, 50, 0.3); }
    50%      { box-shadow: 0 0 0 4px rgba(220, 100, 50, 0.05); }
  }

  .plate-cell-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-1);
  }

  .plate-cell-name {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-ink);
  }

  .plate-cell-type {
    font-family: var(--font-body);
    font-size: 10px;
    padding: 1px 4px;
    border-radius: var(--radius-sm);
  }
  .plate-cell-type[data-type='core'] { background: rgba(143, 75, 40, 0.15); color: var(--color-bronze-dark); }
  .plate-cell-type[data-type='peripheral'] { background: rgba(70, 130, 100, 0.15); color: var(--color-jade-dark); }
  .plate-cell-type[data-type='corridor'] { background: rgba(218, 165, 32, 0.15); color: var(--color-bronze-dark); }

  .plate-cell-status {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: var(--text-xs);
    color: var(--color-ink);
  }
  .plate-cell-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--status-color, var(--color-bronze));
  }

  .plate-cell-tension {
    position: relative;
    height: 4px;
    background: rgba(143, 75, 40, 0.1);
    border-radius: 2px;
    overflow: hidden;
  }
  .plate-cell-tension-bar {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: linear-gradient(90deg, var(--color-jade) 0%, var(--color-bronze) 70%, var(--color-crimson) 100%);
    transition: width 0.3s;
  }
  .plate-cell-tension-label {
    font-family: var(--font-numeric);
    font-size: 10px;
    color: var(--color-bronze-dark);
    text-align: right;
  }

  .plate-cell-detail {
    margin-top: var(--space-1);
    padding-top: var(--space-1);
    border-top: 1px dashed rgba(143, 75, 40, 0.2);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }
  .plate-cell-desc { margin: 0 0 4px; line-height: 1.4; }
  .plate-cell-neighbors {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }
  .plate-cell-neighbors-label { color: var(--color-bronze-dark); }
  .plate-cell-neighbor-chip {
    display: inline-block;
    padding: 1px 5px;
    background: rgba(143, 75, 40, 0.1);
    color: var(--color-ink);
    border-radius: var(--radius-sm);
    font-family: var(--font-numeric);
  }

  .plate-map-corridors {
    margin-top: var(--space-2);
    padding-top: var(--space-2);
    border-top: 1px solid rgba(143, 75, 40, 0.15);
  }
  .plate-map-corridors h4 {
    margin: 0 0 4px;
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
  }
  .plate-map-corridor-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .plate-map-corridor-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: var(--text-xs);
    color: var(--color-ink);
  }
  .plate-map-corridor-from,
  .plate-map-corridor-to {
    font-family: var(--font-numeric);
    font-weight: 600;
  }
  .plate-map-corridor-arrow { color: var(--color-bronze); }
  .plate-map-corridor-desc {
    color: var(--color-ink-light);
    font-style: italic;
  }

  .plate-map-error {
    font-size: var(--text-xs);
    color: var(--color-crimson-dark);
    font-style: italic;
  }

  /* 🆕 W42: 视图切换 tab */
  .plate-map-tabs {
    display: inline-flex;
    margin-left: auto;
    background: rgba(143, 75, 40, 0.08);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .plate-map-tab {
    padding: 2px 10px;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    background: transparent;
    border: 0;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
  }
  .plate-map-tab:hover {
    background: rgba(143, 75, 40, 0.08);
  }
  .plate-map-tab-active {
    background: var(--color-bronze);
    color: white;
    font-weight: 600;
  }

  /* 🆕 W42: SVG 节点图样式 */
  .plate-map-svg-wrap {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .plate-map-svg {
    width: 100%;
    max-width: 500px;
    height: auto;
    background: radial-gradient(circle, rgba(255, 245, 220, 0.4) 0%, transparent 70%);
    border: 1px solid rgba(143, 75, 40, 0.15);
    border-radius: var(--radius-sm);
  }
  .plate-map-edge {
    transition: stroke 0.3s, stroke-width 0.3s;
  }
  .plate-map-node {
    cursor: pointer;
    transition: transform 0.2s;
  }
  .plate-map-node:hover circle {
    stroke: var(--color-bronze-dark);
    stroke-width: 2.5;
  }
  .plate-map-node-shifting circle {
    animation: plate-node-pulse 1.5s ease-in-out infinite;
  }
  @keyframes plate-node-pulse {
    0%, 100% { stroke-opacity: 0.6; }
    50%      { stroke-opacity: 1.0; }
  }
  .plate-map-svg-detail {
    padding: var(--space-2);
    background: rgba(255, 245, 220, 0.5);
    border: 1px solid rgba(143, 75, 40, 0.25);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    color: var(--color-ink);
  }
  .plate-map-svg-detail p {
    margin: 4px 0;
    line-height: 1.4;
  }
  .plate-map-svg-close {
    margin-top: 4px;
    padding: 1px 8px;
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
    background: transparent;
    border: 1px solid rgba(143, 75, 40, 0.3);
    border-radius: var(--radius-sm);
    cursor: pointer;
  }
  .plate-map-svg-close:hover {
    background: rgba(143, 75, 40, 0.1);
  }
</style>
