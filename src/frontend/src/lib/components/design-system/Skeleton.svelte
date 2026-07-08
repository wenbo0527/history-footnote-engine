<script lang="ts">
  /**
   * Skeleton - 骨架屏
   *
   * 加载占位（宣纸色渐变）
   * 用途：API 加载时显示骨架，避免空白闪烁
   */
  interface Props {
    width?: string;
    height?: string;
    rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full';
    block?: boolean;
  }

  let { width = '100%', height = '1em', rounded = 'sm', block = false }: Props = $props();
</script>

<span
  class="skeleton"
  class:skeleton-rounded-sm={rounded === 'sm'}
  class:skeleton-rounded-md={rounded === 'md'}
  class:skeleton-rounded-lg={rounded === 'lg'}
  class:skeleton-rounded-full={rounded === 'full'}
  class:skeleton-block={block}
  style="width: {width}; height: {height};"
  aria-hidden="true"
></span>

<style>
  .skeleton {
    display: inline-block;
    background: linear-gradient(
      90deg,
      var(--color-paper-aged) 0%,
      var(--color-paper-dark) 50%,
      var(--color-paper-aged) 100%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s var(--ease-ink) infinite;
  }

  .skeleton-block {
    display: block;
    width: 100%;
  }

  .skeleton-rounded-sm { border-radius: var(--radius-sm); }
  .skeleton-rounded-md { border-radius: var(--radius-md); }
  .skeleton-rounded-lg { border-radius: var(--radius-lg); }
  .skeleton-rounded-full { border-radius: var(--radius-full); }

  @keyframes skeleton-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
</style>
