<script lang="ts">
  /**
   * AppShell 顶层容器
   * - display: flex; flex-direction: column; height: 100dvh
   * - AppHeader (sticky top)
   * - AppMain (唯一滚动区, flex: 1 1 0)
   * - AppFooter (sticky bottom)
   */
  import type { Snippet } from 'svelte';

  interface Props {
    header?: Snippet;
    main?: Snippet;
    footer?: Snippet;
  }

  let { header, main, footer }: Props = $props();
</script>

<div class="app-shell">
  {#if header}
    <div class="app-shell-header">
      {@render header()}
    </div>
  {/if}

  <main class="app-shell-main">
    {#if main}
      {@render main()}
    {/if}
  </main>

  {#if footer}
    <div class="app-shell-footer">
      {@render footer()}
    </div>
  {/if}
</div>

<style>
  .app-shell {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    width: 100%;
    background: var(--color-paper);
    overflow: hidden;
  }

  .app-shell-header {
    flex: 0 0 auto;
    z-index: var(--z-sticky);
  }

  .app-shell-main {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    background: var(--color-paper);
    position: relative;
  }

  .app-shell-footer {
    flex: 0 0 auto;
    z-index: var(--z-sticky);
  }
</style>
