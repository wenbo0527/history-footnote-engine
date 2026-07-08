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
