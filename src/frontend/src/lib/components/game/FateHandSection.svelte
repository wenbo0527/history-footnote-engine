<script lang="ts">
  /**
   * FateHandSection - 角色卡中的命运卡预览段（CharCard 子组件）
   *
   * 拆出理由：原 CharCard.svelte 530 行
   * - 命运卡 section 模板 42 行 + 样式 ~80 行
   * - 含未用卡 chips + 已用卡 chips + 缩略图
   * - 拆出后 CharCard 减重 ~120 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { FateCard } from '$lib/api/types';

  interface Props {
    fateHand: FateCard[];
    onchipclick: (card: FateCard) => void;
  }

  let { fateHand, onchipclick }: Props = $props();

  const unusedFate = $derived(fateHand.filter(c => !c.used));
  const usedFate = $derived(fateHand.filter(c => c.used));
  // 最多显示 3 张（剩余的折叠）
  const visibleFate = $derived(unusedFate.slice(0, 3));
</script>

<section class="char-card-section char-card-fate">
  <h4 class="char-card-section-title">
    🎴 我的命运
    <span class="char-card-fate-count">{unusedFate.length} / {fateHand.length} 未用</span>
  </h4>
  {#if visibleFate.length > 0}
    <div class="char-card-fate-list">
      {#each visibleFate as c (c.id)}
        <button
          type="button"
          class="char-card-fate-chip"
          style="--card-color: {c.color}"
          title={c.description + '（点击查看详情）'}
          onclick={() => onchipclick(c)}
        >
          <!-- 🆕 v2.10.1 W81: 整卡缩略图 -->
          <img
            src={(c as any).image_url || `/fate/${c.id}.webp`}
            alt={c.name}
            class="char-card-fate-thumb"
            onerror={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
          />
          <span class="char-card-fate-name">{c.name}</span>
        </button>
      {/each}
      {#if unusedFate.length > 3}
        <span class="char-card-fate-more">+{unusedFate.length - 3} 张</span>
      {/if}
    </div>
  {/if}
  {#if usedFate.length > 0}
    <div class="char-card-fate-used">
      <span class="char-card-fate-used-label">已用：</span>
      {#each usedFate as c (c.id)}
        <span
          class="char-card-fate-chip char-card-fate-chip-used"
          style="--card-color: {c.color}"
          title={c.description}
        >
          <span class="char-card-fate-icon" aria-hidden="true">{c.icon}</span>
        </span>
      {/each}
    </div>
  {/if}
</section>

<style>
  .char-card-fate {
    border-top: 1px dashed var(--color-bronze);
  }
  .char-card-fate-count {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    margin-left: var(--space-2);
    font-weight: normal;
  }
  .char-card-fate-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }
  .char-card-fate-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px 4px 4px;
    background: var(--color-paper);
    border: 1px solid var(--card-color, var(--color-ink-faint));
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink);
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .char-card-fate-chip:hover {
    background: var(--color-paper-aged);
    transform: translateY(-1px);
    box-shadow: var(--shadow-1);
  }
  .char-card-fate-thumb {
    width: 28px;
    height: 36px;
    object-fit: cover;
    border-radius: 2px;
  }
  .char-card-fate-name {
    font-weight: 500;
  }
  .char-card-fate-more {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    padding: 4px 8px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
  }
  .char-card-fate-used {
    margin-top: var(--space-2);
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
  }
  .char-card-fate-used-label {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }
  .char-card-fate-chip-used {
    padding: 4px;
    opacity: 0.5;
    cursor: default;
  }
  .char-card-fate-icon {
    font-size: 16px;
  }
</style>