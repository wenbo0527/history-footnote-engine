<script lang="ts">
  /**
   * 🆕 v2.10.x — WorldMap — 江南地理舆图（AI 水墨底图 + SVG 叠加）
   *
   * 集成：跟 GameState (current_city, current_location) 实时联动
   *
   * 视觉：
   * - 底层：AI 生成的 v4 水墨底图（mmx-output/jian-ye-A-v4.jpg）
   * - 顶层：SVG 城市节点 + 运河路径 + 玩家路径
   *
   * 5 城（v4 底图位置）：
   * - 南京 (150, 95) — 应天府
   * - 苏州 (235, 160) — 江南丝织中心
   * - 杭州 (200, 320) — 南宋旧都
   * - 盛泽 (500, 440) — 玩家当前 (current)
   * - 松江 (720, 380) — 棉纺织业
   *
   * 状态：
   * - current: 朱红印章
   * - visited: 蓝色实心
   * - heard: 灰色空心
   * - locked: 灰色半透明
   */

  import type { GameState } from '$lib/api/types';
  import CityMarker, { type CityData } from './CityMarker.svelte';
  import CityDetailPanel from './CityDetailPanel.svelte';
  import CanalPath from './CanalPath.svelte';
  import TravelLine from './TravelLine.svelte';

  interface TravelSegment {
    from: string;
    to: string;
    days: number;
    round?: number;
  }

  interface Props {
    state: GameState;
    visitedCities?: string[];
    heardCities?: string[];
    travelPath?: TravelSegment[];
    onCityClick?: (cityId: string) => void;
    onTravel?: (cityId: string) => void;
  }

  let {
    state,
    visitedCities = [],
    heardCities = [],
    travelPath = [],
    onCityClick = (id) => console.log('[WorldMap] city click:', id),
    onTravel = (id) => console.log('[WorldMap] travel to:', id)
  }: Props = $props();

  // 5 城配置（v4 底图对齐）
  const CITIES = [
    {
      id: 'nanjing', name: '南京應天府', tier: 'fu',
      x: 150, y: 95, days: 6.0,
      desc: '留都，天下財賦出於江南，而金陵為其會',
      meta: '南都 · 留都',
    },
    {
      id: 'suzhou', name: '蘇州府', tier: 'fu',
      x: 235, y: 160, days: 1.0,
      desc: '閶門碼頭人聲鼎沸，民間機戶工匠超過三萬人',
      meta: '江南絲織業絕對中心',
    },
    {
      id: 'hangzhou', name: '杭州府', tier: 'fu',
      x: 200, y: 320, days: 2.5,
      desc: '南宋舊都，絲綢生產的源頭城',
      meta: '南宋舊都 · 京杭運河南端',
    },
    {
      id: 'shengze', name: '盛澤鎮', tier: 'xian',
      x: 500, y: 440, days: 0,
      desc: '蘇州府吳江縣東南，江南絲織業核心小鎮',
      meta: '蘇州府吳江縣',
    },
    {
      id: 'songjiang', name: '松江府', tier: 'fu',
      x: 720, y: 380, days: 2.0,
      desc: '全國棉紡織業中心，衣被天下',
      meta: '棉紡織業第一府',
    },
  ];

  // 运河路径（v4 底图对齐）
  const CANAL_PATH = 'M 150 95 Q 190 130, 235 160 Q 350 280, 500 440 Q 610 410, 720 380';

  function getCityStatus(cityId: string): 'current' | 'visited' | 'heard' | 'locked' {
    if (cityId === state.city) return 'current';
    if (visitedCities.includes(cityId)) return 'visited';
    if (heardCities.includes(cityId)) return 'heard';
    return 'locked';
  }

  let selectedCityId = $state<string | null>(null);
  let showDetail = $state(false);

  function handleCityClick(cityId: string) {
    selectedCityId = cityId;
    showDetail = true;
    onCityClick(cityId);
  }

  function closeDetail() {
    showDetail = false;
    selectedCityId = null;
  }
</script>

<div class="world-map-container">
  <!-- AI 水墨底图（v4） -->
  <img
    class="map-base"
    src="/static/mmx-output/jian-ye-A-v4.jpg"
    alt="江南輿圖"
    draggable="false"
  />

  <!-- SVG 叠加层 -->
  <svg
    class="map-svg"
    viewBox="0 0 1200 800"
    preserveAspectRatio="xMidYMid meet"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- 京杭大运河（青色 + 水流动效）-->
    <CanalPath path={CANAL_PATH} />

    <!-- 玩家路径（朱砂笔触）— Phase 8.4 -->
    {#each travelPath as segment, i (i)}
      <TravelLine {segment} cities={CITIES} />
    {/each}

    <!-- 5 城节点 -->
    {#each CITIES as city (city.id)}
      <CityMarker
        {city}
        status={getCityStatus(city.id)}
        onclick={() => handleCityClick(city.id)}
      />
    {/each}
  </svg>

  <!-- HUD 顶部 -->
  <div class="map-hud">
    <div class="hud-title">江南輿圖</div>
    <div class="hud-sub">明萬曆十五年（1587） · 蘇州府吳江縣</div>
  </div>

  <!-- 图例 -->
  <div class="map-legend">
    <div class="legend-item">
      <span class="legend-dot current"></span>
      <span>當前所在地</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot visited"></span>
      <span>已造訪</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot heard"></span>
      <span>僅聞名</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot locked"></span>
      <span>未探索</span>
    </div>
  </div>

  <!-- 城市详情弹窗 -->
  {#if showDetail && selectedCityId}
    <CityDetailPanel
      cityId={selectedCityId}
      city={CITIES.find(c => c.id === selectedCityId)}
      onClose={closeDetail}
      onTravel={(id) => {
        onTravel(id);
        closeDetail();
      }}
    />
  {/if}
</div>

<style>
  .world-map-container {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--paper, #e8d8b0);
  }

  .map-base {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: 0;
    opacity: 0.78;
    mix-blend-mode: multiply;
    pointer-events: none;
    user-select: none;
  }

  .map-svg {
    position: relative;
    z-index: 1;
    width: 100%;
    height: 100%;
    display: block;
  }

  .map-hud {
    position: absolute;
    top: 16px;
    left: 16px;
    z-index: 2;
    padding: 12px 20px;
    background: rgba(26, 22, 18, 0.85);
    color: var(--paper, #e8d8b0);
    border-left: 3px solid var(--cinnabar, #c44536);
    font-family: 'STKaiti', 'KaiTi', serif;
  }

  .hud-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 4px;
  }

  .hud-sub {
    font-size: 12px;
    color: rgba(232, 216, 176, 0.7);
    margin-top: 2px;
  }

  .map-legend {
    position: absolute;
    bottom: 16px;
    left: 16px;
    z-index: 2;
    padding: 8px 16px;
    background: rgba(232, 216, 176, 0.9);
    border: 1px solid #5a4a36;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 12px;
    display: flex;
    gap: 16px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
  }

  .legend-dot.current {
    background: var(--cinnabar, #c44536);
  }

  .legend-dot.visited {
    background: #2c5e6f;
  }

  .legend-dot.heard {
    background: transparent;
    border: 1.5px solid #5a4a36;
  }

  .legend-dot.locked {
    background: rgba(90, 74, 54, 0.3);
  }
</style>
