<script lang="ts">
  /**
   * FateHandPanel - 命运卡手牌（v2.5）
   *
   * 显示当前手牌，每张可点击触发
   * 触发后：
   *   - 显示效果消息
   *   - 标记为 used
   */
  import { game, gameActions } from '$lib/stores';
  import { fateHand, fateUse } from '$lib/api/fate';
  import { toast } from '$lib/components/design-system/Toast.svelte';
  import type { FateCard } from '$lib/api/types';

  interface Props {
    /** 命运卡手牌（由父组件传入） */
    hand: FateCard[];
  }

  let { hand }: Props = $props();

  let using = $state<string | null>(null);
  let expanded = $state(true);

  async function handleUse(cardId: string) {
    if (using || !$game) return;
    if (hand.find(c => c.id === cardId)?.used) return;
    using = cardId;
    try {
      const res = await fateUse($game.session_id, cardId);
      if (res.messages && res.messages.length > 0) {
        toast.success(res.messages.join('，'));
      }
      // 更新 game state（cash/debt/rice/ap/reputation/hand）
      if (res.state) {
        gameActions.set({
          ...$game,
          ...res.state
        } as any);
      }
      // 重新拉取手牌
      const newHand = await fateHand($game.session_id);
      hand = newHand.hand;
    } catch (e) {
      const err = e as Error & { data?: any };
      toast.error(err.data?.error || err.message || '触发失败');
    } finally {
      using = null;
    }
  }

  const unused = $derived(hand.filter(c => !c.used));
</script>

{#if hand && hand.length > 0}
  <section class="fate-panel">
    <button
      type="button"
      class="fate-toggle"
      onclick={() => (expanded = !expanded)}
    >
      <span class="fate-toggle-icon" aria-hidden="true">
        {expanded ? '▾' : '▸'}
      </span>
      <span class="fate-toggle-text">命运卡（{unused.length}/{hand.length} 未用）</span>
    </button>

    {#if expanded}
      <div class="fate-rail">
        {#each hand as card (card.id)}
          <button
            type="button"
            class="fate-card"
            class:fate-card-used={card.used}
            disabled={card.used || using === card.id}
            onclick={() => handleUse(card.id)}
            style="--card-color: {card.color}"
            title={card.used ? '已使用' : card.description}
          >
            <span class="fate-card-icon" aria-hidden="true">{card.icon}</span>
            <span class="fate-card-name">{card.name}</span>
            <span class="fate-card-desc">{card.description}</span>
            {#if card.used}
              <span class="fate-card-mark">已用</span>
            {/if}
          </button>
        {/each}
      </div>
    {/if}
  </section>
{/if}

<style>
  .fate-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-sm);
  }

  .fate-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 0;
    background: transparent;
    border: none;
    color: var(--color-ink-light);
    font-family: var(--font-display);
    font-size: var(--text-xs);
    cursor: pointer;
    text-align: left;
  }

  .fate-toggle-text {
    flex: 1 1 auto;
  }

  .fate-rail {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    overflow-y: visible;
    padding: 2px 0;
  }

  .fate-rail::-webkit-scrollbar {
    height: 3px;
  }
  .fate-rail::-webkit-scrollbar-thumb {
    background: var(--color-bronze);
    border-radius: 2px;
  }

  .fate-card {
    flex: 0 0 140px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 8px;
    background: var(--color-paper);
    border: 2px solid var(--card-color, var(--color-bronze));
    border-radius: var(--radius-sm);
    cursor: pointer;
    text-align: center;
    transition: all var(--duration-normal) var(--ease-ink);
    position: relative;
  }

  .fate-card:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(58, 42, 26, 0.15);
  }

  .fate-card:disabled {
    cursor: not-allowed;
  }

  .fate-card-used {
    opacity: 0.4;
    background: var(--color-paper-aged);
    filter: grayscale(60%);
  }

  .fate-card-icon {
    font-size: var(--text-xl);
    line-height: 1;
  }

  .fate-card-name {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-ink);
  }

  .fate-card-desc {
    font-family: var(--font-body);
    font-size: 10px;
    color: var(--color-ink-light);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .fate-card-mark {
    position: absolute;
    top: 4px;
    right: 4px;
    font-size: 9px;
    color: var(--color-ink-faint);
    background: var(--color-paper-aged);
    padding: 1px 4px;
    border-radius: 4px;
  }
</style>
