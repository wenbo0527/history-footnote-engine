<script lang="ts">
  /**
   * 根布局 - 加载全局样式 + AppShell
   *
   * 🆕 v2.7+ 路由级卷轴展开转场：
   * - pathname 变化时，外层 page-transition 触发 scrollUnfurl 动画
   * - 走 CSS keyframes（性能开销小，GPU 加速）
   * - prefers-reduced-motion 下完全禁用
   */
  import '$lib/styles/index.css';
  import { AppShell } from '$lib/components/layout';
  import { SkipLink } from '$lib/components/design-system';
  import InkBurst from '$lib/components/effects/InkBurst.svelte';
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
    <div id="main-content" class="page-transition" data-pathname={$page.url.pathname}>
      {@render children()}
    </div>
  {/snippet}
</AppShell>

<!-- 🆕 v2.7+ 全局墨滴点击反馈（Canvas 2D） -->
<InkBurst />

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
