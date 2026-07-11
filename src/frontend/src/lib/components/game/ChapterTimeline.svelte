<!--
  🆕 v2.9.x W46: ChapterTimeline — 章节历史时间线
  
  横向 SVG 时间线，圆点 = 章节，连线 = 章节间过渡。
  - past: 实心绿
  - current: 实心红 (pulse 动画)
  - future: 空心灰
  
  点击节点展开详情卡
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { getChapterHistory } from '$lib/api/chapter';
  import {
    toTimeline,
    progressPercent,
    chapterDotX,
    type TimelineNode,
  } from './chapterHistory';

  interface Props {
    sessionId: string;
    currentChapter?: number;
    totalChapters?: number;
  }

  let { sessionId, currentChapter = 0, totalChapters = 10 }: Props = $props();

  let nodes = $state<TimelineNode[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let selectedChapter = $state<number | null>(null);

  async function loadHistory() {
    if (!sessionId) return;
    try {
      loading = true;
      error = null;
      const resp = await getChapterHistory(sessionId);
      nodes = toTimeline(resp, currentChapter, totalChapters);
    } catch (e) {
      error = (e as Error).message;
      nodes = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadHistory();
  });

  // 进度条位置
  let progress = $derived(progressPercent(currentChapter, totalChapters));

  // 当前选中节点
  let selected = $derived(
    selectedChapter !== null ? nodes.find((n) => n.chapter === selectedChapter) : null
  );

  // 节点颜色
  function dotColor(node: TimelineNode): string {
    if (node.status === 'past') return 'rgb(80, 140, 80)';
    if (node.status === 'current') return 'rgb(180, 50, 50)';
    return 'rgb(180, 180, 180)';
  }

  // 连线颜色
  function lineColor(node: TimelineNode): string {
    if (node.status === 'past') return 'rgba(80, 140, 80, 0.6)';
    if (node.status === 'current') return 'rgba(180, 50, 50, 0.6)';
    return 'rgba(180, 180, 180, 0.4)';
  }
</script>

<section class="chapter-timeline" aria-label="章节时间线">
  <header class="chapter-timeline-header">
    <span class="chapter-timeline-icon" aria-hidden="true">📜</span>
    <h3 class="chapter-timeline-title">章节时间线</h3>
    <span class="chapter-timeline-progress">第 {currentChapter} / {totalChapters} 章 · {progress.toFixed(0)}%</span>
  </header>

  {#if loading}
    <p class="chapter-timeline-loading">加载中...</p>
  {:else if error}
    <p class="chapter-timeline-error">{error}</p>
  {:else}
    <div class="chapter-timeline-track" role="list">
      <svg
        class="chapter-timeline-svg"
        viewBox="0 0 100 8"
        preserveAspectRatio="none"
        aria-label="章节进度"
      >
        <!-- 背景轨道 -->
        <line
          class="chapter-timeline-track-bg"
          x1="0"
          y1="4"
          x2="100"
          y2="4"
          stroke="rgba(143, 75, 40, 0.15)"
          stroke-width="0.3"
        />
        <!-- 进度填充 -->
        <line
          class="chapter-timeline-track-fill"
          x1="0"
          y1="4"
          x2={progress}
          y2="4"
          stroke="rgba(80, 140, 80, 0.7)"
          stroke-width="0.4"
        />
        <!-- 已完成连线 -->
        {#each nodes as node (node.chapter)}
          {#if !node.isLast && node.status === 'past'}
            {@const next = nodes.find((n) => n.chapter === node.chapter + 1)}
            {#if next && next.status === 'past'}
              <line
                class="chapter-timeline-edge chapter-timeline-edge-past"
                x1={chapterDotX(node.chapter, totalChapters, 100)}
                y1="4"
                x2={chapterDotX(node.chapter + 1, totalChapters, 100)}
                y2="4"
                stroke={lineColor(node)}
                stroke-width="0.2"
              />
            {/if}
          {/if}
        {/each}
      </svg>

      <!-- 节点 -->
      <div class="chapter-timeline-nodes">
        {#each nodes as node (node.chapter)}
          <button
            type="button"
            class="chapter-timeline-node"
            class:chapter-timeline-node-past={node.status === 'past'}
            class:chapter-timeline-node-current={node.status === 'current'}
            class:chapter-timeline-node-future={node.status === 'future'}
            class:chapter-timeline-node-selected={selectedChapter === node.chapter}
            style:left={`${chapterDotX(node.chapter, totalChapters)}%`}
            style:--dot-color={dotColor(node)}
            onclick={() => {
              selectedChapter = selectedChapter === node.chapter ? null : node.chapter;
            }}
            aria-label={`第 ${node.chapter} 章 ${node.summary || '未开始'}`}
            title={`第 ${node.chapter} 章 — ${node.summary || '未开始'}`}
          >
            <span class="chapter-timeline-dot" aria-hidden="true"></span>
            <span class="chapter-timeline-label">{node.chapter}</span>
          </button>
        {/each}
      </div>
    </div>

    {#if selected}
      <div class="chapter-timeline-detail" role="region" aria-label="章节详情">
        <div class="chapter-timeline-detail-header">
          <strong>第 {selected.chapter} 章</strong>
          {#if selected.closureLabel}
            <span class="chapter-timeline-badge">{selected.closureLabel}</span>
          {/if}
          <span class="chapter-timeline-duration">{selected.durationLabel}</span>
        </div>
        {#if selected.summary}
          <p class="chapter-timeline-summary">{selected.summary}</p>
          {#if selected.core_event}
            <div class="chapter-timeline-meta">
              <span><strong>核心事件:</strong> {selected.core_event}</span>
            </div>
          {/if}
          {#if selected.key_choice}
            <div class="chapter-timeline-meta">
              <span><strong>关键抉择:</strong> {selected.key_choice}</span>
            </div>
          {/if}
          {#if selected.build_summary}
            <div class="chapter-timeline-meta">
              <span><strong>Build:</strong> {selected.build_summary}</span>
            </div>
          {/if}
          {#if selected.path_summary}
            <div class="chapter-timeline-meta">
              <span><strong>路径:</strong> {selected.path_summary}</span>
            </div>
          {/if}
          {#if selected.transition}
            <p class="chapter-timeline-transition">↪ {selected.transition}</p>
          {/if}
        {:else}
          <p class="chapter-timeline-empty">该章节尚未开始</p>
        {/if}
        <button
          type="button"
          class="chapter-timeline-close"
          onclick={() => (selectedChapter = null)}
        >
          关闭
        </button>
      </div>
    {/if}
  {/if}
</section>

<style>
  .chapter-timeline {
    padding: var(--space-3);
    background: var(--color-paper, rgba(255, 245, 220, 0.5));
    border: 1px solid rgba(143, 75, 40, 0.2);
    border-radius: var(--radius-sm, 4px);
  }

  .chapter-timeline-header {
    display: flex;
    align-items: center;
    gap: var(--space-2, 8px);
    margin-bottom: var(--space-2, 8px);
  }

  .chapter-timeline-icon { font-size: 1.2em; }
  .chapter-timeline-title {
    margin: 0;
    font-size: var(--text-base, 14px);
    font-weight: 600;
    color: var(--color-ink, #2a1a0a);
  }
  .chapter-timeline-progress {
    margin-left: auto;
    font-size: var(--text-xs, 11px);
    color: var(--color-ink-light, #6a5a4a);
  }

  .chapter-timeline-track {
    position: relative;
    height: 50px;
    margin: var(--space-2, 8px) 0;
  }
  .chapter-timeline-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }
  .chapter-timeline-nodes {
    position: relative;
    height: 100%;
  }
  .chapter-timeline-node {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    background: transparent;
    border: 0;
    padding: 0;
    cursor: pointer;
  }
  .chapter-timeline-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--dot-color, rgb(180, 180, 180));
    border: 2px solid white;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    transition: transform 0.2s;
  }
  .chapter-timeline-node:hover .chapter-timeline-dot {
    transform: scale(1.3);
  }
  .chapter-timeline-label {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    color: var(--color-ink, #2a1a0a);
  }
  .chapter-timeline-node-current .chapter-timeline-dot {
    animation: chapter-timeline-pulse 1.5s ease-in-out infinite;
  }
  @keyframes chapter-timeline-pulse {
    0%, 100% { transform: scale(1.0); }
    50% { transform: scale(1.2); }
  }
  .chapter-timeline-node-future .chapter-timeline-dot {
    background: white;
    border: 2px dashed rgba(180, 180, 180, 0.8);
  }
  .chapter-timeline-node-selected .chapter-timeline-dot {
    transform: scale(1.4);
    box-shadow: 0 0 0 3px rgba(180, 50, 50, 0.4);
  }

  .chapter-timeline-detail {
    margin-top: var(--space-3, 12px);
    padding: var(--space-2, 8px);
    background: rgba(255, 255, 255, 0.6);
    border-radius: var(--radius-sm, 4px);
    font-size: var(--text-xs, 11px);
    color: var(--color-ink, #2a1a0a);
  }
  .chapter-timeline-detail-header {
    display: flex;
    align-items: center;
    gap: var(--space-2, 8px);
    margin-bottom: 4px;
  }
  .chapter-timeline-badge {
    padding: 1px 6px;
    font-size: 10px;
    background: var(--color-bronze, #8f4b28);
    color: white;
    border-radius: 10px;
  }
  .chapter-timeline-duration {
    color: var(--color-ink-light, #6a5a4a);
    margin-left: auto;
  }
  .chapter-timeline-summary {
    margin: 4px 0;
    line-height: 1.5;
  }
  .chapter-timeline-meta {
    margin: 2px 0;
  }
  .chapter-timeline-transition {
    margin: 4px 0 0 0;
    color: var(--color-ink-light, #6a5a4a);
    font-style: italic;
  }
  .chapter-timeline-empty {
    color: var(--color-ink-light, #6a5a4a);
    font-style: italic;
  }
  .chapter-timeline-close {
    margin-top: var(--space-2, 8px);
    padding: 2px 8px;
    font-size: 10px;
    background: transparent;
    border: 1px solid rgba(143, 75, 40, 0.3);
    border-radius: var(--radius-sm, 4px);
    color: var(--color-bronze-dark, #6a3a1a);
    cursor: pointer;
  }
  .chapter-timeline-close:hover {
    background: rgba(143, 75, 40, 0.1);
  }

  .chapter-timeline-loading,
  .chapter-timeline-error {
    font-size: var(--text-xs, 11px);
    color: var(--color-ink-light, #6a5a4a);
    font-style: italic;
  }
  .chapter-timeline-error { color: var(--color-crimson-dark, #8a2a1a); }
</style>
