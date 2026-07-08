<script lang="ts">
  /**
   * RecapModal - 剧情回顾
   *
   * 直接展示当前会话所有 narrative 全文，不调 LLM。
   * 国风：章节式 + 朱砂标题
   *
   * 🆕 v1.7.30: 字段对齐后端（recent[] + archive[]）
   * 🆕 v1.7.32: 后端默认返完整 NARRATIVE_RECENT_SIZE=20 条 + ARCHIVE_SIZE=100 条摘要，
   *   玩家可看到每一回合的完整 DM 叙事，不用等 LLM 总结
   */
  import { game } from '$lib/stores';
  import { getRecap, type RecapResponse, type RecapNarrativeItem } from '$lib/api/recap';
  import { Chapter, Spinner, Button, Tabs } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';
  import type { RecapNarrativeItem as Item } from '$lib/api/types';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  let { open, onclose }: Props = $props();

  let loading = $state(false);
  let recap = $state<RecapResponse | null>(null);
  let error = $state<string | null>(null);
  let activeTab = $state<'recent' | 'archive'>('recent');
  // 🆕 v1.7.32: 玩家可按关键词搜索全文（长 session 时有用）
  let searchKeyword = $state('');

  // 🆕 v1.7.32: 派生过滤（轻量级纯前端搜索）
  const filteredRecent = $derived.by(() => {
    if (!recap) return [];
    const kw = searchKeyword.trim();
    if (!kw) return recap.recent;
    return recap.recent.filter(it =>
      it.narrative?.includes(kw) ||
      it.summary?.includes(kw) ||
      `第 ${it.round} 回合`.includes(kw)
    );
  });
  const filteredArchive = $derived.by(() => {
    if (!recap) return [];
    const kw = searchKeyword.trim();
    if (!kw) return recap.archive;
    return recap.archive.filter(it =>
      it.narrative?.includes(kw) ||
      it.summary?.includes(kw) ||
      `第 ${it.round} 回合`.includes(kw)
    );
  });

  $effect(() => {
    if (open && $game && !recap) {
      loadRecap();
    }
  });

  async function loadRecap() {
    if (!$game) return;
    loading = true;
    error = null;
    try {
      recap = await getRecap($game.session_id);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    } finally {
      loading = false;
    }
  }
</script>

<ModalShell {open} {onclose} title="往 事 追 溯" size="lg">
  {#if loading}
    <div class="recap-loading">
      <Spinner mode="brush" size={48} />
      <p>DM 正在整理往事...</p>
    </div>
  {:else if error}
    <div class="recap-error">
      <p>⚠ {error}</p>
      <Button variant="primary" onclick={loadRecap}>重试</Button>
    </div>
  {:else if recap}
    <div class="recap-content">
      <Chapter title="回顾摘要" level={3} />
      <div class="recap-meta">
        <span>📅 当前: {recap.current_date ?? '未明'}</span>
        <span>📖 共 {recap.total_narratives} 条叙事</span>
        {#if recap.round_number}
          <span>🔄 第 {recap.round_number} 回合</span>
        {/if}
      </div>

      <Tabs
        tabs={[
          { id: 'recent', label: `最近 (${recap.recent.length})` },
          { id: 'archive', label: `存档 (${recap.archive.length})` }
        ]}
        value={activeTab}
        onchange={(id) => activeTab = id as 'recent' | 'archive'}
      />

      <!-- 🆕 v1.7.32: 关键词搜索（按 narrative/summary 全文匹配） -->
      <div class="recap-search">
        <span class="recap-search-icon" aria-hidden="true">🔍</span>
        <input
          type="text"
          bind:value={searchKeyword}
          placeholder="按关键词搜索（人名 / 事件 / 银钱）..."
          class="recap-search-input"
        />
        {#if searchKeyword}
          <button
            type="button"
            class="recap-search-clear"
            onclick={() => (searchKeyword = '')}
            aria-label="清除搜索"
          >×</button>
        {/if}
      </div>

      {#if activeTab === 'recent'}
        {#if filteredRecent.length === 0}
          <p class="recap-empty">{searchKeyword ? `「${searchKeyword}」无匹配回合` : '暂无近期叙事'}</p>
        {:else}
          <div class="recap-list">
            {#each filteredRecent as item, idx (idx)}
              <article class="recap-item">
                <header class="recap-item-header">
                  <span class="recap-round">第 {item.round} 回合</span>
                  {#if item.summary}
                    <span class="recap-summary">{item.summary}</span>
                  {/if}
                </header>
                <p class="recap-narrative">{item.narrative}</p>
              </article>
            {/each}
          </div>
        {/if}
      {:else}
        {#if filteredArchive.length === 0}
          <p class="recap-empty">{searchKeyword ? `「${searchKeyword}」无匹配回合` : '暂无存档叙事'}</p>
        {:else}
          <div class="recap-list">
            {#each filteredArchive as item, idx (idx)}
              <article class="recap-item">
                <header class="recap-item-header">
                  <span class="recap-round">第 {item.round} 回合</span>
                </header>
                <p class="recap-narrative">{item.narrative}</p>
              </article>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {:else}
    <p>暂无剧情可回顾</p>
  {/if}
</ModalShell>

<style>
  .recap-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-7);
    color: var(--color-ink-light);
    font-style: italic;
  }

  .recap-error {
    text-align: center;
    padding: var(--space-5);
    color: var(--color-cinnabar);
  }
  .recap-error p {
    margin: 0 0 var(--space-3);
  }

  .recap-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .recap-meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
  }

  .recap-empty {
    color: var(--color-ink-faint);
    text-align: center;
    padding: var(--space-5);
    font-style: italic;
  }

  .recap-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    max-height: 400px;
    overflow-y: auto;
  }

  /* 🆕 v1.7.32: 搜索框 */
  .recap-search {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    transition: border-color var(--duration-quick) var(--ease-ink);
  }
  .recap-search:focus-within {
    border-color: var(--color-cinnabar);
  }
  .recap-search-icon {
    color: var(--color-ink-light);
    font-size: var(--text-base);
  }
  .recap-search-input {
    flex: 1;
    border: none;
    background: transparent;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    outline: none;
  }
  .recap-search-input::placeholder {
    color: var(--color-ink-faint);
  }
  .recap-search-clear {
    background: none;
    border: none;
    color: var(--color-ink-light);
    font-size: var(--text-base);
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }
  .recap-search-clear:hover {
    color: var(--color-cinnabar);
  }

  .recap-item {
    padding: var(--space-3) var(--space-4);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--color-cinnabar);
    border-radius: var(--radius-sm);
  }

  .recap-item-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
  }

  .recap-round {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-cinnabar);
    font-weight: 600;
  }

  .recap-summary {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    padding: 2px 8px;
    background: var(--color-paper);
    border-radius: var(--radius-sm);
  }

  .recap-narrative {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    line-height: var(--leading-relaxed);
    color: var(--color-ink);
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
