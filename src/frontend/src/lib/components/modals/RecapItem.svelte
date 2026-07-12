<script lang="ts">
  /**
   * RecapItem - 单回合叙事回顾卡片（RecapModal 子组件）
   *
   * 拆出理由：原 RecapModal.svelte 678 行
   * - recap-item 模板在 3 处复用（章节 / 近期 / 存档）
   * - 拆出后 3 处都引用同一个 RecapItem
   * - 主 modal 减少 ~80 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分（与 CharacterCard.svelte 同一波）
   */
  import { Icon } from '$lib/components/design-system';
  import type { RecapNarrativeItem } from '$lib/api/types';

  interface Props {
    item: RecapNarrativeItem;
  }

  let { item }: Props = $props();

  // 玩家选择 / 行动显示分支
  const showChoice = $derived(Boolean(item.player_input || item.chosen_voice));
  const showOriginal = $derived(
    Boolean(item.player_input && item.chosen_voice && item.player_input !== item.chosen_voice)
  );
</script>

<article class="recap-item">
  <header class="recap-item-header">
    <span class="recap-round">第 {item.round} 回合</span>
    {#if item.summary}
      <span class="recap-summary">{item.summary}</span>
    {/if}
  </header>
  {#if showChoice}
    <div class="recap-choice">
      <Icon name="gear" size={14} class="recap-choice-icon" />
      <span class="recap-choice-text">
        {#if item.chosen_voice}
          你的选择：<strong>{item.chosen_voice}</strong>
          {#if showOriginal}
            （原话：<em>「{item.player_input}」</em>）
          {/if}
        {:else}
          你的行动：<em>「{item.player_input}」</em>
        {/if}
      </span>
    </div>
  {/if}
  <p class="recap-narrative">{item.narrative}</p>
</article>

<style>
  .recap-item {
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .recap-item:hover {
    background: var(--color-paper-aged);
    border-left-color: var(--color-cinnabar);
  }
  .recap-item-header {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
    flex-wrap: wrap;
  }
  .recap-round {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
    font-weight: 600;
    padding: 2px 8px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
    flex: 0 0 auto;
  }
  .recap-summary {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink);
    font-weight: 500;
  }
  .recap-choice {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    margin-bottom: var(--space-2);
    padding: var(--space-1) var(--space-2);
    background: rgba(184, 134, 11, 0.06);
    border-left: 2px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
  }
  .recap-choice-icon {
    color: var(--color-bronze-dark);
    flex: 0 0 auto;
  }
  .recap-choice-text {
    color: var(--color-ink-light);
    font-family: var(--font-body);
  }
  .recap-choice-text strong {
    color: var(--color-bronze-dark);
    font-weight: 600;
  }
  .recap-choice-text em {
    color: var(--color-ink);
    font-style: italic;
  }
  .recap-narrative {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    line-height: 1.7;
    margin: 0;
    text-indent: 2em;
  }
</style>