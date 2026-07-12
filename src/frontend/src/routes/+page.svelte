<script lang="ts">
  /**
   * 首页 - 默认强制登录（v2.10.1+）
   *
   * 🆕 v2.10.1 W67: 强制登录体验
   * - 默认 → 跳 /login?next=/（必须登录/访客/注册）
   * - 已登录 → 直接显示 StartMenu
   * - ?skip_login=1 → 调试用（跳过）
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { StartMenu } from '$lib/components/home';
  import { isLoggedIn } from '$lib/api/account';
  import { Spinner } from '$lib/components/design-system';

  let checking = $state(true);

  onMount(() => {
    // 调试用：?skip_login=1 → 跳过登录检查
    if ($page.url.searchParams.get('skip_login') === '1') {
      checking = false;
      return;
    }

    // 已登录 → 直接进 StartMenu
    if (isLoggedIn()) {
      checking = false;
      return;
    }

    // 默认：未登录 → 强制跳登录页（访客/注册入口都在 /login）
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
