<script lang="ts">
  /**
   * 🆕 v2.10.x — MiniMap — 缩略地图（始终可见，玩家知道自己位置）
   *
   * 视觉：
   * - 250×140 缩略图（AI 底图 v4）
   * - 玩家位置: 朱砂红点 + 脉冲
   * - 已访问城市: 蓝色实心点
   * - 仅闻名: 棕色空心点
   * - 未探索: 灰色半透明点
   *
   * 交互：
   * - 点击 → 触发 onOpenFullMap 事件
   * - hover 城点 → tooltip
   */

  import type { GameState } from '$lib/api/types';

  interface Props {
    gameState: GameState;
    visitedCities?: string[];
    heardCities?: string[];
    onOpenFullMap?: () => void;
  }

  let { gameState, visitedCities = [], heardCities = [], onOpenFullMap }: Props = $props();

  // 5 城坐标（跟 WorldMap 一致）
  const CITIES = [
    { id: 'nanjing',   name: '南京', x: 12.5, y: 11.9 },  // 150/1200=12.5, 95/800=11.9
    { id: 'suzhou',    name: '蘇州', x: 19.6, y: 20.0 },  // 235/1200=19.6, 160/800=20.0
    { id: 'hangzhou',  name: '杭州', x: 12.9, y: 31.3 },  // 155/1200=12.9, 250/800=31.3
    { id: 'shengze',   name: '盛澤', x: 41.7, y: 55.0 },  // 500/1200=41.7, 440/800=55.0
    { id: 'songjiang', name: '松江', x: 60.0, y: 47.5 },  // 720/1200=60.0, 380/800=47.5
  ];

  function getStatus(cityId: string): 'current' | 'visited' | 'heard' | 'locked' {
    if (cityId === gameState.city) return 'current';
    if (visitedCities.includes(cityId)) return 'visited';
    if (heardCities.includes(cityId)) return 'heard';
    return 'locked';
  }

  function handleClick() {
    onOpenFullMap?.();
  }
</script>

<button
  class="mini-map"
  onclick={handleClick}
  title="點擊查看完整江南輿圖"
  aria-label="江南輿圖縮略圖，點擊查看完整地圖"
>
  <img class="mini-map-base" src="/mmx-output/jian-ye-A-v4.jpg" alt="" />

  <!-- 5 城点 -->
  <svg class="mini-map-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
    {#each CITIES as city (city.id)}
      {@const status = getStatus(city.id)}
      <g class="mini-city status-{status}">
        {#if status === 'current'}
          <circle cx={city.x} cy={city.y} r="1.5" class="city-current-pulse" />
          <circle cx={city.x} cy={city.y} r="0.8" class="city-current" />
        {:else if status === 'visited'}
          <circle cx={city.x} cy={city.y} r="0.7" class="city-visited" />
        {:else if status === 'heard'}
          <circle cx={city.x} cy={city.y} r="0.6" class="city-heard" />
        {:else}
          <circle cx={city.x} cy={city.y} r="0.5" class="city-locked" />
        {/if}
      </g>
    {/each}
  </svg>

  <!-- 角落提示 -->
  <div class="mini-map-corner">🗺️</div>
</button>

<style>
  .mini-map {
    position: relative;
    display: block;
    width: 250px;
    height: 140px;
    padding: 0;
    margin: 0;
    border: 1.5px solid #5a4a36;
    border-radius: 4px;
    overflow: hidden;
    background: #1a1612;
    cursor: pointer;
    transition: border-color 0.2s;
  }

  .mini-map:hover {
    border-color: var(--cinnabar, #c44536);
  }

  .mini-map-base {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.6;
    pointer-events: none;
    user-select: none;
  }

  .mini-map-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  /* 5 城状态点 */
  .city-current {
    fill: var(--cinnabar, #c44536);
    stroke: #fff8e1;
    stroke-width: 0.15;
  }

  .city-current-pulse {
    fill: none;
    stroke: var(--cinnabar, #c44536);
    stroke-width: 0.2;
    animation: mini-pulse 2s ease-out infinite;
    transform-origin: center;
  }

  @keyframes mini-pulse {
    0% { r: 0.8; opacity: 0.9; }
    100% { r: 2.5; opacity: 0; }
  }

  .city-visited {
    fill: #2c5e6f;
    stroke: #fff8e1;
    stroke-width: 0.1;
  }

  .city-heard {
    fill: var(--paper, #e8d8b0);
    stroke: #5a4a36;
    stroke-width: 0.15;
  }

  .city-locked {
    fill: rgba(90, 74, 54, 0.3);
    stroke: rgba(90, 74, 54, 0.5);
    stroke-width: 0.1;
  }

  /* 角落 🗺️ */
  .mini-map-corner {
    position: absolute;
    top: 4px;
    right: 6px;
    font-size: 14px;
    opacity: 0.8;
    pointer-events: none;
  }
</style>