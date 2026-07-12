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

  // 🆕 v2.10.2 fix: rename state → chapterState（避免与 Svelte 5 $state rune 冲突）
  let chapterState: ChapterStateResponse | null = $state(null);
  let error: string | null = $state(null);

  async function refresh() {
    if (!sessionId) return;
    try {
      error = null;
      chapterState = await getChapterState(sessionId);
    } catch (e) {
      // 老存档可能没 chapter_state，容错：active=false
      chapterState = {
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
  // 🆕 v2.10.2 fix: Svelte 5 推断 chapterState 为 never，加 (as ChapterStateResponse | null) 显式类型
  const totalNodes = $derived((chapterState as ChapterStateResponse | null)?.node_count || 4);
  const currentNode = $derived((chapterState as ChapterStateResponse | null)?.current_node || 1);
  const nodes = $derived(Array.from({ length: totalNodes }, (_, i) => i + 1));

  // 当前章节标题
  const chapterLabel = $derived.by(() => {
    const cs = chapterState as ChapterStateResponse | null;
    if (!cs?.active) return null;
    return `第 ${cs.current_chapter} 章 · 节点 ${cs.current_node}/${cs.node_count}`;
  });

  const cs = $derived(chapterState as ChapterStateResponse | null);
  const buildLabel = $derived(cs?.player_build && cs.player_build.trim() ? `Build: ${cs.player_build}` : '');
  const pathLabel = $derived(cs?.main_path_focus && cs.main_path_focus.trim() ? `🎯 ${cs.main_path_focus}` : '');
  const plateLabel = $derived(cs?.active_plate && cs.active_plate.trim() ? `板块: ${cs.active_plate}` : '');
</script>

{#if chapterState}
  <div class="chapter-bar" class:inactive={!chapterState.active}>
    {#if chapterState.active}
      <div class="chapter-bar-row">
        <span class="chapter-bar-icon" aria-hidden="true">📖</span>
        <!-- 🆕 v2.10.2 fix: chapterLabel 是 $derived 值，不是函数 -->
        <span class="chapter-bar-title">{chapterLabel}</span>
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
        <div class="chapter-bar-nodes" role="progressbar" aria-valuenow={chapterState.progress_pct} aria-valuemin="0" aria-valuemax="100">
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
          {chapterState.progress_pct.toFixed(0)}% · 第 {chapterState.round_number} 回合
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
