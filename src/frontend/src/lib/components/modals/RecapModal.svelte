<script lang="ts">
  /**
   * RecapModal - 剧情回顾
   *
   * 直接展示当前会话所有 narrative 全文，不调 LLM。
   * 国风：章节式 + 朱砂标题
   *
   * 🆕 v1.7.30: 字段对齐后端（recent[] + archive[]）
   * 🆕 v1.7.32: 后端默认返完整 NARRATIVE_RECENT_SIZE=20 条 + ARCHIVE_SIZE=100 条摘要
   * 🆕 v2.10.1 W78: 加玩家选择 + 故事衔接
   * 🆕 v2.10.1 W82: 改用 Icon 组件
   * 🆕 v2.10.1 W83: 按章节分目录（侧边导航）+ 移除假 loading
   *              → 直接展示已有 narrative，不再"DM 整理..."
   *              → 左侧章节列表（按月分组），点击滚动到章节
   */
  import { game } from '$lib/stores';
  import { getRecap, type RecapResponse, type RecapNarrativeItem } from '$lib/api/recap';
  import { Chapter, Spinner, Button, Tabs, Icon } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';
  import type { RecapNarrativeItem as Item, RecapChapter } from '$lib/api/types';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  let { open, onclose }: Props = $props();

  let loading = $state(false);
  let recap = $state<RecapResponse | null>(null);
  let error = $state<string | null>(null);
  let activeTab = $state<'chapter' | 'archive'>('chapter');  // 🆕 W83: 默认"按章节"
  let searchKeyword = $state('');

  // 🆕 W83: 当前激活章节（点击左侧导航）
  let activeChapterId = $state<string | null>(null);

  // 🆕 W83: 章节列表（已分组，按月）
  const chapters = $derived(recap?.chapters ?? []);

  // 兼容旧模式：flat list（filtered）
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

  // 🆕 W83: 加载即触发（仍走 API，但内容是已有 narrative，不调 LLM）
  $effect(() => {
    if (open && $game && !recap && !loading) {
      loadRecap();
    }
  });

  async function loadRecap() {
    if (!$game) return;
    loading = true;
    error = null;
    try {
      recap = await getRecap($game.session_id);
      // 默认激活第一章节
      if (recap?.chapters && recap.chapters.length > 0) {
        activeChapterId = recap.chapters[0].chapter_id;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    } finally {
      loading = false;
    }
  }

  // 🆕 W83: 点击章节 → 滚动到对应位置
  function scrollToChapter(chapterId: string) {
    activeChapterId = chapterId;
    const el = document.getElementById(`chapter-${chapterId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        <span>当前: {recap.current_date ?? '未明'}</span>
        <span>共 {recap.total_narratives} 条叙事</span>
        {#if recap.round_number}
          <span>第 {recap.round_number} 回合</span>
        {/if}
      </div>

      <Tabs
        tabs={[
          { id: 'chapter', label: `按章节 (${chapters.length})` },  <!-- 🆕 W83 -->
          { id: 'archive', label: `存档 (${recap.archive.length})` }
        ]}
        value={activeTab}
        onchange={(id) => activeTab = id as 'chapter' | 'archive'}
      />

      <!-- 🆕 v2.10.1 W82: 用 Icon 组件（不用 emoji） -->
      <div class="recap-search">
        <Icon name="search" size={16} class="recap-search-icon" />
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

      <!-- 🆕 v2.10.1 W83: 按章节分（左侧章节目录 + 主区内容） -->
      {#if activeTab === 'chapter'}
        {#if chapters.length === 0}
          <p class="recap-empty">暂无章节（还未生成叙事）</p>
        {:else}
          <div class="recap-chapter-layout">
            <!-- 左侧章节目录 -->
            <nav class="recap-chapter-toc">
              <div class="recap-chapter-toc-title">目 录</div>
              <ul class="recap-chapter-toc-list">
                {#each chapters as ch (ch.chapter_id)}
                  <li>
                    <button
                      type="button"
                      class="recap-chapter-toc-item"
                      class:active={String(ch.chapter_id) === activeChapterId}
                      onclick={() => scrollToChapter(String(ch.chapter_id))}
                    >
                      <span class="recap-chapter-toc-index">
                        {#if ch.is_current}<span class="recap-chapter-dot" title="当前进行中">●</span>{/if}
                        {ch.chapter_id > 0 ? `第${ch.display_index}章` : '序章'}
                      </span>
                      <span class="recap-chapter-toc-title-text">{ch.title}</span>
                      <span class="recap-chapter-toc-count">{ch.narratives.length} 回合</span>
                    </button>
                  </li>
                {/each}
              </ul>
            </nav>

            <!-- 主区：按章节展示 narrative -->
            <div class="recap-chapter-main">
              {#each chapters as ch (ch.chapter_id)}
                <section class="recap-chapter-section" id="chapter-{ch.chapter_id}">
                  <header class="recap-chapter-section-header">
                    <div class="recap-chapter-section-title-wrap">
                      <h3 class="recap-chapter-section-title">
                        {ch.chapter_id > 0 ? `第${ch.display_index}章` : '序章'}
                        · {ch.title}
                        {#if ch.is_current}<span class="recap-chapter-current">（进行中）</span>{/if}
                      </h3>
                      {#if ch.subtitle && ch.is_settled}
                        <p class="recap-chapter-section-subtitle">{ch.subtitle}</p>
                      {/if}
                      {#if ch.summary && ch.is_settled}
                        <p class="recap-chapter-section-summary">{ch.summary}</p>
                      {/if}
                    </div>
                    <span class="recap-chapter-section-count">
                      {ch.narratives.length} 回合{#if ch.date_label} · {ch.date_label}{/if}
                    </span>
                  </header>
                  <div class="recap-list">
                    {#each ch.narratives as item, idx (ch.chapter_id + '-' + item.round)}
                      <article class="recap-item">
                        <header class="recap-item-header">
                          <span class="recap-round">第 {item.round} 回合</span>
                          {#if item.summary}
                            <span class="recap-summary">{item.summary}</span>
                          {/if}
                        </header>
                        {#if item.player_input || item.chosen_voice}
                          <div class="recap-choice">
                            <Icon name="gear" size={14} class="recap-choice-icon" />
                            <span class="recap-choice-text">
                              {#if item.chosen_voice}
                                你的选择：<strong>{item.chosen_voice}</strong>
                                {#if item.player_input && item.player_input !== item.chosen_voice}
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
                    {/each}
                  </div>
                </section>
              {/each}
            </div>
          </div>
        {/if}
      {:else if activeTab === 'recent'}
        <!-- W83 兼容旧模式：flat recent list -->
        {#if filteredRecent.length === 0}
          <p class="recap-empty">{searchKeyword ? `「${searchKeyword}」无匹配回合` : '暂无近期叙事'}</p>
        {:else}
          <div class="recap-list">
            {#each filteredRecent as item, idx (idx)}
              {@const prevDate = idx > 0 ? filteredRecent[idx - 1].current_date : null}
              {@const showMonth = item.current_date && item.current_date !== prevDate}
              {#if showMonth}
                <div class="recap-month-marker">
                  <span class="recap-month-marker-line"></span>
                  <span class="recap-month-marker-text">{item.current_date}</span>
                  <span class="recap-month-marker-line"></span>
                </div>
              {/if}
              <article class="recap-item">
                <header class="recap-item-header">
                  <span class="recap-round">第 {item.round} 回合</span>
                  {#if item.summary}
                    <span class="recap-summary">{item.summary}</span>
                  {/if}
                </header>
                {#if item.player_input || item.chosen_voice}
                  <div class="recap-choice">
                    <Icon name="gear" size={14} class="recap-choice-icon" />
                    <span class="recap-choice-text">
                      {#if item.chosen_voice}
                        你的选择：<strong>{item.chosen_voice}</strong>
                        {#if item.player_input && item.player_input !== item.chosen_voice}
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
            {/each}
          </div>
        {/if}
      {:else}
        {#if filteredArchive.length === 0}
          <p class="recap-empty">{searchKeyword ? `「${searchKeyword}」无匹配回合` : '暂无存档叙事'}</p>
        {:else}
          <div class="recap-list">
            {#each filteredArchive as item, idx (idx)}
              {@const prevDate = idx > 0 ? filteredArchive[idx - 1].current_date : null}
              {@const showMonth = item.current_date && item.current_date !== prevDate}
              {#if showMonth}
                <div class="recap-month-marker">
                  <span class="recap-month-marker-line"></span>
                  <span class="recap-month-marker-text">{item.current_date}</span>
                  <span class="recap-month-marker-line"></span>
                </div>
              {/if}
              <article class="recap-item">
                <header class="recap-item-header">
                  <span class="recap-round">第 {item.round} 回合</span>
                </header>
                {#if item.player_input || item.chosen_voice}
                  <div class="recap-choice">
                    <span class="recap-choice-icon">⚙</span>
                    <span class="recap-choice-text">
                      {#if item.chosen_voice}
                        你的选择：<strong>{item.chosen_voice}</strong>
                      {:else}
                        你的行动：<em>「{item.player_input}」</em>
                      {/if}
                    </span>
                  </div>
                {/if}
                <p class="recap-narrative-preview">{item.narrative}</p>
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
    /* 🆕 v2.10.1 W78: 文字展示优化 */
    max-width: 65ch;
    text-indent: 2em;        /* 中文段落首行缩进 */
    letter-spacing: 0.02em;  /* 字距微调 */
  }
  .recap-narrative-preview {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    line-height: var(--leading-relaxed);
    color: var(--color-ink-light);
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    max-width: 65ch;
    text-indent: 2em;
    letter-spacing: 0.02em;
  }

  /* 🆕 W78: 玩家选择样式 */
  .recap-choice {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    margin-bottom: var(--space-2);
    background: rgba(143, 75, 40, 0.06);
    border-left: 2px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }
  .recap-choice-icon {
    color: var(--color-bronze);
    font-size: var(--text-base);
    line-height: 1.4;
    flex-shrink: 0;
  }
  .recap-choice-text strong {
    color: var(--color-cinnabar);
    font-weight: 600;
  }
  .recap-choice-text em {
    font-style: italic;
    color: var(--color-ink);
  }

  /* 🆕 W78: 月份标记（衔接） */
  .recap-month-marker {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin: var(--space-4) 0 var(--space-2);
  }
  .recap-month-marker-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(
      to right,
      transparent,
      var(--color-ink-faint),
      transparent
    );
  }
  .recap-month-marker-text {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
    font-weight: 600;
    letter-spacing: 0.1em;
    padding: 0 var(--space-2);
    background: var(--color-paper);
  }

  /* 🆕 v2.10.1 W83: 章节布局（左侧 TOC + 右侧内容） */
  .recap-chapter-layout {
    display: grid;
    grid-template-columns: 180px 1fr;
    gap: var(--space-4);
    min-height: 400px;
  }
  .recap-chapter-toc {
    position: sticky;
    top: 0;
    align-self: start;
    max-height: 500px;
    overflow-y: auto;
    padding: var(--space-3);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
  }
  .recap-chapter-toc-title {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-cinnabar);
    font-weight: 600;
    text-align: center;
    padding-bottom: var(--space-2);
    margin-bottom: var(--space-2);
    border-bottom: 1px solid var(--color-ink-faint);
    letter-spacing: 0.2em;
  }
  .recap-chapter-toc-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .recap-chapter-toc-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
    text-align: left;
    font-family: var(--font-body);
  }
  .recap-chapter-toc-item:hover {
    background: var(--color-paper);
    border-color: var(--color-bronze);
  }
  .recap-chapter-toc-item.active {
    background: var(--color-paper);
    border-color: var(--color-cinnabar);
    box-shadow: 0 0 0 1px var(--color-cinnabar);
  }
  .recap-chapter-toc-index {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-cinnabar);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .recap-chapter-dot {
    color: var(--color-cinnabar);
    font-size: 10px;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
  }
  .recap-chapter-toc-title-text {
    font-size: var(--text-xs);
    color: var(--color-ink);
    margin-top: 2px;
    font-weight: 500;
  }
  .recap-chapter-toc-count {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    font-family: var(--font-numeric);
    margin-top: 2px;
  }
  .recap-chapter-main {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    max-height: 500px;
    overflow-y: auto;
    padding-right: var(--space-2);
  }
  .recap-chapter-section {
    scroll-margin-top: var(--space-2);
  }
  .recap-chapter-section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    margin-bottom: var(--space-2);
    border-bottom: 2px solid var(--color-bronze);
  }
  .recap-chapter-section-title-wrap {
    flex: 1;
  }
  .recap-chapter-section-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--text-lg);
    color: var(--color-cinnabar);
    font-weight: 600;
  }
  .recap-chapter-current {
    margin-left: var(--space-2);
    font-size: var(--text-sm);
    color: var(--color-bronze);
    font-weight: 400;
    font-style: italic;
  }
  .recap-chapter-section-subtitle {
    margin: var(--space-1) 0 0;
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
    font-style: italic;
  }
  .recap-chapter-section-summary {
    margin: var(--space-2) 0 0;
    padding: var(--space-2) var(--space-3);
    background: rgba(143, 75, 40, 0.05);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    line-height: 1.6;
    color: var(--color-ink-light);
    text-indent: 2em;
  }
  .recap-chapter-section-count {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    padding: 2px 8px;
    background: var(--color-paper-aged);
    border-radius: 10px;
    white-space: nowrap;
    flex-shrink: 0;
  }
</style>
