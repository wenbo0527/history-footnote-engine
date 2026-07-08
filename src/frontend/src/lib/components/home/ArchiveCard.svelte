<script lang="ts">
  /**
   * ArchiveCard 存档卡片
   * 用于"我的存档"列表中每条记录
   */
  import type { Archive } from '$lib/api/types';

  interface Props {
    archive: Archive;
    onclick?: () => void;
    ondelete?: () => void;
  }

  let { archive, onclick, ondelete }: Props = $props();

  // 格式化时间
  function formatTime(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
      });
    } catch {
      return iso;
    }
  }

  const eraName = $derived(archive.era_id === 'wanli1587' ? '万历十五年' : archive.era_id);
</script>

<article class="archive-card">
  <button
    type="button"
    class="archive-card-main"
    onclick={onclick}
    aria-label={`加载存档 ${archive.character_name}`}
  >
    <div class="archive-card-header">
      <h3 class="archive-card-name">{archive.character_name}</h3>
      <span class="archive-card-occupation">{archive.character_occupation}</span>
    </div>
    <div class="archive-card-meta">
      <span class="archive-card-era">{eraName}</span>
      <span class="archive-card-year">万历{archive.year - 1573}年</span>
      <span class="archive-card-round">第 {archive.round} 回合</span>
    </div>
    <div class="archive-card-stats">
      <span class="archive-card-stat">💰 {archive.cash.toFixed(2)} 两</span>
      <span class="archive-card-stat">💳 {archive.debt.toFixed(2)} 两</span>
    </div>
    <div class="archive-card-time">{formatTime(archive.updated_at)}</div>
  </button>

  {#if ondelete}
    <button
      type="button"
      class="archive-card-delete"
      onclick={ondelete}
      aria-label="删除存档"
      title="删除存档"
    >
      ×
    </button>
  {/if}
</article>

<style>
  .archive-card {
    position: relative;
    display: flex;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .archive-card:hover {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze-dark);
    box-shadow: var(--shadow-fold);
  }

  .archive-card-main {
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-4) var(--space-5);
    text-align: left;
    background: none;
    border: none;
    cursor: pointer;
    color: inherit;
    font: inherit;
  }

  .archive-card-header {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
    flex-wrap: wrap;
  }

  .archive-card-name {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0;
  }

  .archive-card-occupation {
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
  }

  .archive-card-meta {
    display: flex;
    gap: var(--space-3);
    flex-wrap: wrap;
    font-size: var(--text-sm);
    color: var(--color-ink-light);
  }

  .archive-card-era,
  .archive-card-year,
  .archive-card-round {
    font-family: var(--font-numeric);
  }

  .archive-card-stats {
    display: flex;
    gap: var(--space-4);
    font-size: var(--text-sm);
    color: var(--color-ink);
    font-family: var(--font-numeric);
  }

  .archive-card-time {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }

  .archive-card-delete {
    flex: 0 0 auto;
    width: 40px;
    font-size: 20px;
    color: var(--color-ink-light);
    background: none;
    border: none;
    border-left: 1px solid var(--color-ink-faint);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .archive-card-delete:hover {
    color: var(--color-cinnabar);
    background: var(--color-paper-dark);
  }
</style>
