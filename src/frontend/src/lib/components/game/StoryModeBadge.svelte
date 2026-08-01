<script lang="ts">
  /**
   * 🆕 v2.10.22 — 剧本模式徽章
   *
   * 当 game.scripted_mode = true 时显示在 GameView 顶部
   * - 显示章节 + 当前节点
   * - 玩家可以"退出剧本模式"切回 LLM
   */
  import { game, gameActions } from '$lib/stores';
  import { toast } from '$lib/components/design-system/Toast.svelte';

  let scripted = $derived($game?.scripted_mode ?? false);
  let chapter = $derived($game?.scripted_chapter_id ?? 0);
  let nodeId = $derived($game?.scripted_node_id ?? '');
  let flagsCount = $derived(($game?.scripted_flags ?? []).length);
  let chapterComplete = $derived($game?.scripted_chapter_complete ?? false);
  let exiting = $state(false);

  async function handleExit() {
    if (!$game || exiting) return;
    if (!confirm('退出剧本模式？将保留已解锁的 flag 作为 LLM 提示。')) return;

    exiting = true;
    try {
      const { call } = await import('$lib/api/client');
      await call('/api/scripted/exit', { session_id: $game.session_id });
      // 更新本地状态
      const updated = { ...$game };
      updated.scripted_mode = false;
      updated.scripted_chapter_complete = false;
      gameActions.set(updated);
      toast.success('已退出剧本模式');
    } catch (e) {
      toast.error('退出失败：' + (e instanceof Error ? e.message : '未知错误'));
    } finally {
      exiting = false;
    }
  }

  function getChapterName(ch: number): string {
    const map: Record<number, string> = {
      1: '家贫',
      2: '织染',
      3: '丝绢案',
    };
    return map[ch] || `第${ch}章`;
  }
</script>

{#if scripted}
  <div class="story-mode-badge" class:complete={chapterComplete}>
    <div class="badge-icon">🎭</div>
    <div class="badge-info">
      <div class="badge-title">剧本模式 · {getChapterName(chapter)}</div>
      <div class="badge-meta">
        <code>{nodeId}</code>
        <span class="flags">🚩 {flagsCount}</span>
        {#if chapterComplete}
          <span class="complete-marker">✅ 章节完成</span>
        {/if}
      </div>
    </div>
    <button
      class="exit-btn"
      onclick={handleExit}
      disabled={exiting}
      title="退出剧本模式"
    >
      {exiting ? '退出中…' : '退出'}
    </button>
  </div>
{/if}

<style>
  .story-mode-badge {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    background: linear-gradient(135deg, #c44536 0%, #8b1a1a 100%);
    color: #fff8e1;
    border-radius: 4px;
    margin: 8px 16px;
    box-shadow: 0 2px 8px rgba(196, 69, 54, 0.3);
  }

  .story-mode-badge.complete {
    background: linear-gradient(135deg, #2c5e6f 0%, #1a3a44 100%);
  }

  .badge-icon {
    font-size: 24px;
  }

  .badge-info {
    flex: 1;
  }

  .badge-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 2px;
  }

  .badge-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    align-items: center;
    opacity: 0.85;
  }

  .badge-meta code {
    background: rgba(0, 0, 0, 0.2);
    padding: 1px 6px;
    border-radius: 2px;
    font-size: 11px;
  }

  .complete-marker {
    background: #fff8e1;
    color: #2c5e6f;
    padding: 1px 6px;
    border-radius: 8px;
    font-weight: 700;
  }

  .exit-btn {
    background: rgba(255, 248, 225, 0.2);
    color: #fff8e1;
    border: 1px solid rgba(255, 248, 225, 0.4);
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    transition: background 0.15s;
  }

  .exit-btn:hover:not(:disabled) {
    background: rgba(255, 248, 225, 0.3);
  }

  .exit-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>