<script lang="ts">
  /**
   * 🆕 v2.10.x — CityMarker — 城市节点（朱砂印章 / 蓝色实心 / 灰色空心）
   *
   * 状态颜色：
   * - current: 朱砂印章 + 红色文本 + 旋转 -3°
   * - visited: 蓝色实心圆 + 白色文本
   * - heard: 灰色空心圆 + 棕色文本
   * - locked: 灰色半透明
   */

  interface CityData {
    id: string;
    name: string;
    tier: 'fu' | 'xian';
    x: number;
    y: number;
    days: number;
    desc: string;
    meta: string;
  }

  // 导出供其他组件使用
  export type { CityData };

  interface Props {
    city: CityData;
    status: 'current' | 'visited' | 'heard' | 'locked';
    onclick?: () => void;
  }

  let { city, status, onclick }: Props = $props();

  let showTooltip = $state(false);
  let showDays = $state(true);

  const tierLabel = $derived(city.tier === 'fu' ? '府城' : '縣城');
</script>

<g
  class="city-marker status-{status} tier-{city.tier}"
  transform="translate({city.x}, {city.y})"
  role="button"
  tabindex="0"
  on:click={onclick}
  on:keydown={(e) => e.key === 'Enter' && onclick?.()}
  on:mouseenter={() => (showTooltip = true)}
  on:mouseleave={() => (showTooltip = false)}
>
  <!-- 当前：朱砂印章 -->
  {#if status === 'current'}
    <g class="seal" transform="rotate(-3)">
      <rect class="seal-bg" x="-12" y="-12" width="24" height="24" />
      <text class="seal-text" x="0" y="5" text-anchor="middle">此</text>
    </g>
    <!-- 当前脉冲环 -->
    <circle class="pulse-ring" cx="0" cy="0" r="20" fill="none" />
  {:else if status === 'visited'}
    <!-- 已访问：蓝色实心圆 + 白色字 -->
    <circle class="city-circle" cx="0" cy="0" r="12" />
    <text class="city-text-light" x="0" y="4" text-anchor="middle">{city.name[0]}</text>
  {:else if status === 'heard'}
    <!-- 仅闻名：棕色空心圆 -->
    <circle class="city-circle" cx="0" cy="0" r="10" />
    <text class="city-text" x="0" y="4" text-anchor="middle">{city.name[0]}</text>
  {:else}
    <!-- 未探索：灰色半透明 -->
    <circle class="city-circle-locked" cx="0" cy="0" r="8" />
    <text class="city-text-locked" x="0" y="3" text-anchor="middle">?</text>
  {/if}

  <!-- 城名标签 -->
  <text
    class="city-label"
    x="0"
    y={status === 'current' ? 30 : 24}
    text-anchor="middle"
  >
    {city.name}
  </text>

  <!-- 天数标签 -->
  {#if showDays && status !== 'current' && city.days > 0}
    <text
      class="city-days"
      x="0"
      y={status === 'current' ? 46 : 40}
      text-anchor="middle"
    >
      距盛澤 {city.days} 天
    </text>
  {/if}

  <!-- 悬浮提示 -->
  {#if showTooltip}
    <g class="tooltip" transform="translate(20, -40)">
      <rect class="tooltip-bg" x="0" y="0" width="180" height="48" rx="2" />
      <text class="tooltip-title" x="8" y="16">{city.name}</text>
      <text class="tooltip-meta" x="8" y="32">{tierLabel} · {city.meta}</text>
      <text class="tooltip-action" x="8" y="44">→ 點擊查看詳情</text>
    </g>
  {/if}
</g>

<style>
  .city-marker {
    cursor: pointer;
    transition: transform 0.2s;
  }

  .city-marker:hover {
    transform: translate(var(--tx, 0), var(--ty, 0)) scale(1.15);
  }

  .city-marker:focus {
    outline: 2px solid var(--cinnabar, #c44536);
    outline-offset: 4px;
  }

  /* 当前：朱砂印章 */
  .seal-bg {
    fill: var(--cinnabar, #c44536);
    stroke: #8b1a1a;
    stroke-width: 1;
  }
  .seal-text {
    fill: #fff8e1;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 18px;
    font-weight: 700;
  }

  /* 脉冲环 */
  .pulse-ring {
    stroke: var(--cinnabar, #c44536);
    stroke-width: 1.5;
    animation: pulse 2s ease-out infinite;
  }
  @keyframes pulse {
    0% { r: 14; opacity: 0.8; }
    100% { r: 28; opacity: 0; }
  }

  /* 已访问：蓝色实心 */
  .city-circle {
    fill: #2c5e6f;
    stroke: #1a3a4a;
    stroke-width: 1;
  }

  /* 仅闻名：棕色空心 */
  .city-marker.status-heard .city-circle {
    fill: var(--paper, #e8d8b0);
    stroke: #5a4a36;
    stroke-width: 1.5;
  }

  /* 未探索 */
  .city-circle-locked {
    fill: rgba(90, 74, 54, 0.3);
    stroke: rgba(90, 74, 54, 0.5);
    stroke-width: 1;
    stroke-dasharray: 2 2;
  }

  /* 文字 */
  .city-text {
    fill: #5a4a36;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 11px;
    font-weight: 600;
  }
  .city-text-light {
    fill: #fff8e1;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 11px;
    font-weight: 600;
  }
  .city-text-locked {
    fill: rgba(90, 74, 54, 0.6);
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 10px;
  }

  /* 城名 */
  .city-label {
    fill: #1a1612;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    paint-order: stroke;
    stroke: rgba(232, 216, 176, 0.9);
    stroke-width: 3;
    stroke-linejoin: round;
  }

  .status-current .city-label {
    fill: var(--cinnabar, #c44536);
  }

  /* 天数 */
  .city-days {
    fill: #5a4a36;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 9px;
    font-style: italic;
    paint-order: stroke;
    stroke: rgba(232, 216, 176, 0.9);
    stroke-width: 2;
  }

  /* 悬浮提示 */
  .tooltip-bg {
    fill: rgba(26, 22, 18, 0.92);
    stroke: var(--cinnabar, #c44536);
    stroke-width: 1;
  }
  .tooltip-title {
    fill: #fff8e1;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
  }
  .tooltip-meta {
    fill: rgba(232, 216, 176, 0.8);
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 9px;
  }
  .tooltip-action {
    fill: var(--cinnabar, #c44536);
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 9px;
    font-weight: 600;
  }
</style>
