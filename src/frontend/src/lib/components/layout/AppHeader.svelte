<script lang="ts">
  /**
   * AppHeader - 顶部导航
   *
   * variant:
   *   - home   首页（极简，仅 logo + 关于）
   *   - game   游戏页（万历年号 + 进度条 + stats）
   *   - wizard 角色创建（步骤进度）
   */
  import { page } from '$app/stores';
  import { session } from '$lib/stores';
  // 🆕 v2.10.2: 银钱单位统一
  import { toCompactLiang } from '$lib/utils/currency';

  type Variant = 'home' | 'game' | 'wizard';

  interface Props {
    variant?: Variant;
    title?: string;
    subtitle?: string;
    progress?: number;            // 0-100
    stats?: { cash: number; looms: number; reputation: number };
  }

  let { variant = 'home', title, subtitle, progress = 0, stats }: Props = $props();
</script>

<header class="app-header" data-variant={variant}>
  <div class="app-header-brand">
    <a href="/" class="app-header-logo">
      <img src="/icons/nav/home.webp" alt="" class="app-header-emoji" />
      <span class="app-header-name">历史注脚</span>
    </a>
  </div>

  {#if variant === 'game' && title}
    <div class="app-header-game">
      <h1 class="app-header-title">{title}</h1>
      {#if subtitle}
        <p class="app-header-subtitle">{subtitle}</p>
      {/if}
    </div>

    {#if progress !== undefined}
      <div class="app-header-progress">
        <div class="app-header-progress-label">时代进度 {Math.round(progress)}%</div>
        <div class="app-header-progress-bar">
          <div class="app-header-progress-fill" style="width: {progress}%"></div>
        </div>
      </div>
    {/if}

    {#if stats}
      <div class="app-header-stats">
        <span class="app-header-stat" title="现金">
          <img src="/icons/stats/cash.webp" alt="" class="app-header-stat-icon" />
          {toCompactLiang(stats.cash)}
        </span>
        <span class="app-header-stat" title="织机">
          <img src="/icons/stats/loom.webp" alt="" class="app-header-stat-icon" />
          {stats.looms}
        </span>
        <span class="app-header-stat" title="声望">
          <img src="/icons/stats/reputation.webp" alt="" class="app-header-stat-icon" />
          {stats.reputation}
        </span>
      </div>
    {/if}
  {/if}

  <div class="app-header-user">
    {#if $session.isLoggedIn}
      <span class="app-header-username">{$session.username}</span>
    {/if}
  </div>
</header>

<style>
  .app-header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-3) var(--space-5);
    padding-top: max(var(--space-3), env(safe-area-inset-top));
    background: linear-gradient(135deg, var(--color-bronze-dark) 0%, var(--color-ink) 100%);
    color: var(--color-paper);
    flex-wrap: wrap;
    min-height: 56px;
  }

  .app-header-brand {
    flex: 0 0 auto;
  }

  .app-header-stat-icon {
    width: 1.2em;
    height: 1.2em;
    object-fit: contain;
    vertical-align: middle;
    margin-right: 0.2em;
  }

  .app-header-logo {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--color-paper);
    text-decoration: none;
    font-family: var(--font-display);
    transition: color var(--duration-normal) var(--ease-ink);
  }
  .app-header-logo:hover { color: var(--color-bronze-light); }

  .app-header-emoji {
    width: 1.4em;
    height: 1.4em;
    object-fit: contain;
  }

  .app-header-name {
    font-size: var(--text-base);
    font-weight: 600;
    letter-spacing: var(--tracking-wide);
  }

  /* Game variant */
  .app-header-game {
    flex: 1 1 auto;
    min-width: 200px;
  }

  .app-header-title {
    font-family: var(--font-display);
    font-size: var(--text-base);
    font-weight: 600;
    color: var(--color-paper);
    margin: 0;
  }

  .app-header-subtitle {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-bronze-light);
    margin: 0;
    opacity: 0.9;
  }

  .app-header-progress {
    flex: 1 1 220px;
    min-width: 180px;
    max-width: 480px;
  }

  .app-header-progress-label {
    font-size: var(--text-xs);
    color: var(--color-bronze-light);
    margin-bottom: var(--space-1);
    opacity: 0.9;
  }

  .app-header-progress-bar {
    height: 6px;
    background: rgba(245, 239, 225, 0.2);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .app-header-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--color-bronze-light), var(--color-paper));
    border-radius: var(--radius-full);
    transition: width var(--duration-slow) var(--ease-ink);
  }

  .app-header-stats {
    display: flex;
    gap: var(--space-3);
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
  }

  .app-header-stat {
    padding: var(--space-1) var(--space-2);
    background: rgba(245, 239, 225, 0.1);
    border-radius: var(--radius-sm);
    border: 1px solid rgba(245, 239, 225, 0.15);
  }

  .app-header-user {
    flex: 0 0 auto;
    margin-left: auto;
  }

  .app-header-username {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-bronze-light);
  }

  /* 移动端 */
  @media (max-width: 767px) {
    .app-header {
      padding: var(--space-2) var(--space-3);
      gap: var(--space-2);
    }
    .app-header-game {
      flex: 1 1 100%;
      order: 2;
    }
    .app-header-progress {
      flex: 1 1 100%;
      order: 3;
      max-width: none;
    }
    .app-header-stats {
      order: 4;
    }
  }
</style>
