<!--
  🆕 v2.10.1 W80: 命运卡详情弹窗

  点击 CharCard 命运卡 chip → 弹此窗
  - 展示大图（emoji + 主题色背景）
  - 完整描述 + 效果
  - "使用" / "收起" 按钮
-->
<script lang="ts">
  import ModalShell from './ModalShell.svelte';
  import { Button, Spinner } from '$lib/components/design-system';
  import { useFateCard } from '$lib/api/fate';
  import { game, gameActions } from '$lib/stores';
  import { toast } from '$lib/components/design-system';
  import type { FateCard } from '$lib/api/types';

  interface Props {
    open: boolean;
    card: FateCard | null;
    onclose: () => void;
  }

  let { open, card, onclose }: Props = $props();

  let submitting = $state(false);

  // 关闭后清空 card
  $effect(() => {
    if (!open) {
      setTimeout(() => submitting = false, 200);
    }
  });

  async function handleUse() {
    if (!card || !$game) return;
    submitting = true;
    try {
      const res = await useFateCard($game.session_id, card.id);
      // 刷新 state（含新 cash/variables）
      if ((res as any).updated_state) {
        gameActions.set((res as any).updated_state);
      }
      toast.success(`已使用：${card.name}`);
      onclose();
    } catch (e) {
      const err = e as Error;
      toast.error(err.message || '使用失败');
      submitting = false;
    }
  }

  // 🆕 use_type 中文标签
  const USE_TYPE_LABEL: Record<string, string> = {
    immediate: '即时',
    round_start: '回合开始',
    emergency: '紧急',
    any: '任何时机',
  };
</script>

<ModalShell {open} {onclose} title="命 运 卡" size="md">
  {#if card}
    <div class="fate-detail">
      <!-- 大图区 -->
      <div class="fate-detail-header" style="background: linear-gradient(135deg, {card.color}cc, {card.color}88);">
        <div class="fate-detail-icon">{card.icon}</div>
        <h2 class="fate-detail-name">{card.name}</h2>
        {#if card.use_type}
          <span class="fate-detail-tag">⏱ {USE_TYPE_LABEL[card.use_type] ?? card.use_type}</span>
        {/if}
      </div>

      <!-- 描述 -->
      <div class="fate-detail-body">
        <p class="fate-detail-description">{card.description}</p>

        <!-- 使用提示 -->
        {#if card.use_hint}
          <div class="fate-detail-hint">
            <span class="fate-detail-hint-icon">💡</span>
            <span>{card.use_hint}</span>
          </div>
        {/if}

        <!-- 效果 -->
        <div class="fate-detail-effect">
          <span class="fate-detail-effect-label">效果类型</span>
          <code class="fate-detail-effect-code">{card.effect_type}</code>
        </div>

        <!-- 已用 -->
        {#if card.used}
          <div class="fate-detail-used-banner">
            ✓ 此卡已使用
          </div>
        {/if}
      </div>

      <!-- 操作按钮 -->
      <div class="fate-detail-actions">
        <Button
          variant="ghost"
          size="md"
          onclick={onclose}
          disabled={submitting}
        >
          收起
        </Button>
        <Button
          variant="primary"
          size="md"
          onclick={handleUse}
          disabled={submitting || card.used}
        >
          {#if submitting}
            <Spinner size={16} /> 使用中...
          {:else if card.used}
            已使用
          {:else}
            ✨ 启用此卡
          {/if}
        </Button>
      </div>

      <p class="fate-detail-hint-bottom">提示：按 Esc 收起</p>
    </div>
  {/if}
</ModalShell>

<style>
  .fate-detail {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    min-width: 400px;
    max-width: 480px;
  }
  .fate-detail-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-5) var(--space-4);
    border-radius: var(--radius-md);
    color: white;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }
  .fate-detail-icon {
    font-size: 64px;
    line-height: 1;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
  }
  .fate-detail-name {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 600;
    color: white;
  }
  .fate-detail-tag {
    padding: 2px 10px;
    background: rgba(255,255,255,0.25);
    border-radius: 12px;
    font-size: var(--text-xs);
    font-weight: 500;
  }
  .fate-detail-body {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .fate-detail-description {
    margin: 0;
    font-family: var(--font-body);
    font-size: var(--text-md);
    line-height: 1.7;
    color: var(--color-ink);
    text-indent: 2em;
  }
  .fate-detail-hint {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: rgba(143, 75, 40, 0.06);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: 1.6;
  }
  .fate-detail-hint-icon {
    flex-shrink: 0;
    font-size: var(--text-base);
  }
  .fate-detail-effect {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
  }
  .fate-detail-effect-label {
    color: var(--color-ink-light);
    font-weight: 500;
  }
  .fate-detail-effect-code {
    color: var(--color-cinnabar);
    font-family: var(--font-numeric);
    font-weight: 600;
  }
  .fate-detail-used-banner {
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    text-align: center;
    font-size: var(--text-sm);
    color: var(--color-ink-light);
  }
  .fate-detail-actions {
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
  }
  .fate-detail-hint-bottom {
    margin: 0;
    text-align: center;
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    opacity: 0.6;
  }
</style>
