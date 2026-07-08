<script lang="ts">
  /**
   * AppMain - 唯一滚动区
   * 桌面：max-width 居中
   * 移动：100% 视口
   */
  import type { Snippet } from 'svelte';

  interface Props {
    children: Snippet;
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  }

  let { children, maxWidth = 'full' }: Props = $props();
</script>

<main class="app-main" data-max={maxWidth}>
  {@render children()}
</main>

<style>
  .app-main {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    background: var(--color-paper);
    position: relative;
  }

  .app-main[data-max='sm'] > :global(*) { max-width: 640px; margin-inline: auto; }
  .app-main[data-max='md'] > :global(*) { max-width: 768px; margin-inline: auto; }
  .app-main[data-max='lg'] > :global(*) { max-width: 1024px; margin-inline: auto; }
  .app-main[data-max='xl'] > :global(*) { max-width: 1280px; margin-inline: auto; }
  .app-main[data-max='full'] > :global(*) { max-width: 100%; }

  /* 滚动条样式（webikit） */
  .app-main::-webkit-scrollbar {
    width: 8px;
  }
  .app-main::-webkit-scrollbar-track {
    background: var(--color-paper-aged);
  }
  .app-main::-webkit-scrollbar-thumb {
    background: var(--color-bronze);
    border-radius: var(--radius-full);
  }
  .app-main::-webkit-scrollbar-thumb:hover {
    background: var(--color-bronze-dark);
  }
</style>
