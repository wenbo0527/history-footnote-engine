<script lang="ts">
  /**
   * CharCard 角色卡
   *
   * 桌面：固定 240px
   * 移动：可折叠（默认展开）→ 100% 宽
   *
   * 数据来源：state.game.character + state.game.family + state.game.skills
   */
  import type { Character, FamilyMember, Skill } from '$lib/api/types';

  interface Props {
    character: Character;
    family?: FamilyMember[];
    skills?: Skill[];
    collapsible?: boolean;
  }

  let { character, family = [], skills = [], collapsible = true }: Props = $props();

  let expanded = $state(true);
</script>

<aside class="char-card" class:char-card-collapsed={collapsible && !expanded}>
  <header class="char-card-header">
    <div class="char-card-avatar" aria-hidden="true">👤</div>
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
    </div>
  {/if}
</aside>

<style>
  .char-card {
    display: flex;
    flex-direction: column;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-fold);
    overflow: hidden;
  }

  .char-card-header {
    padding: var(--space-5);
    text-align: center;
    background: linear-gradient(180deg, var(--color-paper-aged) 0%, var(--color-paper) 100%);
    border-bottom: 1px solid var(--color-ink-faint);
  }

  .char-card-avatar {
    font-size: var(--text-4xl);
    line-height: 1;
    margin-bottom: var(--space-2);
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
