<script lang="ts">
  /**
   * CharCard 角色卡
   *
   * 桌面：固定 240px
   * 移动：可折叠（默认展开）→ 100% 宽
   *
   * 数据来源：state.game.character + state.game.family + state.game.skills
   */
  import type { Character, FamilyMember, Skill, FateCard } from '$lib/api/types';
  import { game } from '$lib/stores';
  import { fateEvents } from '$lib/stores/fate-events';
  import FateCardDetailModal from '../modals/FateCardDetailModal.svelte';
  import FateHandSection from './FateHandSection.svelte';

  interface Props {
    character: Character;
    family?: FamilyMember[];
    skills?: Skill[];
    collapsible?: boolean;
  }

  let { character, family = [], skills = [], collapsible = true }: Props = $props();

  let expanded = $state(true);

  // 🆕 v2.7 命运卡：从 game store 拉（不再依赖外部 prop）
  const fateHand: FateCard[] = $derived($game?.fate_hand ?? []);

  // 🆕 v2.10.1 W80: 卡包模式 - 点击 chip 弹详情窗
  let selectedCard = $state<FateCard | null>(null);
  let detailOpen = $state(false);

  function handleChipClick(card: FateCard) {
    selectedCard = card;
    detailOpen = true;
  }

  function closeDetail() {
    detailOpen = false;
    setTimeout(() => { selectedCard = null; }, 200);
  }

  // 旧 API 保留（兼容 fateEvents 总线）
  function handleQuickUse(cardId: string, e: Event) {
    e.stopPropagation();
    fateEvents.useCard(cardId);
  }
</script>

<aside class="char-card" class:char-card-collapsed={collapsible && !expanded}>
  <header class="char-card-header">
    <div class="char-card-avatar" aria-hidden="true">
      <img
        src={`/character/${character.identity ?? $game?.identity ?? 'weaving_male'}.webp`}
        alt=""
        class="char-card-avatar-img"
        onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
      />
    </div>
    <h3 class="char-card-name">{character.name}</h3>
    <p class="char-card-meta">{character.occupation} · {character.age}岁</p>
    <p class="char-card-location">{character.hometown}</p>
  </header>

  {#if collapsible}
    <button
      type="button"
      class="char-card-toggle"
      onclick={() => expanded = !expanded}
      aria-expanded={expanded}
      aria-label={expanded ? '折叠角色卡' : '展开角色卡'}
    >
      <span class="char-card-toggle-icon" aria-hidden="true">
        {expanded ? '▾' : '▸'}
      </span>
    </button>
  {/if}

  {#if !collapsible || expanded}
    <div class="char-card-body">
      {#if family.length > 0}
        <section class="char-card-section">
          <h4 class="char-card-section-title">家庭</h4>
          {#each family as f, i (i)}
            <p class="char-card-family-row">
              <span class="char-card-family-rel">{f.relation}：{f.name}</span>
              <span class="char-card-family-age">{f.age}岁</span>
            </p>
          {/each}
        </section>
      {/if}

      {#if skills.length > 0}
        <section class="char-card-section">
          <h4 class="char-card-section-title">技能</h4>
          {#each skills as s, i (i)}
            <p class="char-card-skill">
              <span class="char-card-skill-name">{s.name}</span>
              <span class="char-card-skill-stars" aria-label={`等级 ${s.level}`}>
                {'⭐'.repeat(s.level)}
              </span>
            </p>
          {/each}
        </section>
      {/if}

      <!-- 🆕 v2.7: 命运卡预览（始终可见，玩家一打开就看到自己的卡） -->
      {#if fateHand.length > 0}
        <FateHandSection fateHand={fateHand} onchipclick={handleChipClick} />
      {/if}
    </div>
  {/if}
</aside>

<!-- 🆕 v2.10.1 W80: 命运卡详情弹窗 -->
<FateCardDetailModal
  open={detailOpen}
  card={selectedCard}
  onclose={closeDetail}
/>

<style>
  .char-card {
    display: flex;
    flex-direction: column;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-fold);
    overflow: hidden;
    /* 🆕 v2.7 容器查询：让 char-card 知道自己的宽度，自适应 */
    container-type: inline-size;
    container-name: char-card;
  }

  .char-card-header {
    flex: 0 0 auto;  /* 🆕 v2.7 不收缩，按内容定高 */
    padding: var(--space-5);
    text-align: center;
    background: linear-gradient(180deg, var(--color-paper-aged) 0%, var(--color-paper) 100%);
    border-bottom: 1px solid var(--color-ink-faint);
  }

  .char-card-avatar {
    line-height: 1;
    margin-bottom: var(--space-2);
    display: flex;
    justify-content: center;
  }

  .char-card-avatar-img {
    width: 6em;
    height: 7.5em;
    object-fit: contain;
  }

  .char-card-name {
    font-family: var(--font-display);
    font-size: var(--text-xl);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0 0 var(--space-1);
    letter-spacing: var(--tracking-wide);
  }

  .char-card-meta {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
    margin: 0 0 var(--space-1);
  }

  .char-card-location {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    margin: 0;
  }

  .char-card-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-2);
    background: var(--color-paper);
    border: none;
    border-top: 1px solid var(--color-ink-faint);
    color: var(--color-bronze-dark);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .char-card-toggle:hover {
    background: var(--color-paper-aged);
    color: var(--color-cinnabar);
  }

  .char-card-toggle-icon {
    display: inline-block;
  }

  .char-card-body {
    flex: 1 1 auto;     /* 🆕 v2.7 占满剩余高度 */
    min-height: 0;      /* 🆕 flex 子项可滚动关键 */
    overflow-y: auto;   /* 🆕 溢出滚动（避免覆盖 header） */
    padding: var(--space-4) var(--space-5);
  }

  .char-card-section + .char-card-section {
    margin-top: var(--space-4);
    padding-top: var(--space-3);
    border-top: 1px dashed var(--color-ink-faint);
  }

  .char-card-section-title {
    font-family: var(--font-display);
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-bronze-dark);
    letter-spacing: var(--tracking-wide);
    margin: 0 0 var(--space-2);
  }

  /* 🆕 v2.7 命运卡预览段 */
  .char-card-fate-count {
    font-family: var(--font-numeric);
    font-size: 10px;
    font-weight: 400;
    color: var(--color-ink-faint);
    margin-left: var(--space-1);
  }

  .char-card-fate-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
  }

  .char-card-fate-chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px 6px 2px 2px;  /* 🆕 W81: 左侧少 padding 给缩略图 */
    background: var(--color-paper);
    border: 1px solid var(--card-color, var(--color-bronze));
    border-radius: 10px;
    font-family: var(--font-body);
    /* 🆕 W81: 缩略图尺寸 */
  }
  .char-card-fate-thumb {
    width: 24px;
    height: 32px;
    object-fit: cover;
    border-radius: 4px;
    flex-shrink: 0;
    background: var(--color-paper-aged);
    /* 🆕 v2.7 自适应字号：窄屏更小，宽屏稍大 */
    font-size: clamp(9px, 2.4cqw, 11px);
    color: var(--color-ink);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    position: relative;
    /* 🆕 防 chip 自身过长 */
    max-width: 100%;
  }

  .char-card-fate-name {
    font-family: var(--font-display);
    color: var(--color-ink);
    /* 🆕 文字超长省略 */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 12ch;  /* 最多 12 个汉字 */
  }

  .char-card-fate-chip:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(58, 42, 26, 0.15);
  }

  .char-card-fate-chip:focus-visible {
    outline: 2px solid var(--card-color, var(--color-bronze));
    outline-offset: 1px;
  }

  /* 🆕 v2.7 一键使用角标 */
  .char-card-fate-quick {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    margin-left: 2px;
    background: var(--card-color, var(--color-bronze));
    color: var(--color-paper);
    border-radius: 50%;
    font-size: 8px;
    line-height: 1;
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    opacity: 0.7;
  }

  .char-card-fate-chip:hover .char-card-fate-quick {
    opacity: 1;
    transform: scale(1.15);
  }

  .char-card-fate-quick:hover {
    transform: scale(1.3) !important;
    box-shadow: 0 0 6px var(--card-color, var(--color-bronze));
  }

  .char-card-fate-chip-used {
    opacity: 0.4;
    filter: grayscale(60%);
    padding: 2px 4px;
  }

  .char-card-fate-icon {
    font-size: var(--text-xs);
    line-height: 1;
    flex: 0 0 auto;
  }

  .char-card-fate-more {
    font-family: var(--font-numeric);
    font-size: 10px;
    color: var(--color-ink-faint);
  }

  .char-card-fate-used {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 3px;
    margin-top: var(--space-2);
  }

  .char-card-fate-used-label {
    font-family: var(--font-body);
    font-size: 10px;
    color: var(--color-ink-faint);
  }

  /* 🆕 v2.7 容器查询：char-card 窄时（< 260px）只显示图标不显示名字 */
  @container char-card (max-width: 260px) {
    .char-card-fate-name {
      display: none;
    }
    .char-card-fate-chip {
      padding: 2px 4px;
    }
  }

  /* 🆕 v2.7 容器查询：char-card 极窄时（< 200px）连图标也隐藏角标 */
  @container char-card (max-width: 200px) {
    .char-card-fate-quick {
      display: none;
    }
  }

  .char-card-family-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    margin: var(--space-1) 0;
  }

  .char-card-family-age {
    font-family: var(--font-numeric);
    color: var(--color-ink-light);
    font-size: var(--text-xs);
  }

  .char-card-skill {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    margin: var(--space-1) 0;
  }

  .char-card-skill-stars {
    color: var(--color-bronze);
    font-size: var(--text-sm);
    letter-spacing: 0;
  }

  /* 折叠态：只隐藏 body，toggle 按钮必须保留（否则玩家无法重新展开） */
  .char-card-collapsed .char-card-body {
    display: none;
  }

  /* 折叠态下 toggle 加朱砂色高亮 — 让玩家一眼看到"点这儿展开" */
  .char-card-collapsed .char-card-toggle {
    background: var(--color-cinnabar);
    color: var(--color-paper);
    border-top-color: var(--color-cinnabar);
  }
  .char-card-collapsed .char-card-toggle:hover {
    background: var(--color-cinnabar-light, #c44040);
    color: var(--color-paper);
  }

  /* ============================================================
   * v1.7.32 响应式
   *   - Wide (≥ 1600):     加大 padding 提升呼吸感
   *   - Desktop (1024-1599): 默认
   *   - Tablet (768-1023):   紧凑化（padding 减半，avatar 缩小）
   *   - Mobile (≤ 767):     横向布局（avatar + name 一行，下面 1 列堆叠）
   * ============================================================ */

  /* Tablet：紧凑化 */
  @media (max-width: 1023px) {
    .char-card-header {
      padding: var(--space-3);
    }
    .char-card-avatar {
      font-size: var(--text-3xl);
    }
    .char-card-name {
      font-size: var(--text-lg);
    }
    .char-card-body {
      padding: var(--space-2) var(--space-3);
    }
  }

  /* Mobile：横向布局 */
  @media (max-width: 767px) {
    .char-card {
      flex-direction: row;
      align-items: stretch;
    }
    .char-card-header {
      flex: 0 0 auto;
      padding: var(--space-2) var(--space-3);
      border-bottom: none;
      border-right: 1px solid var(--color-ink-faint);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-width: 96px;
    }
    .char-card-avatar {
      font-size: var(--text-2xl);
      margin-bottom: var(--space-1);
    }
    .char-card-name {
      font-size: var(--text-base);
    }
    .char-card-meta, .char-card-location {
      font-size: var(--text-xs);
    }
    .char-card-toggle {
      flex: 0 0 36px;
      border-top: none;
      border-left: 1px solid var(--color-ink-faint);
    }
  }

  /* Wide：加 padding 提升呼吸感 */
  @media (min-width: 1600px) {
    .char-card-header {
      padding: var(--space-6) var(--space-5);
    }
    .char-card-avatar {
      font-size: var(--text-5xl);
    }
    .char-card-name {
      font-size: var(--text-2xl);
    }
    .char-card-body {
      padding: var(--space-5) var(--space-6);
    }
  }
</style>
