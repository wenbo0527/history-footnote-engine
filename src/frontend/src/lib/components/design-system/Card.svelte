<script lang="ts">
  /**
   * Card 卡片容器
   *
   * variant:
   *   - paper  宣纸色（默认）
   *   - aged   旧纸色（次要）
   *   - dark   古铜色（强调）
   *
   * 卡片是国风叙事的基础容器：宣纸色 + 1px 古铜边 + 极弱阴影
   */
  import type { Snippet } from 'svelte';

  type Variant = 'paper' | 'aged' | 'dark';

  interface Props {
    variant?: Variant;
    padding?: 'sm' | 'md' | 'lg' | 'none';
    bordered?: boolean;
    shadow?: 'none' | 'paper' | 'fold' | 'ink';
    children: Snippet;
  }

  let {
    variant = 'paper',
    padding = 'md',
    bordered = true,
    shadow = 'paper',
    children
  }: Props = $props();
</script>

<div
  class="card"
  class:card-paper={variant === 'paper'}
  class:card-aged={variant === 'aged'}
  class:card-dark={variant === 'dark'}
  class:card-pad-sm={padding === 'sm'}
  class:card-pad-md={padding === 'md'}
  class:card-pad-lg={padding === 'lg'}
  class:card-bordered={bordered}
  class:shadow-none={shadow === 'none'}
  class:shadow-paper={shadow === 'paper'}
  class:shadow-fold={shadow === 'fold'}
  class:shadow-ink={shadow === 'ink'}
>
  {@render children()}
</div>

<style>
  .card {
    border-radius: var(--radius-lg);
    transition: all var(--duration-normal) var(--ease-ink);
  }

  /* Variants */
  .card-paper { background: var(--color-paper); }
  .card-aged  { background: var(--color-paper-aged); }
  .card-dark  { background: var(--color-bronze-dark); color: var(--color-paper); }

  /* Border */
  .card-bordered { border: 1px solid var(--color-bronze); }
  .card-dark.card-bordered { border-color: var(--color-bronze-light); }

  /* Padding */
  .card-pad-sm { padding: var(--space-3); }
  .card-pad-md { padding: var(--space-5); }
  .card-pad-lg { padding: var(--space-6); }
  .card-pad-none { padding: 0; }

  /* Shadows */
  .shadow-none  { box-shadow: none; }
  .shadow-paper { box-shadow: var(--shadow-paper); }
  .shadow-fold  { box-shadow: var(--shadow-fold); }
  .shadow-ink   { box-shadow: var(--shadow-ink); }
</style>
