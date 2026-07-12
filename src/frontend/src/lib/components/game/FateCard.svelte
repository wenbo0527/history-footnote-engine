<script lang="ts">
  /**
   * FateCard - 单个命运卡（FateHandPanel 子组件）
   *
   * 拆出理由：原 FateHandPanel.svelte 519 行
   * - 单卡模板 35 行 + 大量 .fate-card-* 样式 ~200 行
   * - 拆出后 FateHandPanel 减重 ~50 行 template + 200 行样式
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { FateCard as FateCardType } from '$lib/api/types';

  interface Props {
    card: FateCardType;
    canUse: boolean;
    reason: string;
    highlighted: boolean;
    using: boolean;
    highlightedUse: boolean;
    onuse: (id: string) => void;
    setref: (el: HTMLElement) => void;
  }

  let {
    card,
    canUse,
    reason,
    highlighted,
    using,
    highlightedUse,
    onuse,
    setref,
  }: Props = $props();

  // 检测 icon 是 emoji 还是文件路径
  const isEmoji = $derived(!/^[a-z_]+$/.test(card.icon));
</script>

<button
  type="button"
  class="fate-card"
  class:fate-card-used={card.used}
  class:fate-card-disabled={!canUse && !card.used}
  class:fate-card-available={canUse}
  class:fate-card-emergency={card.use_type === 'emergency'}
  class:fate-card-round={card.use_type === 'round_start'}
  class:fate-card-highlighted={highlighted}
  class:fate-card-using={highlightedUse}
  disabled={!canUse || using}
  onclick={() => onuse(card.id)}
  use:setref
  data-card-id={card.id}
  style="--card-color: {card.color}"
  title={card.used ? '已使用' : (canUse ? card.description : reason)}
>
  <span class="fate-card-icon" aria-hidden="true">
    {#if isEmoji}
      {card.icon}
    {:else}
      <img src={`/fate/${card.icon}.webp`} alt="" class="fate-card-icon-img" />
    {/if}
  </span>
  <span class="fate-card-name">{card.name}</span>
  <span class="fate-card-desc">{card.description}</span>
  {#if card.use_hint}
    <span class="fate-card-hint">{card.use_hint}</span>
  {/if}
  {#if card.used}
    <span class="fate-card-mark">已用</span>
  {:else if !canUse && reason}
    <span class="fate-card-lock">🔒 {reason}</span>
  {/if}
</button>

<style>
  .fate-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    padding: var(--space-2);
    background: var(--color-paper);
    border: 1px solid var(--card-color, var(--color-ink-faint));
    border-left: 3px solid var(--card-color, var(--color-ink-faint));
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink);
    transition: all var(--duration-normal) var(--ease-ink);
    min-width: 120px;
    max-width: 200px;
    text-align: left;
  }
  .fate-card:hover:not(:disabled) {
    background: var(--color-paper-aged);
    transform: translateY(-1px);
    box-shadow: var(--shadow-1);
  }
  .fate-card:disabled {
    cursor: not-allowed;
  }
  .fate-card-used {
    opacity: 0.4;
  }
  .fate-card-disabled {
    opacity: 0.6;
    background: var(--color-ink-faint);
    border-color: var(--color-ink-faint);
  }
  .fate-card-available {
    background: var(--color-paper);
  }
  .fate-card-emergency {
    border-left-width: 4px;
  }
  .fate-card-round {
    border-left-style: dashed;
  }
  .fate-card-highlighted {
    box-shadow: 0 0 0 3px var(--color-cinnabar);
    animation: fate-pulse 1.5s ease-in-out infinite;
  }
  .fate-card-using {
    background: var(--color-cinnabar);
    color: white;
  }
  @keyframes fate-pulse {
    0%, 100% { box-shadow: 0 0 0 3px var(--color-cinnabar); }
    50% { box-shadow: 0 0 0 6px rgba(165, 40, 40, 0.3); }
  }
  .fate-card-icon {
    font-size: 18px;
    line-height: 1;
  }
  .fate-card-icon-img {
    width: 24px;
    height: 24px;
    object-fit: contain;
  }
  .fate-card-name {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-ink);
  }
  .fate-card-desc {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .fate-card-hint {
    font-size: 10px;
    color: var(--color-ink-faint);
    font-style: italic;
  }
  .fate-card-mark {
    position: absolute;
    top: 4px;
    right: 4px;
    padding: 1px 4px;
    background: var(--color-ink-faint);
    color: white;
    font-size: 10px;
    border-radius: 2px;
  }
  .fate-card-lock {
    font-size: 10px;
    color: var(--color-ink-faint);
    margin-top: 2px;
  }
</style>