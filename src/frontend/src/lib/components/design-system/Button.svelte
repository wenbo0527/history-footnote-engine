<script lang="ts">
  /**
   * Button 基础按钮
   *
   * variant:
   *   - primary  古铜色（默认主按钮）
   *   - seal     朱砂印章（关键操作）
   *   - ghost    透明描边（次要操作）
   *   - subtle   米黄底色（最弱操作）
   *
   * size:
   *   - sm  32px
   *   - md  40px (默认)
   *   - lg  48px
   */
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  type Variant = 'primary' | 'seal' | 'ghost' | 'subtle';
  type Size = 'sm' | 'md' | 'lg';

  interface Props extends Omit<HTMLButtonAttributes, 'children'> {
    variant?: Variant;
    size?: Size;
    loading?: boolean;
    disabled?: boolean;
    children: Snippet;
  }

  let {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    children,
    type = 'button',
    ...rest
  }: Props = $props();
</script>

<button
  {type}
  class="btn"
  class:btn-primary={variant === 'primary'}
  class:btn-seal={variant === 'seal'}
  class:btn-ghost={variant === 'ghost'}
  class:btn-subtle={variant === 'subtle'}
  class:btn-sm={size === 'sm'}
  class:btn-md={size === 'md'}
  class:btn-lg={size === 'lg'}
  class:btn-loading={loading}
  disabled={disabled || loading}
  aria-busy={loading}
  {...rest}
>
  {#if loading}
    <span class="btn-spinner" aria-hidden="true"></span>
  {/if}
  <span class="btn-content" class:btn-content-loading={loading}>
    {@render children()}
  </span>
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    font-family: var(--font-display);
    font-weight: 500;
    border-radius: var(--radius-md);
    cursor: pointer;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
    transition:
      background-color var(--duration-normal) var(--ease-ink),
      border-color var(--duration-normal) var(--ease-ink),
      color var(--duration-normal) var(--ease-ink),
      transform var(--duration-quick) var(--ease-ink),
      box-shadow var(--duration-normal) var(--ease-ink);
    position: relative;
    overflow: hidden;
    white-space: nowrap;
  }

  /* Sizes */
  .btn-sm { padding: 0 var(--space-3); height: 32px; font-size: var(--text-sm); }
  .btn-md { padding: 0 var(--space-5); height: 40px; font-size: var(--text-base); }
  .btn-lg { padding: 0 var(--space-6); height: 48px; font-size: var(--text-md); }

  /* Primary: 古铜色 */
  .btn-primary {
    background: var(--color-bronze);
    color: var(--color-paper);
    border: 1px solid var(--color-bronze);
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--color-bronze-dark);
    border-color: var(--color-bronze-dark);
    box-shadow: var(--shadow-fold);
  }
  .btn-primary:active:not(:disabled) {
    transform: translateY(1px);
  }

  /* Seal: 朱砂印章（关键操作） */
  .btn-seal {
    background: var(--color-cinnabar);
    color: var(--color-paper);
    border: 1px solid var(--color-cinnabar);
    letter-spacing: var(--tracking-wide);
  }
  .btn-seal::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(
      circle at center,
      rgba(245, 239, 225, 0.15) 0%,
      transparent 60%
    );
    opacity: 0;
    transition: opacity var(--duration-normal) var(--ease-ink);
  }
  .btn-seal:hover:not(:disabled) {
    background: var(--color-cinnabar-dark);
    box-shadow: var(--shadow-ink);
  }
  .btn-seal:hover:not(:disabled)::before {
    opacity: 1;
  }
  .btn-seal:active:not(:disabled) {
    transform: translateY(1px);
  }

  /* Ghost: 透明描边（次要操作） */
  .btn-ghost {
    background: transparent;
    color: var(--color-ink);
    border: 1px solid var(--color-ink-faint);
  }
  .btn-ghost:hover:not(:disabled) {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
  }
  .btn-ghost:active:not(:disabled) {
    transform: translateY(1px);
  }

  /* Subtle: 米黄底色（最弱操作） */
  .btn-subtle {
    background: var(--color-paper-aged);
    color: var(--color-ink);
    border: 1px solid transparent;
  }
  .btn-subtle:hover:not(:disabled) {
    background: var(--color-paper-dark);
  }
  .btn-subtle:active:not(:disabled) {
    transform: translateY(1px);
  }

  /* Disabled */
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Loading */
  .btn-loading {
    pointer-events: none;
  }
  .btn-content-loading {
    opacity: 0.6;
  }
  .btn-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: btn-spin 0.8s linear infinite;
  }
  @keyframes btn-spin {
    to { transform: rotate(360deg); }
  }

  /* 触摸目标 (iOS) */
  @media (max-width: 767px) {
    .btn { min-height: 44px; }
  }
</style>
