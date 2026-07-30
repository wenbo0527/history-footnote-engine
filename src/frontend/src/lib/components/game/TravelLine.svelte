<script lang="ts">
  /**
   * 🆕 v2.10.x — TravelLine — 玩家路径可视化（朱砂笔触自绘）
   *
   * 视觉：
   * - 朱砂色（cinnabar）实线（主路径）
   * - 黄色双线（船行驶方向）
   * - 虚线波纹（已走过的路）
   * - 圆点（每段起讫点）
   * - 天数标签（中间位置）
   *
   * 数据：
   *   TravelLine props: { from, to, days, round }
   *   from/to 是 CityData
   *   路径用 Q (quadratic Bezier) 平滑
   */

  import type { CityData } from './CityMarker.svelte';

  interface TravelSegment {
    from: string;
    to: string;
    days: number;
    round?: number;
  }

  interface Props {
    segment: TravelSegment;
    cities: CityData[];
  }

  let { segment, cities }: Props = $props();

  // 查找起讫城
  const fromCity = $derived(cities.find(c => c.id === segment.from));
  const toCity = $derived(cities.find(c => c.id === segment.to));

  // 路径（quadratic Bezier，中点偏移）
  const path = $derived.by(() => {
    if (!fromCity || !toCity) return '';
    const mx = (fromCity.x + toCity.x) / 2;
    const my = (fromCity.y + toCity.y) / 2;
    // 偏移：中点垂直于起讫方向 10-30 像素
    const dx = toCity.x - fromCity.x;
    const dy = toCity.y - fromCity.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const offsetX = -dy / len * 15;
    const offsetY = dx / len * 15;
    return `M ${fromCity.x} ${fromCity.y} Q ${mx + offsetX} ${my + offsetY} ${toCity.x} ${toCity.y}`;
  });

  // 中点位置（用于显示标签）
  const midPos = $derived.by(() => {
    if (!fromCity || !toCity) return { x: 0, y: 0 };
    const mx = (fromCity.x + toCity.x) / 2;
    const my = (fromCity.y + toCity.y) / 2;
    const dx = toCity.x - fromCity.x;
    const dy = toCity.y - fromCity.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const offsetX = -dy / len * 15;
    const offsetY = dx / len * 15;
    return { x: mx + offsetX, y: my + offsetY };
  });
</script>

{#if fromCity && toCity}
  <g class="travel-line">
    <!-- 底层：朱砂笔触（已走过） -->
    <path
      class="trail-main"
      d={path}
      fill="none"
      stroke="#c44536"
      stroke-width="2.5"
      stroke-linecap="round"
      opacity="0.75"
    />

    <!-- 中层：黄色双线（船迹） -->
    <path
      class="trail-inner"
      d={path}
      fill="none"
      stroke="#d4a548"
      stroke-width="0.8"
      stroke-linecap="round"
      stroke-dasharray="2 4"
      opacity="0.6"
    />

    <!-- 顶层：朱砂笔触动画（流动效果） -->
    <path
      class="trail-flow"
      d={path}
      fill="none"
      stroke="#fff8e1"
      stroke-width="1.2"
      stroke-linecap="round"
      stroke-dasharray="3 6"
      opacity="0.7"
    />

    <!-- 起讫圆点 -->
    <circle cx={fromCity.x} cy={fromCity.y} r="3" fill="#c44536" stroke="#8b1a1a" stroke-width="0.5"/>
    <circle cx={toCity.x} cy={toCity.y} r="3" fill="#c44536" stroke="#8b1a1a" stroke-width="0.5"/>

    <!-- 中点标签 -->
    <g transform="translate({midPos.x}, {midPos.y})">
      <rect class="trail-label-bg" x="-20" y="-10" width="40" height="16" rx="2"/>
      <text class="trail-label" x="0" y="3" text-anchor="middle">{segment.days} 天</text>
    </g>
  </g>
{/if}

<style>
  .trail-main {
    filter: drop-shadow(0 0 1px rgba(196, 69, 54, 0.5));
  }

  .trail-flow {
    animation: trail-flow 1.5s linear infinite;
  }

  @keyframes trail-flow {
    0% {
      stroke-dashoffset: 0;
    }
    100% {
      stroke-dashoffset: -18;
    }
  }

  .trail-label-bg {
    fill: rgba(232, 216, 176, 0.92);
    stroke: #c44536;
    stroke-width: 0.8;
  }

  .trail-label {
    fill: #1a1612;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 9px;
    font-weight: 600;
  }
</style>
