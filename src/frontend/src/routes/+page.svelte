<script lang="ts">
  /**
   * 首页 - StartMenu 入口
   *
   * 🆕 v1.7.30: 可选登录
   * - 已登录 → 直接显示 StartMenu
   * - 未登录 → 跳 /login（但 URL 参数 ?skip_login=1 可跳过）
   * - 访客模式：未登录也能进首页（localStorage 存访客标记）
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { StartMenu } from '$lib/components/home';
  import { isLoggedIn, isGuest, setGuest, ensureGuestAccountId } from '$lib/api/account';
  import { Spinner } from '$lib/components/design-system';

  let checking = $state(true);

  onMount(async () => {
    // URL 参数 ?skip_login=1 → 直接进首页（调试用）
    if ($page.url.searchParams.get('skip_login') === '1') {
      // 🆕 v2.7+ 即使跳过登录也要给一个 guest_id，否则 StartMenu 拉不到存档
      try { await ensureGuestAccountId(); } catch { /* 静默 */ }
      checking = false;
      return;
    }

    if (isLoggedIn()) {
      checking = false;
      return;
    }

    // 访客模式：localStorage 标记（用户在 /login 点"以访客身份进入"）
    if (isGuest()) {
      // 🆕 v2.7+ 兜底：保证 guest_id 存在（之前可能因网络失败没拿到）
      try { await ensureGuestAccountId(); } catch { /* 静默 */ }
      checking = false;
      return;
    }

    // 第一次来 → 跳登录页（?next=/）
    goto('/login?next=/');
  });
</script>

<svelte:head>
  <title>万历十五年 · 历史注脚</title>
  <meta name="description" content="AI 驱动的明朝万历年间生存模拟" />
</svelte:head>

{#if checking}
  <div class="home-loading">
    <Spinner mode="brush" size={48} />
    <p>正在准备万历年...</p>
  </div>
{:else}
  <StartMenu />
{/if}

<style>
  .home-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    height: 100%;
    color: var(--color-ink-light);
  }
</style>
