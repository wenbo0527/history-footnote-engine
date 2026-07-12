<script lang="ts">
  /**
   * LocationMovePill - 移动胶囊（LocationPanel 子组件）
   *
   * 拆出理由：原 LocationPanel.svelte 429 行
   * - 移动胶囊 2 处复用（移动选项 / 听过列表）
   * - 拆出后 LocationPanel 减重 ~30 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { LocationInfo } from '$lib/api/types';

  interface Props {
    location: LocationInfo;
    visited: boolean;
    heard: boolean;
    apCost?: string;     // 听过列表显示 AP 成本
    disabled: boolean;
    onmove: (id: string) => void;
  }

  let { location, visited, heard, apCost, disabled, onmove }: Props = $props();
</script>

<button
  type="button"
  class="location-move-pill"
  class:location-move-pill-heard={heard && !visited}
  onclick={() => onmove(location.id)}
  disabled={disabled}
  title={location.description}
>
  <span class="location-move-icon" aria-hidden="true">
    {visited ? '↗' : heard ? '❓' : '→'}
  </span>
  <span class="location-move-name">{location.name}</span>
  {#if apCost}
    <span class="location-heard-ap">{apCost}</span>
  {/if}
</button>

<style>
  .location-move-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: 100px;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    white-space: nowrap;
  }
  .location-move-pill:hover:not(:disabled) {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
    transform: translateY(-1px);
  }
  .location-move-pill:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .location-move-pill-heard {
    background: var(--color-paper-aged);
    border-style: dashed;
    color: var(--color-ink-light);
  }
  .location-move-icon {
    font-size: 12px;
  }
  .location-move-name {
    font-weight: 500;
  }
  .location-heard-ap {
    font-family: var(--font-numeric);
    font-size: 10px;
    color: var(--color-ink-faint);
  }
</style>