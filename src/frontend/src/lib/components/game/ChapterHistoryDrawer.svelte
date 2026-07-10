<script lang="ts">
  /**
   * 🆕 v2.8.0 ChapterHistoryDrawer — 章节历史抽屉
   *
   * 弹出式展示已结算章节摘要列表
   * 每条显示 chapter/summary/closure_status/rounds/transition
   */
  import { getChapterHistory, type ChapterHistoryResponse } from '$lib/api/chapter';

  interface Props {
    sessionId: string;
    open: boolean;
    onClose: () => void;
  }

  let { sessionId, open, onClose }: Props = $props();

  let history = $state<ChapterHistoryResponse | null>(null);
  let error = $state<string | null>(null);
  let loading = $state(false);

  async function load() {
    if (!sessionId || !open) return;
    loading = true;
    error = null;
    try {
      history = await getChapterHistory(sessionId);
    } catch (e) {
      error = (e as Error).message;
      history = { count: 0, history: [] };
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (open) load();
  });
</script>

{#if open}
  <div class="chapter-drawer-backdrop" onclick={onClose} role="presentation"></div>
  <aside class="chapter-drawer" role="dialog" aria-label="章节历史">
    <header class="chapter-drawer-header">
      <h2>📚 章节历史</h2>
      <button type="button" onclick={onClose} class="chapter-drawer-close" aria-label="关闭">×</button>
    </header>

    <div class="chapter-drawer-body">
      {#if loading}
        <p class="chapter-drawer-loading">加载中…</p>
      {:else if error}
        <p class="chapter-drawer-error">错误: {error}</p>
      {:else if history && history.history.length === 0}
        <p class="chapter-drawer-empty">尚未结算任何章节。第一章尚未结束。</p>
      {:else if history}
        <ol class="chapter-drawer-list">
          {#each history.history as record (`chapter-${record.chapter}`)}
            <li class="chapter-drawer-record">
              <header class="chapter-drawer-record-header">
                <span class="chapter-drawer-chapter-num">第 {record.chapter} 章</span>
                <span
                  class="chapter-drawer-status"
                  class:ready={record.closure_status === 'SOFT_READY'}
                  class:forced={record.closure_status === 'HARD_FORCED'}
                >
                  {record.closure_status || 'UNKNOWN'}
                </span>
              </header>
              <p class="chapter-drawer-summary">{record.summary}</p>
              <dl class="chapter-drawer-meta">
                {#if record.rounds_in_chapter !== undefined}
                  <dt>回合</dt>
                  <dd>{record.rounds_in_chapter}</dd>
                {/if}
                {#if record.transition}
                  <dt>转化</dt>
                  <dd>{record.transition}</dd>
                {/if}
                {#if record.key_choice}
                  <dt>选择</dt>
                  <dd>{record.key_choice}</dd>
                {/if}
              </dl>
            </li>
          {/each}
        </ol>
      {/if}
    </div>
  </aside>
{/if}

<style>
  .chapter-drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 100;
  }
  .chapter-drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 380px;
    max-width: 100vw;
    background: var(--color-paper, #faf6ed);
    box-shadow: -4px 0 12px rgba(0, 0, 0, 0.15);
    z-index: 101;
    display: flex;
    flex-direction: column;
    border-left: 1px solid var(--color-bronze, #daa520);
  }
  .chapter-drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-3);
    border-bottom: 1px solid rgba(218, 165, 32, 0.2);
  }
  .chapter-drawer-header h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-lg);
    color: var(--color-ink, #2a1a0e);
  }
  .chapter-drawer-close {
    background: transparent;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--color-bronze-dark);
    padding: 4px 10px;
    border-radius: var(--radius-sm);
  }
  .chapter-drawer-close:hover {
    background: rgba(218, 165, 32, 0.1);
  }
  .chapter-drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-3);
  }
  .chapter-drawer-loading,
  .chapter-drawer-error,
  .chapter-drawer-empty {
    color: var(--color-bronze-dark);
    font-style: italic;
    text-align: center;
    padding: var(--space-6) var(--space-2);
  }
  .chapter-drawer-error {
    color: var(--color-crimson-dark, #8b2020);
  }
  .chapter-drawer-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .chapter-drawer-record {
    border: 1px solid rgba(218, 165, 32, 0.3);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    background: rgba(255, 255, 255, 0.4);
  }
  .chapter-drawer-record-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-1);
  }
  .chapter-drawer-chapter-num {
    font-family: var(--font-display);
    font-weight: 600;
    color: var(--color-ink);
  }
  .chapter-drawer-status {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    padding: 1px 6px;
    border-radius: var(--radius-sm);
    background: var(--color-bronze);
    color: var(--color-paper);
  }
  .chapter-drawer-status.forced {
    background: var(--color-crimson, #b22222);
  }
  .chapter-drawer-summary {
    margin: var(--space-1) 0;
    line-height: 1.5;
    color: var(--color-ink);
  }
  .chapter-drawer-meta {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px var(--space-2);
    margin: var(--space-2) 0 0;
    font-size: var(--text-xs);
  }
  .chapter-drawer-meta dt {
    color: var(--color-bronze-dark);
    font-weight: 500;
  }
  .chapter-drawer-meta dd {
    margin: 0;
    color: var(--color-ink);
  }
</style>
