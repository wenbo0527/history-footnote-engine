<script lang="ts">
  /**
   * ArchiveCard 存档卡片
   * 用于"我的存档"列表中每条记录
   *
   * 🆕 v2.10.2 fix: 派生 name/occupation
   * - 后端不返回 character_name/character_occupation（已废弃字段）
   * - 用 selected_identity 派生（IDENTITY_PRESETS）
   * - 若 IDENTITY_PRESETS 也没匹配，显示 generic "盛泽织户"
   */
  import type { Archive, Identity } from '$lib/api/types';
  import { IDENTITY_PRESETS } from '$lib/stores/wizard.svelte';

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

  // 🆕 v2.10.2 fix: 派生人物信息（用 selected_identity + IDENTITY_PRESETS）
  const characterName = $derived.by(() => {
    // 优先用旧字段（兼容老存档）
    if (archive.character_name && archive.character_name.trim()) {
      return archive.character_name;
    }
    // 否则用 selected_identity 派生
    const preset = IDENTITY_PRESETS[archive.selected_identity as Identity];
    if (preset) {
      return preset.name;
    }
    // 兜底
    return '盛泽织户';
  });

  const characterOccupation = $derived.by(() => {
    if (archive.character_occupation && archive.character_occupation.trim()) {
      return archive.character_occupation;
    }
    const preset = IDENTITY_PRESETS[archive.selected_identity as Identity];
    if (preset) {
      return preset.profile.occupation;
    }
    return '织工';
  });
</script>

<article class="archive-card">
  <button
    type="button"
    class="archive-card-main"
    onclick={onclick}
    aria-label={`加载存档 ${characterName}`}
  >
    <div class="archive-card-header">
      <h3 class="archive-card-name">{characterName}</h3>
      <span class="archive-card-occupation">{characterOccupation}</span>
    </div>
    <div class="archive-card-meta">
      <span class="archive-card-era">{eraName}</span>
      <!-- 🆕 v2.10.1 fix: Archive 类型无 year/cash/debt 字段，只显示 current_round -->
      <span class="archive-card-round">第 {archive.current_round} 回合</span>
    </div>
    <div class="archive-card-time">{formatTime(archive.last_saved_at)}</div>
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
