<script lang="ts">
  /**
   * 根布局 - 加载全局样式 + AppShell
   */
  import '$lib/styles/index.css';
  import { AppShell } from '$lib/components/layout';
  import { SkipLink } from '$lib/components/design-system';
  import { page } from '$app/stores';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();

  $effect(() => {
    if (typeof document !== 'undefined') {
      const _ = $page.url.pathname;
      document.querySelector('.app-main')?.scrollTo?.(0, 0);
    }
  });
</script>

<SkipLink />
<AppShell>
  {#snippet main()}
    <div id="main-content">
      {@render children()}
    </div>
  {/snippet}
</AppShell>

<style>
  #main-content {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  :global(input[type='text']),
  :global(input[type='number']),
  :global(textarea) {
    font-size: 16px;
  }
</style>
