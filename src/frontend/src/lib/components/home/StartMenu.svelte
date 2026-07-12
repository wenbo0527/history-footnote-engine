<script lang="ts">
  /**
   * StartMenu 首页（v1.7.30 桌面端优化）
   *
   * 布局：
   *   桌面（≥1024px）：左 1 列（开始/设置/账户）+ 右大块（我的存档 可滚动）
   *   移动（<1024px）：单列堆叠
   *
   * 🆕 v1.7.30:
   *   - 桌面 2 列布局（之前只 1 列）
   *   - 真实账户信息（从 localStorage 读 + 显示）
   *   - 真实存档列表（接真后端）
   */
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { Chapter, Divider, Button, Seal, Spinner, toast } from '$lib/components/design-system';
  import { session, sessionActions } from '$lib/stores';
  import { listArchives } from '$lib/api/archives';
  import { getCurrentUsername, getCurrentAccountId, logout, getAccountInfo, isLoggedIn, isGuest, ensureGuestAccountId } from '$lib/api/account';
  import type { Archive } from '$lib/api/types';
  import StartMenuCard from './StartMenuCard.svelte';
  import ArchiveList from './ArchiveList.svelte';

  // 🆕 v2.10.2 fix: listArchives 返回 ArchivesResponse 包含 sessions（Archive[] 数组）
  // 用 any[] 兜底避免类型不匹配（原 ArchiveSession 类型不存在）
  let archives = $state<any[]>([]);
  let loadingArchives = $state(false);
  let accountUsername = $state<string | null>(null);
  let currentAccountId = $state<string | null>(null);
  // 🆕 v2.10.1 W68: "入局" 过渡状态（点击后显示 loading overlay）
  let enteringWizard = $state(false);

  onMount(async () => {
    // 🆕 v2.7+: 游客也要拿真 guest_id（首页已兜底一次，这里再保险）
    if (!currentAccountId && isGuest()) {
      try { await ensureGuestAccountId(); } catch { /* 静默 */ }
    }
    accountUsername = getCurrentUsername();
    currentAccountId = getCurrentAccountId();

    // 拉取账户真实信息
    if (currentAccountId) {
      try {
        const info = await getAccountInfo(currentAccountId);
        if (info?.username) {
          accountUsername = info.username;
        }
      } catch (e) {
        // 静默
      }
    }

    await loadArchives();
  });

  async function loadArchives() {
    loadingArchives = true;
    try {
      // 🆕 v2.7+: 已登录/游客都用真 account_id 拉取，不再回退到 'default'
      // （首页已保证游客有 guest_id；若仍为空表示后端不可用 → 返回空列表）
      const accountId = currentAccountId ?? '';
      // 🆕 v2.10.1 fix: listArchives 返回 {count, sessions}，不是数组
      const response = await listArchives(accountId);
      archives = response.sessions;
    } catch (e) {
      archives = [];
    } finally {
      loadingArchives = false;
    }
  }

  function handleLoadArchive(sessionId: string) {
    goto(`/game?session=${sessionId}`);
  }

  function handleLogout() {
    logout();
    accountUsername = null;
    toast.success('已登出');
  }

  // 🆕 v2.7+: 游客模式点"登录/注册"时不丢本地存档
  function handleGoLogin() {
    // 保留 SESSION_KEY（游客 ID）和 GUEST_KEY，等注册成功后由后端迁移
    goto('/login');
  }

  // 🆕 v2.10.1 W68: "入局" 点击 → 200ms 视觉反馈 → 跳 /wizard
  // 目的：避免点击"无响应"的疑惑（实际 goto() 是即时但用户感知延迟）
  function handleEnter() {
    enteringWizard = true;
    setTimeout(() => {
      goto('/wizard');
      // 兜底：万一 goto 失败，1.5s 后恢复
      setTimeout(() => { enteringWizard = false; }, 1500);
    }, 200);
  }
</script>

<article class="start-menu">
  <header class="start-menu-header">
    <Chapter title="入 局" level={1} />
    <p class="start-menu-subtitle">历史注脚 · AI 驱动的明朝万历年间生存模拟</p>
  </header>

  <Divider variant="brush" spacing="md" />

  <!-- 🆕 v2.10.1 W68: 入局过渡遮罩 -->
  {#if enteringWizard}
    <div class="start-menu-transition" role="status" aria-live="polite">
      <div class="start-menu-transition-card">
        <Spinner mode="brush" size={56} />
        <p class="start-menu-transition-title">即将入局</p>
        <p class="start-menu-transition-subtitle">AI 正在为你翻开万历十五年的篇章...</p>
      </div>
    </div>
  {/if}

  <div class="start-menu-grid">
    <!-- 左侧 1 列：开始新游戏 / 设置 / 账户 -->
    <aside class="start-menu-left">
      <!-- 开始新游戏 -->
      <StartMenuCard
        iconSrc="/icons/nav/home.webp"
        title="开始新游戏"
        description="选择一个朝代，创建你的角色，开启一段历史注脚"
        primary
      >
        {#snippet action()}
          <Seal text="入 局" size="md" disabled={enteringWizard} onclick={handleEnter} />
        {/snippet}
      </StartMenuCard>

      <!-- 我的账户 -->
      <StartMenuCard
        iconSrc="/icons/nav/choice.webp"
        title="我的账户"
      >
        {#snippet description()}
          {#if accountUsername}
            当前: <strong>{accountUsername}</strong>
            <br />
            <span class="start-menu-card-hint">已登录，云端存档</span>
          {:else}
            访客模式（本地存档）
            <br />
            <span class="start-menu-card-hint">登录后可同步存档</span>
          {/if}
        {/snippet}
        {#snippet action()}
          {#if accountUsername}
            <Button variant="ghost" size="sm" onclick={handleLogout} fullWidth>登 出</Button>
          {:else}
            <Button variant="primary" size="sm" onclick={handleGoLogin} fullWidth>登录 / 注册</Button>
          {/if}
        {/snippet}
      </StartMenuCard>

      <!-- 系统设置 -->
      <StartMenuCard
        iconEmoji="⚙️"
        title="系统设置"
        description="主题、字号、提示音、动画"
      >
        {#snippet action()}
          <Button variant="ghost" size="sm" disabled fullWidth>即将开放</Button>
        {/snippet}
      </StartMenuCard>
    </aside>

    <!-- 右侧：我的存档（大块可滚动）-->
    <section class="start-menu-right">
      <div class="start-menu-archive-header">
        <h2 class="start-menu-archive-title">📦 我的存档</h2>
        <Button
          variant="ghost"
          size="sm"
          onclick={loadArchives}
          disabled={loadingArchives}
        >
          {loadingArchives ? '加载中...' : '刷新'}
        </Button>
      </div>

      {#if loadingArchives && archives.length === 0}
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
        <ArchiveList
          archives={archives}
          loading={loadingArchives}
          accountUsername={accountUsername}
          onload={handleLoadArchive}
        />
      {/if}
    </section>
  </div>
</article>

<style>
  .start-menu {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-5) var(--space-4);
    width: 100%;
    margin: 0 auto;
    max-width: 1280px;  /* 🆕 桌面 1280 撑开 */
  }

  .start-menu-header {
    text-align: center;
  }

  .start-menu-subtitle {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0;
  }

  .start-menu-grid {
    display: grid;
    grid-template-columns: 1fr;       /* 移动：1 列 */
    gap: var(--space-4);
    width: 100%;
  }

  /* 🆕 v2.10.1 W68: 入局过渡遮罩 */
  .start-menu-transition {
    position: fixed;
    inset: 0;
    background: rgba(245, 240, 225, 0.92);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    animation: fadeIn 200ms ease-out;
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .start-menu-transition-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-5) var(--space-6);
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(143, 75, 40, 0.2);
    border-radius: var(--radius-md, 8px);
    box-shadow: 0 8px 32px rgba(143, 75, 40, 0.15);
    min-width: 280px;
  }
  .start-menu-transition-title {
    margin: 0;
    font-family: var(--font-heading);
    font-size: var(--text-xl, 18px);
    color: var(--color-bronze-dark, #5a3a25);
    font-weight: 600;
  }
  .start-menu-transition-subtitle {
    margin: 0;
    font-size: var(--text-sm, 12px);
    color: var(--color-ink-light, #6a5a4a);
    text-align: center;
    max-width: 240px;
  }

  @media (min-width: 1024px) {
    .start-menu-grid {
      grid-template-columns: 380px 1fr;   /* 桌面：左 380 + 右 1fr */
      gap: var(--space-5);
    }
  }

  .start-menu-left {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .start-menu-right {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    min-height: 480px;
  }

  /* 卡片样式（左侧）*/
  .start-menu-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-4);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-fold);
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .start-menu-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-rise);
  }

  .start-menu-card-primary {
    background: linear-gradient(135deg, var(--color-paper) 0%, var(--color-paper-aged) 100%);
    border-color: var(--color-cinnabar);
  }

  .start-menu-card-icon {
    font-size: 2rem;
    line-height: 1;
  }

  .start-menu-card-title {
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0;
    text-align: center;
  }

  .start-menu-card-desc {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    margin: 0;
    text-align: center;
    line-height: var(--leading-snug);
  }

  .start-menu-card-hint {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }

  .start-menu-card-action {
    width: 100%;
    margin-top: var(--space-1);
  }

  /* 存档区（右侧）*/
  .start-menu-archive-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: var(--space-2);
    border-bottom: 1px solid var(--color-ink-faint);
  }

  .start-menu-archive-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0;
  }

  .start-menu-archive-count {
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0 0 var(--space-2);
  }

  .start-menu-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-7);
    color: var(--color-ink-light);
  }

  .start-menu-archive-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-7);
    text-align: center;
  }

  .start-menu-archive-empty-icon {
    font-size: 3rem;
    opacity: 0.4;
  }

  .start-menu-archive-empty-title {
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink-light);
    margin: 0;
  }

  .start-menu-archive-empty-desc {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-faint);
    line-height: var(--leading-relaxed);
    margin: 0;
    max-width: 360px;
  }

  .start-menu-archive-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    max-height: 600px;
    overflow-y: auto;
  }

  .start-menu-archive-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    width: 100%;
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
    text-align: left;
  }
  .start-menu-archive-item:hover {
    background: var(--color-paper-aged);
    border-left-color: var(--color-cinnabar);
    transform: translateX(2px);
  }

  .start-menu-archive-icon {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-cinnabar);
    color: var(--color-paper);
    font-family: var(--font-display);
    font-weight: 700;
    font-size: var(--text-md);
    border-radius: var(--radius-sm);
  }

  .start-menu-archive-info {
    flex: 1 1 0;
    min-width: 0;
  }

  .start-menu-archive-line1 {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink);
    font-weight: 600;
  }

  .start-menu-archive-era {
    color: var(--color-cinnabar);
  }

  .start-menu-archive-round {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    font-weight: 400;
  }

  .start-menu-archive-line2 {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    margin-top: 2px;
  }

  .start-menu-archive-line3 {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    margin-top: 2px;
  }

  .start-menu-archive-arrow {
    color: var(--color-bronze-dark);
    font-size: var(--text-lg);
    flex-shrink: 0;
  }
</style>
