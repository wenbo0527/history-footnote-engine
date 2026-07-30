<script lang="ts">
  /**
   * 🆕 v2.10.x — WorldMap 演示页面
   *
   * 完整集成：
   * - GameState 联动 (current_city)
   * - 5 城状态 (current/visited/heard/locked)
   * - 城市点击 → 详情弹窗
   * - 前往此城 → travel action
   */

  import WorldMap from '$lib/components/game/WorldMap.svelte';
  import type { GameState } from '$lib/api/types';

  // Mock GameState（演示用）
  let state = $state<GameState>({
    session_id: 'demo',
    account_username: '盛澤織工',
    character: {
      name: '盛澤織工',
      age: 28,
      health: 80,
      stamina: 75,
    } as any,
    family: [] as any,
    skills: [] as any,
    city: 'shengze',
    year_current: 1587,
    year_max: 1600,
    round_current: 1,
    cash: 100,
    rice: 50,
    looms: 2,
  } as any);

  let visitedCities = $state<string[]>([]);
  let heardCities = $state<string[]>(['suzhou', 'hangzhou', 'songjiang', 'nanjing']);
  let selectedCity = $state<string | null>(null);

  function handleCityClick(cityId: string) {
    selectedCity = cityId;
    if (cityId !== state.city) {
      // 模拟探索
      if (!visitedCities.includes(cityId)) {
        visitedCities = [...visitedCities, cityId];
      }
    }
  }

  function handleTravel(cityId: string) {
    if (cityId === state.city) return;
    // 模拟 travel
    state = { ...state, city: cityId };
    if (!visitedCities.includes(cityId)) {
      visitedCities = [...visitedCities, cityId];
    }
    selectedCity = null;
  }
</script>

<svelte:head>
  <title>江南輿圖 · 萬曆十五年</title>
</svelte:head>

<div class="demo-page">
  <header class="demo-header">
    <h1>🗺️ 江南輿圖 · 萬曆十五年（1587）</h1>
    <p class="subtitle">Svelte 组件集成演示 — 跟 GameState 实时联动</p>
    <div class="state-info">
      <span>當前位置: <strong>{state.city}</strong></span>
      <span>已造訪: {visitedCities.length} 城</span>
      <span>僅聞名: {heardCities.length} 城</span>
    </div>
  </header>

  <div class="map-wrapper">
    <WorldMap
      {state}
      {visitedCities}
      {heardCities}
      onCityClick={handleCityClick}
    />
  </div>

  <footer class="demo-footer">
    <details>
      <summary>📚 設計說明</summary>
      <ul>
        <li><strong>5 城</strong>: 盛澤（玩家起點）/ 蘇州 / 杭州 / 松江 / 南京</li>
        <li><strong>AI 底圖</strong>: MiniMax mmx image 生成 v4 (1536×864)</li>
        <li><strong>狀態</strong>: 朱砂印章（current）/ 藍實心（visited）/ 棕空心（heard）/ 灰半透明（locked）</li>
        <li><strong>動效</strong>: 當前位置 2s 脉冲环 / 運河 2s 流動波紋</li>
        <li><strong>彈窗</strong>: 30 城內地點 + 9 NPC + 8 史實事件</li>
      </ul>
    </details>
  </footer>
</div>

<style>
  .demo-page {
    min-height: 100vh;
    background: linear-gradient(180deg, #2c2418 0%, #1a1612 100%);
    color: #e8d8b0;
    font-family: 'STKaiti', 'KaiTi', serif;
    padding: 20px;
  }

  .demo-header {
    text-align: center;
    margin-bottom: 20px;
  }

  .demo-header h1 {
    font-size: 28px;
    margin: 0 0 8px;
    color: #fff8e1;
    letter-spacing: 4px;
  }

  .subtitle {
    font-size: 14px;
    color: rgba(232, 216, 176, 0.7);
    margin: 0 0 16px;
  }

  .state-info {
    display: flex;
    justify-content: center;
    gap: 24px;
    font-size: 13px;
  }

  .state-info strong {
    color: var(--cinnabar, #c44536);
  }

  .map-wrapper {
    max-width: 1200px;
    margin: 0 auto;
    aspect-ratio: 1200 / 800;
    background: #e8d8b0;
    border: 3px solid #5a4a36;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }

  .demo-footer {
    max-width: 720px;
    margin: 24px auto 0;
    font-size: 12px;
  }

  .demo-footer summary {
    cursor: pointer;
    color: var(--cinnabar, #c44536);
    padding: 4px 0;
  }

  .demo-footer ul {
    margin: 12px 0 0;
    padding-left: 20px;
    line-height: 1.8;
  }

  .demo-footer li strong {
    color: #fff8e1;
  }
</style>
