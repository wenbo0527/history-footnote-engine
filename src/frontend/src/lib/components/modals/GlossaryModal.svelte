<script lang="ts">
  /**
   * GlossaryModal - 词条查询
   *
   * 输入查询词 → 后端返回词条列表（terms[]）或单个词条详情
   *
   * 🆕 v1.7.30: 字段对齐后端
   * - 搜索模式：返回 terms[] 列表（点单个词条看详情）
   * - 详情模式：返回单个词条（key, category, definition, example, related）
   */
  import { game } from '$lib/stores';
  import { queryGlossary, getTerm, type TermDetail } from '$lib/api/glossary';
  import { Chapter, Spinner, Button, Divider } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';
  import GlossaryTermItem from './GlossaryTermItem.svelte';
  import type { GlossaryResponse } from '$lib/api/types';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  let { open, onclose }: Props = $props();

  let query = $state('');
  let loading = $state(false);
  let searchResult = $state<GlossaryResponse | null>(null);
  let detail = $state<TermDetail | null>(null);
  let error = $state<string | null>(null);

  $effect(() => {
    if (open) {
      query = '';
      searchResult = null;
      detail = null;
      error = null;
    }
  });

  async function handleSearch() {
    if (!query.trim() || loading) return;
    loading = true;
    error = null;
    detail = null;
    try {
      searchResult = await queryGlossary(query.trim(), $game?.session_id);
    } catch (e) {
      error = e instanceof Error ? e.message : '查询失败';
    } finally {
      loading = false;
    }
  }

  async function handleSelectTerm(key: string) {
    loading = true;
    error = null;
    try {
      const t = await getTerm(key);
      if (t) detail = t;
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    } finally {
      loading = false;
    }
  }

  function handleBackToList() {
    detail = null;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  }
</script>

<ModalShell {open} {onclose} title="词 条 解 释" size="md">
  <div class="glossary-search">
    <input
      type="text"
      class="glossary-input"
      placeholder="如：挽丝 / 牙行 / 矿税监"
      bind:value={query}
      onkeydown={handleKeydown}
      disabled={loading}
    />
    <Button
      variant="primary"
      onclick={handleSearch}
      disabled={!query.trim() || loading}
      loading={loading}
    >
      查询
    </Button>
  </div>

  <Divider variant="dashed" spacing="sm" />

  {#if loading && !searchResult && !detail}
    <div class="glossary-loading">
      <Spinner mode="brush" size={32} />
      <p>查阅中...</p>
    </div>
  {:else if error}
    <p class="glossary-error">⚠ {error}</p>
  {:else if detail}
    <!-- 单个词条详情 -->
    <article class="glossary-result">
      <Button variant="ghost" size="sm" onclick={handleBackToList}>← 返回列表</Button>
      <Chapter title={detail.key} level={2} />
      <div class="glossary-meta">
        <span class="glossary-category">{detail.category}</span>
      </div>
      <p class="glossary-definition">{detail.definition}</p>
      {#if detail.example}
        <div class="glossary-example">
          <h4 class="glossary-related-title">例</h4>
          <p class="glossary-example-text">{detail.example}</p>
        </div>
      {/if}
      {#if detail.related && detail.related.length > 0}
        <div class="glossary-related">
          <h4 class="glossary-related-title">相关</h4>
          <div class="glossary-related-tags">
            {#each detail.related as r, i (i)}
              <button
                type="button"
                class="glossary-related-tag"
                onclick={() => handleSelectTerm(r)}
              >{r}</button>
            {/each}
          </div>
        </div>
      {/if}
    </article>
  {:else if searchResult}
    <!-- 搜索结果列表 -->
    <div class="glossary-search-result">
      <Chapter title="查询结果" level={3} />
      <p class="glossary-meta-info">
        找到 <strong>{searchResult.count}</strong> 个词条
        （字典共 {searchResult.total_in_dict} 个）
      </p>
      {#if searchResult.terms.length === 0}
        <p class="glossary-hint">未找到相关词条。试试其他关键词。</p>
      {:else}
        <ul class="glossary-terms-list">
          {#each searchResult.terms as t (t.key)}
            <li>
              <GlossaryTermItem
                term={t}
                disabled={loading}
                onselect={handleSelectTerm}
              />
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {:else}
    <p class="glossary-hint">
      输入万历年间的术语、方言或历史概念，DM 将为你解释其来历与含义。
    </p>
  {/if}
</ModalShell>

<style>
  .glossary-search {
    display: flex;
    gap: var(--space-2);
  }

  .glossary-input {
    flex: 1 1 0;
    padding: var(--space-3);
    font-family: var(--font-body);
    font-size: var(--text-base);
    color: var(--color-ink);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
  }

  .glossary-input:focus {
    outline: none;
    border-color: var(--color-bronze);
    background: var(--color-paper);
    box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.1);
  }

  .glossary-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    color: var(--color-ink-light);
    font-style: italic;
  }

  .glossary-error {
    color: var(--color-cinnabar);
    padding: var(--space-3);
  }

  .glossary-hint {
    text-align: center;
    color: var(--color-ink-faint);
    font-style: italic;
    padding: var(--space-5);
  }

  .glossary-search-result {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .glossary-meta-info {
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0;
  }

  .glossary-terms-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    max-height: 400px;
    overflow-y: auto;
  }

  .glossary-term-item {
    width: 100%;
    text-align: left;
    padding: var(--space-3) var(--space-4);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .glossary-term-item:hover:not(:disabled) {
    background: var(--color-paper);
    border-left-color: var(--color-cinnabar);
  }
  .glossary-term-item:disabled {
    opacity: 0.5;
  }

  .glossary-term-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-1);
  }

  .glossary-term-key {
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 600;
    color: var(--color-ink);
  }

  .glossary-term-category {
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    padding: 1px 6px;
    background: var(--color-paper);
    border-radius: var(--radius-sm);
  }

  .glossary-term-def {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: var(--leading-snug);
    margin: 0;
  }

  .glossary-result {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .glossary-meta {
    display: flex;
    gap: var(--space-2);
  }

  .glossary-category {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    padding: 2px 8px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
  }

  .glossary-definition {
    font-family: var(--font-body);
    font-size: var(--text-md);
    line-height: var(--leading-relaxed);
    color: var(--color-ink);
    margin: 0;
  }

  .glossary-example {
    background: var(--color-paper-aged);
    padding: var(--space-3);
    border-left: 2px solid var(--color-bronze);
    border-radius: var(--radius-sm);
  }

  .glossary-example-text {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    line-height: var(--leading-relaxed);
    color: var(--color-ink);
    margin: 0;
    font-style: italic;
  }

  .glossary-related-title {
    font-family: var(--font-display);
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-bronze-dark);
    letter-spacing: var(--tracking-wide);
    margin: 0 0 var(--space-2);
  }

  .glossary-related-tags {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .glossary-related-tag {
    padding: var(--space-1) var(--space-3);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-full);
    color: var(--color-bronze-dark);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .glossary-related-tag:hover {
    background: var(--color-bronze);
    color: var(--color-paper);
  }
</style>
