<!--
  🆕 v2.10.1 W80-W81: 命运卡详情弹窗（中国算命风·整卡图）

  点击 CharCard 命运卡 chip → 弹此窗
  - 整卡图（mmx image generate 生成，中国算命风）
  - 卡名 + 使用时机
  - 描述 + 使用提示
  - "启用此卡" / "收起" 按钮
-->
<script lang="ts">
  import ModalShell from './ModalShell.svelte';
  import { Button, Spinner } from '$lib/components/design-system';
  import { fateUse } from '$lib/api/fate';
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
  let imgError = $state(false);

  // 关闭后清空
  $effect(() => {
    if (!open) {
      setTimeout(() => {
        submitting = false;
        imgError = false;
      }, 200);
    }
  });

  async function handleUse() {
    if (!card || !$game) return;
    submitting = true;
    try {
      const context = (card.use_type === 'round_start' ? 'round_start'
                    : card.use_type === 'emergency' ? 'emergency'
                    : 'immediate') as 'immediate' | 'round_start' | 'emergency';
      const res = await fateUse($game.session_id, card.id, context);
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

  // use_type 中文标签
  const USE_TYPE_LABEL: Record<string, string> = {
    immediate: '即时使用',
    round_start: '回合开始',
    emergency: '紧急',
    any: '任何时机',
  };

  // 🆕 v2.10.1 W81: 解析 image_url
  // 后端可能返完整 URL 或相对路径，统一处理
  function getCardImageUrl(card: FateCard | null): string {
    if (!card) return '/fate/card_back.svg';
    // 后端在 image_url 字段（可能没有，用 fallback）
    const url = (card as any).image_url || `/fate/${card.id}.webp`;
    // 如果已经是完整 URL（http/https）直接用
    if (url.startsWith('http')) return url;
    // 相对路径 → 加上 / 前缀
    if (!url.startsWith('/')) return `/${url}`;
    return url;
  }
</script>

<ModalShell {open} {onclose} title="命 运 卡" size="md">
  {#if card}
    <div class="fate-detail">
      <!-- 🆕 W81: 整卡图（中国算命风） -->
      <div class="fate-detail-card">
        {#if !imgError}
          <img
            src={getCardImageUrl(card)}
            alt={card.name}
            class="fate-detail-img"
            onerror={() => { imgError = true; }}
          />
        {:else}
          <!-- fallback: emoji 渐变 -->
          <div class="fate-detail-fallback" style="background: linear-gradient(135deg, {card.color}cc, {card.color}88);">
            <div class="fate-detail-icon">{card.icon}</div>
          </div>
        {/if}
        <!-- 使用时机角标（覆盖在卡上） -->
        {#if card.use_type && !imgError}
          <span class="fate-detail-time-badge">⏱ {USE_TYPE_LABEL[card.use_type] ?? card.use_type}</span>
        {/if}
        <!-- 已用蒙层 -->
        {#if card.used}
          <div class="fate-detail-used-overlay">已 使用</div>
        {/if}
      </div>

      <!-- 卡名 -->
      <div class="fate-detail-info">
        <h2 class="fate-detail-name">{card.name}</h2>
        <p class="fate-detail-id">id: {card.id}</p>
      </div>

      <!-- 描述 -->
      <div class="fate-detail-body">
        <p class="fate-detail-description">{card.description}</p>

        {#if card.use_hint}
          <div class="fate-detail-hint">
            <span class="fate-detail-hint-icon">💡</span>
            <span>{card.use_hint}</span>
          </div>
        {/if}

        <div class="fate-detail-effect">
          <span class="fate-detail-effect-label">效果类型</span>
          <code class="fate-detail-effect-code">{card.effect_type}</code>
        </div>
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
  /* 🆕 W81: 整卡图容器（竖版 3:4） */
  .fate-detail-card {
    position: relative;
    width: 240px;
    height: 320px;
    margin: 0 auto;
    border-radius: 12px;
    overflow: hidden;
    box-shadow:
      0 2px 8px rgba(0,0,0,0.15),
      0 8px 24px rgba(0,0,0,0.2);
    background: var(--color-paper-aged);
    border: 2px solid #6b5230;
  }
  .fate-detail-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .fate-detail-fallback {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .fate-detail-fallback .fate-detail-icon {
    font-size: 96px;
    line-height: 1;
    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
  }
  .fate-detail-time-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 3px 10px;
    background: rgba(0,0,0,0.6);
    color: #f5ebd4;
    font-size: var(--text-xs);
    font-weight: 500;
    border-radius: 12px;
    backdrop-filter: blur(4px);
  }
  .fate-detail-used-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-15deg);
    padding: 12px 24px;
    background: rgba(165, 40, 40, 0.85);
    color: #f5ebd4;
    font-family: var(--font-display);
    font-size: var(--text-xl);
    font-weight: 700;
    border-radius: 6px;
    border: 3px solid #f5ebd4;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }
  /* 卡名 */
  .fate-detail-info {
    text-align: center;
  }
  .fate-detail-name {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 600;
    color: var(--color-ink);
  }
  .fate-detail-id {
    margin: var(--space-1) 0 0;
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    font-family: var(--font-numeric);
    opacity: 0.5;
  }
  /* 描述区 */
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
  /* 操作按钮 */
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
