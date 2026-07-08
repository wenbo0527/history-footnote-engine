<script lang="ts">
  /**
   * Seal 朱砂印章
   *
   * 国风特有：朱砂色 + 方正字 + 印泥效果
   * 用于关键操作按钮（提交、确认、决定）
   *
   * 印章的"按压感"：hover 时微微下压，active 时印泥扩散
   */
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends Omit<HTMLButtonAttributes, 'children'> {
    text: string;        // 印章文字
    size?: 'sm' | 'md' | 'lg';
    ink?: 'fresh' | 'aged';  // fresh 朱砂鲜亮，aged 朱砂褪色
    pulse?: boolean;     // 印泥脉冲动画
    children?: Snippet;  // 可选图标
  }

  let {
    text,
    size = 'md',
    ink = 'fresh',
    pulse = false,
    children,
    type = 'button',
    ...rest
  }: Props = $props();
</script>

<button
  {type}
  class="seal"
  class:seal-sm={size === 'sm'}
  class:seal-md={size === 'md'}
  class:seal-lg={size === 'lg'}
  class:seal-fresh={ink === 'fresh'}
  class:seal-aged={ink === 'aged'}
  class:seal-pulse={pulse}
  {...rest}
>
  <span class="seal-text">{text}</span>
  {#if children}
    <span class="seal-icon">{@render children()}</span>
  {/if}
  <span class="seal-edge" aria-hidden="true"></span>
</button>

<style>
  .seal {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    font-family: var(--font-display);
    font-weight: 700;
    color: var(--color-paper);
    background: var(--color-cinnabar);
    border: 2px solid var(--color-cinnabar);
    border-radius: var(--radius-sm);
    letter-spacing: var(--tracking-wide);
    cursor: pointer;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
    overflow: hidden;
    transition:
      background-color var(--duration-normal) var(--ease-ink),
      transform var(--duration-quick) var(--ease-ink),
      box-shadow var(--duration-normal) var(--ease-ink);
    box-shadow:
      inset 0 0 0 1px rgba(245, 239, 225, 0.15),
      0 1px 2px rgba(122, 31, 31, 0.3);
  }

  /* 印泥纹理 */
  .seal::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      radial-gradient(circle at 30% 20%, rgba(245, 239, 225, 0.1) 0%, transparent 30%),
      radial-gradient(circle at 70% 80%, rgba(122, 31, 31, 0.2) 0%, transparent 40%);
    pointer-events: none;
  }

  /* 边角磨损 */
  .seal-edge {
    position: absolute;
    inset: 0;
    pointer-events: none;
    box-shadow: inset 0 0 8px rgba(122, 31, 31, 0.4);
  }

  /* Sizes */
  .seal-sm { padding: var(--space-1) var(--space-3); font-size: var(--text-xs); }
  .seal-md { padding: var(--space-2) var(--space-5); font-size: var(--text-sm); }
  .seal-lg { padding: var(--space-3) var(--space-6); font-size: var(--text-base); }

  /* Aged: 褪色印章 */
  .seal-aged {
    background: #8b2828;
    border-color: #6b2020;
    color: rgba(245, 239, 225, 0.85);
  }

  /* Hover: 微微下压 */
  .seal:hover:not(:disabled) {
    transform: translateY(1px);
    box-shadow:
      inset 0 0 0 1px rgba(245, 239, 225, 0.2),
      0 1px 1px rgba(122, 31, 31, 0.4);
  }

  /* Active: 印泥扩散 */
  .seal:active:not(:disabled) {
    transform: translateY(2px);
    box-shadow:
      inset 0 0 0 1px rgba(245, 239, 225, 0.3),
      inset 0 0 12px rgba(122, 31, 31, 0.6);
  }

  /* Pulse: 印泥脉冲 */
  .seal-pulse::after {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(
      circle at center,
      rgba(245, 239, 225, 0.3) 0%,
      transparent 60%
    );
    animation: seal-pulse 2s var(--ease-ink) infinite;
  }
  @keyframes seal-pulse {
    0%   { opacity: 0; transform: scale(0.95); }
    50%  { opacity: 1; transform: scale(1); }
    100% { opacity: 0; transform: scale(1.05); }
  }

  .seal:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .seal-text {
    position: relative;
    z-index: 1;
  }

  .seal-icon {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
  }
</style>
