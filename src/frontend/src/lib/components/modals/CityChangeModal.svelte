<!--
  🆕 v2.10.1 W77: 城市变更确认弹窗

  当 LLM 触发 arrive.X 事件时，后端写入 state.pending_city_change
  → 前端检测到 → 弹"是否要去 XX"确认
  → 玩家点"出发" → 调 /api/confirm_city_change
  → 玩家点"留下" → 调 /api/reject_city_change
-->
<script lang="ts">
  import ModalShell from './ModalShell.svelte';
  import { Button } from '$lib/components/design-system';

  interface Props {
    open: boolean;
    fromCity: string;
    toCity: string;
    narrative: string;
    onConfirm: () => void;
    onReject: () => void;
  }

  let { open, fromCity, toCity, narrative, onConfirm, onReject }: Props = $props();

  // 城市 id → 中文名映射
  const CITY_NAMES: Record<string, string> = {
    shengze: '盛泽镇',
    suzhou: '苏州城',
    hangzhou: '杭州',
    nanjing: '南京',
    songjiang: '松江',
    jiaxing: '嘉兴',
  };

  let fromName = $derived(CITY_NAMES[fromCity] ?? fromCity);
  let toName = $derived(CITY_NAMES[toCity] ?? toCity);
  let submitting = $state(false);

  function handleConfirm() {
    if (submitting) return;
    submitting = true;
    onConfirm();
    setTimeout(() => { submitting = false; }, 1500);
  }

  function handleReject() {
    if (submitting) return;
    submitting = true;
    onReject();
    setTimeout(() => { submitting = false; }, 1500);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!open) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      handleReject();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      handleConfirm();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<ModalShell {open} title="离开盛泽？" onclose={handleReject}>
  <div class="city-change">
    <div class="city-change-icon">🚶</div>
    <p class="city-change-headline">
      <strong>{fromName}</strong> → <strong>{toName}</strong>
    </p>
    {#if narrative}
      <p class="city-change-narrative">"{narrative}"</p>
    {/if}
    <p class="city-change-warning">
      离开故土后，街坊邻里难得照面。
      <br />
      确认要动身吗？
    </p>
    <div class="city-change-actions">
      <Button
        variant="ghost"
        size="md"
        onclick={handleReject}
        disabled={submitting}
      >
        留下
      </Button>
      <Button
        variant="primary"
        size="md"
        onclick={handleConfirm}
        disabled={submitting}
      >
        {submitting ? '处理中...' : '出发'}
      </Button>
    </div>
    <p class="city-change-hint">提示：按 Enter 出发 / 按 Esc 留下</p>
  </div>
</ModalShell>

<style>
  .city-change {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) 0;
    min-width: 360px;
  }
  .city-change-icon {
    font-size: 48px;
    line-height: 1;
  }
  .city-change-headline {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-xl);
    color: var(--color-ink);
    font-weight: 600;
  }
  .city-change-headline strong {
    color: var(--color-cinnabar);
  }
  .city-change-narrative {
    margin: 0;
    padding: var(--space-3) var(--space-4);
    background: rgba(143, 75, 40, 0.06);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    font-style: italic;
    color: var(--color-ink-light);
    font-size: var(--text-sm);
    line-height: 1.6;
    max-width: 100%;
  }
  .city-change-warning {
    margin: 0;
    text-align: center;
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: 1.7;
  }
  .city-change-actions {
    display: flex;
    gap: var(--space-3);
    margin-top: var(--space-2);
  }
  .city-change-hint {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    opacity: 0.7;
  }
</style>
