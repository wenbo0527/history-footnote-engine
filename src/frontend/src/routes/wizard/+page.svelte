<script lang="ts">
  /**
   * Wizard 页面 - 5 步角色创建
   * 朝代固定为万历
   */
  import { WizardShell } from '$lib/components/wizard';
  import { onMount } from 'svelte';
  import { wizard } from '$lib/stores';
  import { page } from '$app/stores';

  onMount(() => {
    // 进入 wizard 时重置
    wizard.reset();
    // 🆕 v2.10.22: 剧本模式标记 (来自 StartMenu 入口)
    const scripted = $page.url.searchParams.get('scripted') === '1';
    if (scripted) {
      // 可以存到 wizard state
      wizard.setScriptedMode?.(true);
      // 也存到 sessionStorage 给 /game 路由用
      try { sessionStorage.setItem('hfe_wizard_scripted', '1'); } catch {}
    } else {
      try { sessionStorage.removeItem('hfe_wizard_scripted'); } catch {}
    }
    // 调试用：URL ?step=N 跳到指定步骤
    const target = parseInt($page.url.searchParams.get('step') ?? '0', 10);
    if (target > 0) {
      wizard.goTo(target);
    }
  });
</script>

<svelte:head>
  <title>创建角色 · 历史注脚</title>
  <meta name="description" content="在万历年间，创建你的角色" />
</svelte:head>

<WizardShell />
