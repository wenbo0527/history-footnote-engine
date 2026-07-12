<script lang="ts">
  /**
   * CharacterCard - 单个角色卡片（CharacterWikiModal 子组件）
   *
   * 拆出理由：原 CharacterWikiModal.svelte 752 行
   * - 单个 card 模板约 60 行 + 100+ 行 .wiki-char-* 样式
   * - 拆出后主 modal 减少 ~160 行
   * - 卡片可独立复用（未来加 NPC 列表 / 关系图）
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { WikiCharacter } from '$lib/api/types';

  interface Props {
    character: WikiCharacter & { isFamily?: boolean; affinity?: number };
  }

  let { character }: Props = $props();

  // 角色类型
  const isFamily = $derived(character.isFamily ?? false);
  const affinity = $derived(character.affinity);
  const badge = $derived(statusBadge(character.status));

  // affinity 颜色（红/橙/黄/绿）
  function affinityColor(aff: number | undefined): string {
    if (aff === undefined) return 'transparent';
    if (aff >= 50) return '#6b8b5a';
    if (aff >= 0) return '#b8860b';
    if (aff >= -30) return '#a5703a';
    return '#a52828';
  }

  function affinityLabel(aff: number | undefined): string {
    if (aff === undefined) return '';
    if (aff >= 80) return '至亲';
    if (aff >= 50) return '亲近';
    if (aff >= 20) return '友善';
    if (aff >= -10) return '中立';
    if (aff >= -30) return '戒备';
    return '敌对';
  }

  // status 徽章
  function statusBadge(s: WikiCharacter['status']): { label: string; color: string } | null {
    if (!s || s === 'alive' || s === 'unknown') return null;
    if (s === 'dead') return { label: '已故', color: '#4a4a4a' };
    if (s === 'missing') return { label: '失踪', color: '#8b6f47' };
    return null;
  }
</script>

<article
  class="wiki-char-card"
  class:wiki-char-card-family={isFamily}
  style={affinity !== undefined ? `--aff-color: ${affinityColor(affinity)}` : ''}
>
  <!-- 头像位 -->
  <div class="wiki-char-portrait" aria-hidden="true">
    {#if character.portrait}
      <img src={character.portrait} alt={character.name} />
    {:else}
      <span class="wiki-char-portrait-emoji">
        {isFamily ? '🏠' : '👤'}
      </span>
    {/if}
    {#if badge}
      <span class="wiki-char-status" style="background: {badge.color}">
        {badge.label}
      </span>
    {/if}
  </div>

  <div class="wiki-char-body">
    <header class="wiki-char-name">
      <span class="wiki-char-name-text">{character.name}</span>
      <span
        class="wiki-char-relation"
        class:wiki-char-relation-family={isFamily}
      >{character.relation}</span>
    </header>
    <p class="wiki-char-meta">
      {#if character.age}<span>{character.age}岁</span>{/if}
      {#if character.first_met_round !== undefined && character.first_met_round > 0}
        <span class="wiki-char-meta-sep">·</span>
        <span>第 {character.first_met_round} 回合相遇</span>
      {/if}
    </p>
    <p class="wiki-char-desc" class:wiki-char-desc-empty={!character.description || character.description === '（暂无介绍）'}>
      {character.description && character.description !== '（暂无介绍）'
        ? character.description
        : '（未详细记录——继续互动以解锁）'}
    </p>
    {#if affinity !== undefined}
      <div class="wiki-char-aff">
        <span
          class="wiki-char-aff-bar"
          style="background: {affinityColor(affinity)}; width: {Math.min(Math.abs(affinity), 100)}%"
        ></span>
        <span class="wiki-char-aff-label">{affinityLabel(affinity)}</span>
      </div>
    {/if}
  </div>
</article>

<style>
  .wiki-char-card {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-md);
    transition: all var(--duration-normal) var(--ease-ink);
    position: relative;
  }
  .wiki-char-card:hover {
    transform: translateX(2px);
    box-shadow: var(--shadow-1);
    border-color: var(--color-bronze);
  }
  .wiki-char-card-family {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
  }
  .wiki-char-card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: var(--aff-color, transparent);
    border-radius: var(--radius-md) 0 0 var(--radius-md);
  }

  .wiki-char-portrait {
    position: relative;
    flex: 0 0 64px;
    width: 64px;
    height: 64px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .wiki-char-portrait img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .wiki-char-portrait-emoji {
    font-size: 32px;
  }
  .wiki-char-status {
    position: absolute;
    top: -4px;
    right: -4px;
    padding: 2px 6px;
    font-size: var(--text-xs);
    color: white;
    border-radius: var(--radius-sm);
    font-weight: 600;
  }

  .wiki-char-body {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .wiki-char-name {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .wiki-char-name-text {
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink);
    font-weight: 600;
  }
  .wiki-char-relation {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    padding: 1px 6px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
  }
  .wiki-char-relation-family {
    background: var(--color-bronze);
    color: white;
  }
  .wiki-char-meta {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    display: flex;
    gap: var(--space-1);
    margin: 0;
  }
  .wiki-char-meta-sep {
    color: var(--color-ink-faint);
  }
  .wiki-char-desc {
    font-size: var(--text-sm);
    color: var(--color-ink);
    line-height: 1.6;
    margin: var(--space-1) 0 0 0;
  }
  .wiki-char-desc-empty {
    color: var(--color-ink-faint);
    font-style: italic;
  }
  .wiki-char-aff {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-1);
  }
  .wiki-char-aff-bar {
    height: 4px;
    border-radius: 2px;
    flex: 0 0 auto;
    min-width: 0;
  }
  .wiki-char-aff-label {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }
</style>