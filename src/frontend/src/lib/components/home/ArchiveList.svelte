<script lang="ts">
  /**
   * ArchiveList - 存档列表（StartMenu 子组件）
   *
   * 拆出理由：原 StartMenu.svelte 556 行
   * - 存档列表块 ~37 行 template + ~60 行样式
   * - 含 loading / empty / list 三态
   * - 拆出后主组件减少 ~100 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import { Spinner } from '$lib/components/design-system';
  import type { Archive } from '$lib/api/types';

  interface Props {
    archives: Archive[];
    loading: boolean;
    accountUsername: string | null;
    onload: (sessionId: string) => void;
  }

  let { archives, loading, accountUsername, onload }: Props = $props();

  // 🆕 时间格式化
  function formatDate(iso: string): string {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  }

  // 🆕 朝代名映射
  function eraName(eraId: string): string {
    return eraId === 'wanli1587' ? '万历十五年' : eraId;
  }
</script>

{#if loading && archives.length === 0}
  <div class="start-menu-loading">
    <Spinner mode="brush" size={32} />
    <p>正在加载存档...</p>
  </div>
{:else if archives.length === 0}
  <div class="start-menu-archive-empty">
    <img src="/icons/nav/archive.webp" alt="" class="start-menu-archive-empty-icon" />
    <p class="start-menu-archive-empty-title">暂无存档</p>
    <p class="start-menu-archive-empty-desc">
      {#if accountUsername}
        你的「{accountUsername}」账户下还没有存档
      {:else}
        当前为访客模式，存档仅保存在本地
      {/if}
      <br />
      点击左侧"开始新游戏"创建第一个故事
    </p>
  </div>
{:else}
  <p class="start-menu-archive-count">
    共 <strong>{archives.length}</strong> 个存档
  </p>
  <ul class="start-menu-archive-list">
    {#each archives as arc (arc.session_id)}
      <li>
        <button
          type="button"
          class="start-menu-archive-item"
          onclick={() => onload(arc.session_id)}
          title={arc.summary}
        >
          <div class="start-menu-archive-icon">
            {arc.era_id === 'wanli1587' ? '万' : '古'}
          </div>
          <div class="start-menu-archive-info">
            <div class="start-menu-archive-line1">
              <span class="start-menu-archive-era">{eraName(arc.era_id)}</span>
              <span class="start-menu-archive-round">第 {arc.current_round} 回合</span>
            </div>
            <div class="start-menu-archive-line2">{arc.summary || '新游戏'}</div>
            <div class="start-menu-archive-line3">{formatDate(arc.last_saved_at)}</div>
          </div>
          <span class="start-menu-archive-arrow">→</span>
        </button>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .start-menu-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-7);
    color: var(--color-ink-light);
    font-style: italic;
  }
  .start-menu-archive-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--space-7) var(--space-4);
    color: var(--color-ink-light);
  }
  .start-menu-archive-empty-icon {
    width: 64px;
    height: 64px;
    opacity: 0.4;
    margin-bottom: var(--space-2);
  }
  .start-menu-archive-empty-title {
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink);
    margin: 0 0 var(--space-1);
  }
  .start-menu-archive-empty-desc {
    font-size: var(--text-sm);
    color: var(--color-ink-faint);
    line-height: 1.6;
    margin: 0;
    max-width: 400px;
  }
  .start-menu-archive-count {
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0 0 var(--space-2);
  }
  .start-menu-archive-count strong {
    color: var(--color-cinnabar);
    font-family: var(--font-numeric);
    font-size: var(--text-md);
  }
  .start-menu-archive-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .start-menu-archive-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    text-align: left;
  }
  .start-menu-archive-item:hover {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
    transform: translateX(2px);
  }
  .start-menu-archive-icon {
    flex: 0 0 48px;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--color-paper-aged) 0%, var(--color-bronze) 100%);
    color: white;
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 600;
    border-radius: var(--radius-sm);
  }
  .start-menu-archive-info {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .start-menu-archive-line1 {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .start-menu-archive-era {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink);
    font-weight: 600;
  }
  .start-menu-archive-round {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }
  .start-menu-archive-line2 {
    font-size: var(--text-sm);
    color: var(--color-ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .start-menu-archive-line3 {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }
  .start-menu-archive-arrow {
    flex: 0 0 auto;
    color: var(--color-ink-faint);
    font-size: var(--text-md);
    transition: transform var(--duration-normal) var(--ease-ink);
  }
  .start-menu-archive-item:hover .start-menu-archive-arrow {
    color: var(--color-cinnabar);
    transform: translateX(2px);
  }
</style>