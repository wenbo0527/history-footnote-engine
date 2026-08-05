<script lang="ts">
  /**
   * 首页 - StartMenu (🆕 v2.10.33 D1.1: 取消强制跳登录)
   *
   * 历史：v2.10.1 W67 强制跳 /login (访客也必须走登录页)
   * 现在：直接显示 StartMenu (游客/登录/注册入口都在 StartMenu 内)
   *
   * 旧 ?skip_login=1 调试 flag 仍保留兼容
   */
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { StartMenu } from '$lib/components/home';
  import { Spinner } from '$lib/components/design-system';

  let checking = $state(true);

  onMount(() => {
    // 调试用：?skip_login=1 仍支持
    if ($page.url.searchParams.get('skip_login') === '1') {
      checking = false;
      return;
    }
    // 🆕 v2.10.33 D1.1: 不再强制跳 /login，访客也能看 StartMenu
    checking = false;
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
