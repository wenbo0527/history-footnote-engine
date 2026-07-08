<script lang="ts">
  /**
   * GameHeader - 游戏页顶部
   *
   * 显示：
   *   - 万历年号 + 角色名 + 城市
   *   - 时代进度条
   *   - 3 个 stats（💰 现金 / 🧵 织机 / ⭐ 声望）
   *   - GameToolbar（档案/回顾/词条/反馈/设置）
   */
  import type { GameState } from '$lib/api/types';
  import GameToolbar from './GameToolbar.svelte';

  interface Props {
    game: GameState;
    onwiki?: () => void;
    onrecap?: () => void;
    onglossary?: () => void;
    onfeedback?: () => void;
    onsettings?: () => void;
  }

  let { game, onwiki, onrecap, onglossary, onfeedback, onsettings }: Props = $props();

  // 派生
  const yearLabel = $derived(`万历${game.year_current - 1573}年（${game.year_current}）`);
  const yearMaxLabel = $derived(`万历${game.year_max - 1573}年（${game.year_max}）`);
  const progress = $derived(Math.min(100, ((game.year_current - 1587) / (game.year_max - 1587)) * 100));
</script>

<header class="game-header">
  <div class="game-header-info">
    <span class="game-header-emoji" aria-hidden="true">🎭</span>
    <div class="game-header-text">
      <h1 class="game-header-title">{yearLabel} → {yearMaxLabel}</h1>
      <p class="game-header-subtitle">
        第 {game.round_current} 回合 · {game.city} · {game.account_username}
      </p>
    </div>
  </div>

  <div class="game-header-progress">
    <div class="game-header-progress-label">时代进度 {progress.toFixed(0)}%</div>
    <div class="game-header-progress-bar">
      <div class="game-header-progress-fill" style="width: {progress}%"></div>
    </div>
  </div>

  <div class="game-header-stats">
    <!-- 🆕 行动点❤条：每月 3-4 个，让"过日子"可感知 -->
    <div
      class="game-header-action-points"
      title="本月剩余行动点（每月自动重置）"
    >
      {#each Array.from({ length: game.action_points_max }) as _, i (i)}
        {@const filled = i < game.action_points_current}
        <span
          class="game-header-ap"
          class:game-header-ap-filled={filled}
          aria-hidden="true"
        >❤</span>
      {/each}
      <span class="game-header-ap-label">
        {game.action_points_current}/{game.action_points_max}
      </span>
    </div>
    <div class="game-header-stat" title="银两">
      <span class="game-header-stat-icon">💰</span>
      <span class="game-header-stat-val">{game.cash.toFixed(2)}</span>
    </div>
    <div class="game-header-stat" title="织机">
      <span class="game-header-stat-icon">🧵</span>
      <span class="game-header-stat-val">{game.looms}</span>
    </div>
    <div class="game-header-stat" title="声望">
      <span class="game-header-stat-icon">⭐</span>
      <span class="game-header-stat-val">{game.reputation}</span>
    </div>
  </div>

  <GameToolbar
    {onwiki}
    {onrecap}
    {onglossary}
    {onfeedback}
    {onsettings}
  />
</header>

<style>
  .game-header {
    display: flex;
    align-items: center;
    gap: var(--space-5);
    padding: var(--space-4) var(--space-5);
    background: linear-gradient(135deg, var(--color-bronze-dark) 0%, var(--color-ink) 100%);
    color: var(--color-paper);
    flex-wrap: wrap;
  }

  .game-header-info {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    flex: 1 1 auto;
    min-width: 240px;
  }

  .game-header-emoji {
    font-size: var(--text-2xl);
    line-height: 1;
  }

  .game-header-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-paper);
    margin: 0;
    letter-spacing: var(--tracking-wide);
  }

  .game-header-subtitle {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-bronze-light);
    margin: 0;
    opacity: 0.9;
  }

  .game-header-progress {
    flex: 1 1 240px;
    min-width: 200px;
    max-width: 480px;
  }

  .game-header-progress-label {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-bronze-light);
    margin-bottom: var(--space-1);
    opacity: 0.9;
  }

  .game-header-progress-bar {
    height: 6px;
    background: rgba(245, 239, 225, 0.2);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .game-header-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--color-bronze-light), var(--color-paper));
    border-radius: var(--radius-full);
    transition: width var(--duration-slow) var(--ease-ink);
  }

  .game-header-stats {
    display: flex;
    gap: var(--space-2);
    flex: 0 0 auto;
    align-items: center;
  }

  /* 🆕 行动点❤条 */
  .game-header-action-points {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: var(--space-1) var(--space-2);
    background: rgba(165, 42, 42, 0.12);
    border: 1px solid rgba(165, 42, 42, 0.25);
    border-radius: var(--radius-sm);
    font-family: var(--font-numeric);
  }

  .game-header-ap {
    font-size: var(--text-sm);
    line-height: 1;
    color: rgba(245, 239, 225, 0.25);
    transition: color var(--duration-normal) var(--ease-ink),
                transform var(--duration-normal) var(--ease-ink);
  }

  .game-header-ap-filled {
    color: var(--color-cinnabar);
    text-shadow: 0 0 4px rgba(165, 42, 42, 0.4);
  }

  .game-header-ap-label {
    font-size: var(--text-xs);
    color: var(--color-paper);
    margin-left: var(--space-1);
    opacity: 0.85;
  }

  .game-header-stat {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-2);
    background: rgba(245, 239, 225, 0.1);
    border-radius: var(--radius-sm);
    border: 1px solid rgba(245, 239, 225, 0.15);
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-paper);
  }

  .game-header-stat-icon {
    font-size: var(--text-base);
  }

  /* 工具栏在 header 底部一行 */
  :global(.game-header > .game-toolbar) {
    flex: 1 0 100%;
    margin-top: var(--space-2);
  }

  /* 移动端：垂直堆叠 */
  @media (max-width: 767px) {
    .game-header {
      flex-direction: column;
      align-items: stretch;
      gap: var(--space-3);
      padding: var(--space-3);
    }
    .game-header-info {
      flex: 0 0 auto;
    }
    .game-header-progress {
      max-width: none;
    }
    .game-header-stats {
      justify-content: space-around;
    }
  }
</style>
