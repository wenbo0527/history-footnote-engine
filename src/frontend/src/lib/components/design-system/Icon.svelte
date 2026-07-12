<!--
  🆕 v2.10.1 W82: Icon 组件（统一 SVG icon）

  用法：
    <Icon name="search" size={20} />
    <Icon name="warning" size={24} />

  优点：
  - 避免 emoji（文字感重）
  - 中国风一致（朱砂/古铜/宣纸色系）
  - 矢量（任意尺寸）
  - 单文件 < 1KB
-->
<script lang="ts">
  /**
   * Icon 组件 - 统一管理 SVG / WebP icon
   */
  type IconName =
    | 'search' | 'sparkle' | 'warning' | 'hint' | 'coin'
    | 'scroll' | 'chat' | 'calendar' | 'walk' | 'gear' | 'cards'
    | 'archive' | 'choice' | 'home' | 'recap' | 'settings' | 'share' | 'wiki'
    | 'action' | 'cash' | 'health' | 'loom' | 'reputation';

  interface Props {
    name: IconName;
    size?: number;
    class?: string;
  }

  let { name, size = 20, class: className = '' }: Props = $props();

  // 🆕 W82: 分类管理 icon 路径
  // - ui/* 新建 SVG（11 个）
  // - nav/* / stats/* 已有 WebP（12 个）
  const SVG_NAMES = new Set(['search', 'sparkle', 'warning', 'hint', 'coin', 'scroll', 'chat', 'calendar', 'walk', 'gear', 'cards']);
  const NAV_NAMES = new Set(['archive', 'choice', 'home', 'recap', 'settings', 'share', 'wiki']);
  const STATS_NAMES = new Set(['action', 'cash', 'health', 'loom', 'reputation']);

  const isSvg = $derived(SVG_NAMES.has(name));
  const isNav = $derived(NAV_NAMES.has(name));
  const isStats = $derived(STATS_NAMES.has(name));

  const src = $derived(
    isSvg ? `/icons/ui/${name}.svg`
    : isNav ? `/icons/nav/${name}.webp`
    : isStats ? `/icons/stats/${name}.webp`
    : ''
  );
</script>

{#if src}
  <img
    {src}
    alt={name}
    class="icon {className}"
    style="width: {size}px; height: {size}px;"
    onerror={(e) => { (e.currentTarget as HTMLImageElement).style.opacity = '0.3'; }}
  />
{/if}

<style>
  .icon {
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
    object-fit: contain;
  }
</style>
