<script lang="ts">
  /**
   * EmergencyModal - 应急弹出（v2.6）
   *
   * 关键时刻系统检测到危机（如 cash<1、debt>=2）时弹出
   * 显示可用的 emergency 卡，玩家可选择：
   *   - 点击卡 → 立即使用
   *   - 5 秒不点 → 自动关闭
   *
   * 不强制——给玩家一个"明牌"
   */
  import { onMount, onDestroy } from 'svelte';
  import { fateUse } from '$lib/api/fate';
  import { toast } from '$lib/components/design-system/Toast.svelte';
  import type { FateCard } from '$lib/api/types';

  interface Props {
    show: boolean;
    /** session id（用于触发卡） */
    sessionId: string;
    /** 应急原因（中文） */
    reason: string;
    /** 触发器 id（cash_critical 等） */
    trigger?: string;
    /** 可用的 emergency 卡 */
    cards: FateCard[];
    /** 关闭回调 */
    onclose: (usedCardId?: string) => void;
    /** 自动关闭超时（秒），0=不自动关 */
    timeout?: number;
  }

  let { show, sessionId, reason, trigger = '', cards, onclose, timeout = 8 }: Props = $props();

  let using = $state<string | null>(null);
  let remaining = $state(timeout);
  let timer: ReturnType<typeof setInterval> | null = null;

  $effect(() => {
    if (show && timeout > 0) {
      remaining = timeout;
      if (timer) clearInterval(timer);
      timer = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
          close();
        }
      }, 1000);
    } else if (!show && timer) {
      clearInterval(timer);
      timer = null;
    }
  });

  onDestroy(() => {
    if (timer) clearInterval(timer);
  });

  function close() {
    onclose();
  }

  async function handleUse(cardId: string) {
    if (using) return;
    using = cardId;
    try {
      const res = await fateUse(sessionId, cardId, 'emergency');
      if (res.messages && res.messages.length > 0) {
        toast.success(res.messages.join('，'));
      }
      onclose(cardId);
    } catch (e) {
      const err = e as Error & { data?: any };
      toast.error(err.data?.reason || err.data?.error || err.message || '使用失败');
    } finally {
      using = null;
    }
  }
</script>

{#if show}
  <div
    class="emergency-overlay"
    role="dialog"
    aria-modal="true"
    aria-labelledby="emergency-title"
  >
    <div class="emergency-modal">
      <header class="emergency-header">
        <span class="emergency-icon" aria-hidden="true">⚠️</span>
        <h2 id="emergency-title" class="emergency-title">紧急时刻</h2>
        {#if timeout > 0}
          <span class="emergency-timer" aria-live="polite">
            {remaining}s
          </span>
        {/if}
      </header>

      <div class="emergency-reason">
        <p class="emergency-reason-text">{reason}</p>
        {#if trigger}
          <span class="emergency-trigger">触发器: {trigger}</span>
        {/if}
      </div>

      <div class="emergency-body">
        {#if cards.length === 0}
          <p class="emergency-empty">你没有可用的应急卡</p>
        {:else}
          <p class="emergency-hint">💡 你有 {cards.length} 张应急卡可现在使用</p>
          <div class="emergency-cards">
            {#each cards as card (card.id)}
              <button
                type="button"
                class="emergency-card"
                disabled={using === card.id}
                onclick={() => handleUse(card.id)}
                style="--card-color: {card.color}"
              >
                <span class="emergency-card-icon" aria-hidden="true">{card.icon}</span>
                <span class="emergency-card-name">{card.name}</span>
                <span class="emergency-card-desc">{card.description}</span>
                {#if card.use_hint}
                  <span class="emergency-card-hint">{card.use_hint}</span>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <footer class="emergency-footer">
        <button
          type="button"
          class="emergency-skip"
          onclick={close}
        >继续（不用卡）</button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .emergency-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    animation: fade-in 0.2s ease-out;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .emergency-modal {
    background: var(--color-paper);
    border: 2px solid var(--color-cinnabar);
    border-radius: var(--radius-md);
    box-shadow: 0 8px 32px rgba(58, 42, 26, 0.3);
    max-width: 480px;
    width: calc(100% - 32px);
    max-height: 80vh;
    overflow-y: auto;
    animation: scale-in 0.2s ease-out;
  }

  @keyframes scale-in {
    from { transform: scale(0.9); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .emergency-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    background: linear-gradient(180deg, rgba(165, 40, 40, 0.1) 0%, var(--color-paper) 100%);
    border-bottom: 1px solid var(--color-cinnabar);
  }

  .emergency-icon {
    font-size: 24px;
  }

  .emergency-title {
    flex: 1 1 auto;
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-cinnabar);
  }

  .emergency-timer {
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-cinnabar);
    background: rgba(165, 40, 40, 0.1);
    padding: 2px 8px;
    border-radius: 12px;
  }

  .emergency-reason {
    padding: var(--space-3) var(--space-4);
    background: var(--color-paper-aged);
    border-bottom: 1px solid var(--color-bronze);
  }

  .emergency-reason-text {
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink);
    margin: 0 0 4px;
  }

  .emergency-trigger {
    font-family: var(--font-numeric);
    font-size: 10px;
    color: var(--color-ink-faint);
  }

  .emergency-body {
    padding: var(--space-3) var(--space-4);
  }

  .emergency-hint {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0 0 var(--space-2);
    text-align: center;
  }

  .emergency-empty {
    text-align: center;
    color: var(--color-ink-faint);
    font-style: italic;
    padding: var(--space-3) 0;
  }

  .emergency-cards {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .emergency-card {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 2px solid var(--card-color, var(--color-bronze));
    border-radius: var(--radius-sm);
    cursor: pointer;
    text-align: left;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .emergency-card:hover:not(:disabled) {
    background: var(--color-paper-aged);
    transform: translateX(4px);
    box-shadow: 0 2px 8px rgba(58, 42, 26, 0.15);
  }

  .emergency-card:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .emergency-card-icon {
    flex: 0 0 auto;
    font-size: 28px;
    line-height: 1;
  }

  .emergency-card-name {
    flex: 0 0 auto;
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 600;
    color: var(--color-ink);
    min-width: 80px;
  }

  .emergency-card-desc {
    flex: 1 1 auto;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    line-height: 1.4;
  }

  .emergency-card-hint {
    flex: 0 0 auto;
    font-family: var(--font-body);
    font-size: 10px;
    color: var(--color-bronze-dark);
    font-style: italic;
    max-width: 120px;
    line-height: 1.3;
  }

  .emergency-footer {
    display: flex;
    justify-content: center;
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--color-bronze);
  }

  .emergency-skip {
    background: transparent;
    border: 1px solid var(--color-ink-faint);
    color: var(--color-ink-light);
    padding: 6px 20px;
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .emergency-skip:hover {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
    color: var(--color-ink);
  }
</style>
