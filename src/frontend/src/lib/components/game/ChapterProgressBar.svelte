<script lang="ts">
  /**
   * 🆕 v2.8.0 ChapterProgressBar — 章节进度条
   *
   * 显示在 GameHeader 的时代进度条下方：
   *   ┌─────────────────────────────────────────┐
   *   │ 📖 第一章 · 春蚕 · 节点 2/4            │
   *   │ [████████░░░░░░░░] 50%              │
   *   └─────────────────────────────────────────┘
   *
   * 节点圆点：●(已完成)◉(当前)○(未到)
   *
   * 当 chapter 未激活（active=false）：显示"游戏尚未进入章节制"
   */
  import { onMount } from 'svelte';
  import { getChapterState, type ChapterStateResponse } from '$lib/api/chapter';

  interface Props {
    sessionId: string;
    /** 章节激活时点击"章节历史"按钮的回调（可选） */
    onHistoryClick?: () => void;
  }

  let { sessionId, onHistoryClick }: Props = $props();

  let state: ChapterStateResponse | null = $state(null);
  let error: string | null = $state(null);

  async function refresh() {
    if (!sessionId) return;
    try {
      error = null;
      state = await getChapterState(sessionId);
    } catch (e) {
      // 老存档可能没 chapter_state，容错：active=false
      state = {
        active: false,
        current_chapter: 0,
        current_node: 1,
        node_count: 4,
        chapter_start_round: 1,
        round_number: 0,
        rounds_elapsed: 0,
        last_closure_status: 'INIT',
        progress_pct: 0,
        player_build: '',
        main_path_focus: '',
        active_plate: '',
      };
      error = (e as Error).message;
    }
  }

  onMount(() => {
    refresh();
    // 每 30 秒刷新一次（章节状态变化频率低）
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  });

  // 节点序号 1..N
  const totalNodes = $derived(state?.node_count || 4);
  const currentNode = $derived(state?.current_node || 1);
  const nodes = $derived(Array.from({ length: totalNodes }, (_, i) => i + 1));

  // 当前章节标题
  const chapterLabel = $derived(() => {
    if (!state?.active) return null;
    return `第 ${state.current_chapter} 章 · 节点 ${state.current_node}/${state.node_count}`;
  });

  // Build 标签
  const buildLabel = $derived(state?.player_build && state.player_build.trim() ? `Build: ${state.player_build}` : '');

  // 路径标签
  const pathLabel = $derived(state?.main_path_focus && state.main_path_focus.trim() ? `🎯 ${state.main_path_focus}` : '');

  // 板块标签
  const plateLabel = $derived(state?.active_plate && state.active_plate.trim() ? `板块: ${state.active_plate}` : '');
</script>

{#if state}
  <div class="chapter-bar" class:inactive={!state.active}>
    {#if state.active}
      <div class="chapter-bar-row">
        <span class="chapter-bar-icon" aria-hidden="true">📖</span>
        <span class="chapter-bar-title">{chapterLabel()}</span>
        <span class="chapter-bar-meta">
          {#if buildLabel}<span class="chapter-bar-tag build">{buildLabel}</span>{/if}
          {#if pathLabel}<span class="chapter-bar-tag path">{pathLabel}</span>{/if}
          {#if plateLabel}<span class="chapter-bar-tag plate">{plateLabel}</span>{/if}
        </span>
        {#if onHistoryClick}
          <button
            type="button"
            class="chapter-bar-history-btn"
            onclick={onHistoryClick}
            aria-label="查看章节历史"
          >
            📚
          </button>
        {/if}
      </div>
      <div class="chapter-bar-row progress-row">
        <div class="chapter-bar-nodes" role="progressbar" aria-valuenow={state.progress_pct} aria-valuemin="0" aria-valuemax="100">
          {#each nodes as idx (`node-${idx}`)}
            <span
              class="chapter-bar-node"
              class:completed={idx < currentNode}
              class:current={idx === currentNode}
              class:upcoming={idx > currentNode}
              aria-label={`节点 ${idx}`}
            >{idx}</span>
          {/each}
        </div>
        <div class="chapter-bar-progress-text">
          {state.progress_pct.toFixed(0)}% · 第 {state.round_number} 回合
        </div>
      </div>
    {:else}
      <div class="chapter-bar-inactive">
        <span aria-hidden="true">📖</span>
        <span>章节制未激活 · 游戏中</span>
        <small>{error || '（老存档或首次游戏）'}</small>
      </div>
    {/if}
  </div>
{/if}

<style>
  .chapter-bar {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-2) var(--space-3);
    background: linear-gradient(135deg, rgba(165, 42, 42, 0.06) 0%, rgba(218, 165, 32, 0.04) 100%);
    border: 1px solid rgba(218, 165, 32, 0.2);
    border-radius: var(--radius-md);
    color: var(--color-bronze-dark, #8b6914);
    font-family: var(--font-body);
    font-size: var(--text-xs);
  }

  .chapter-bar.inactive {
    opacity: 0.6;
    font-style: italic;
    background: transparent;
    border-style: dashed;
  }

  .chapter-bar-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .chapter-bar-row + .chapter-bar-row {
    margin-top: var(--space-1);
  }

  .chapter-bar-icon {
    font-size: var(--text-sm);
    flex-shrink: 0;
  }

  .chapter-bar-title {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: var(--text-sm);
    color: var(--color-ink, #2a1a0e);
    flex-shrink: 0;
  }

  .chapter-bar-meta {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    flex: 1 1 auto;
    flex-wrap: wrap;
    min-width: 0;
  }

  .chapter-bar-tag {
    display: inline-flex;
    align-items: center;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    font-family: var(--font-body);
    white-space: nowrap;
  }
  .chapter-bar-tag.build {
    background: rgba(143, 75, 40, 0.1);
    color: var(--color-bronze-dark, #8b4513);
  }
  .chapter-bar-tag.path {
    background: rgba(70, 130, 100, 0.1);
    color: var(--color-jade-dark, #2d6049);
  }
  .chapter-bar-tag.plate {
    background: rgba(180, 50, 50, 0.1);
    color: var(--color-crimson-dark, #8b2020);
  }

  .chapter-bar-history-btn {
    background: transparent;
    border: 1px solid var(--color-bronze, #daa520);
    border-radius: var(--radius-sm);
    padding: 2px 6px;
    font-size: var(--text-sm);
    cursor: pointer;
    color: var(--color-bronze-dark);
    flex-shrink: 0;
    transition: background var(--duration-normal);
  }
  .chapter-bar-history-btn:hover {
    background: rgba(218, 165, 32, 0.1);
  }

  .progress-row {
    justify-content: space-between;
  }

  .chapter-bar-nodes {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    flex: 1 1 auto;
  }

  .chapter-bar-node {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.6em;
    height: 1.6em;
    border-radius: var(--radius-full);
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    font-weight: 600;
    flex-shrink: 0;
  }

  .chapter-bar-node.completed {
    background: var(--color-jade);
    color: var(--color-paper);
  }
  .chapter-bar-node.current {
    background: var(--color-bronze);
    color: var(--color-paper);
    box-shadow: 0 0 0 3px rgba(218, 165, 32, 0.2);
    animation: chapter-pulse 2s ease-in-out infinite;
  }
  .chapter-bar-node.upcoming {
    background: transparent;
    color: var(--color-bronze-dark);
    border: 1px dashed var(--color-bronze);
  }

  @keyframes chapter-pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(218, 165, 32, 0.2); }
    50%      { box-shadow: 0 0 0 6px rgba(218, 165, 32, 0.05); }
  }

  .chapter-bar-progress-text {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
    flex-shrink: 0;
  }

  .chapter-bar-inactive {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--color-bronze-dark, #8b6914);
  }
  .chapter-bar-inactive small {
    color: var(--color-bronze);
    opacity: 0.7;
    font-size: 0.85em;
  }
</style>
