<script lang="ts">
  /**
   * Seal 朱砂印章
   *
   * 🆕 v2.7+ 国风升级：
   * - 残缺纹理：SVG feTurbulence + feDisplacementMap 制造破边
   * - 盖落动画：active 时 scale(0.96) + 旋转，松开回弹
   * - 旋转默认 -3deg：模拟手工盖落的歪斜
   * - 印泥脉冲（pulse）：呼吸式外发光
   *
   * 国风特有：朱砂色 + 方正字 + 印泥效果
   * 用于关键操作按钮（提交、确认、决定）
   */
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends Omit<HTMLButtonAttributes, 'children'> {
    text: string;        // 印章文字
    size?: 'sm' | 'md' | 'lg';
    ink?: 'fresh' | 'aged';  // fresh 朱砂鲜亮，aged 朱砂褪色
    pulse?: boolean;     // 印泥脉冲动画
    rotate?: number;     // 旋转角度（默认 -3deg 模拟手工）
    children?: Snippet;  // 可选图标
  }

  let {
    text,
    size = 'md',
    ink = 'fresh',
    pulse = false,
    rotate = -3,
    children,
    type = 'button',
    ...rest
  }: Props = $props();

  // 唯一 filter id（避免 SVG 滤镜冲突）
  const FILTER_ID = `seal-rough-${Math.random().toString(36).slice(2, 9)}`;
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
  style="--seal-rotate: {rotate}deg"
  {...rest}
>
  <span class="seal-text">{text}</span>
  {#if children}
    <span class="seal-icon">{@render children()}</span>
  {/if}
  <!-- 🆕 v2.7+ 残缺纹理层（SVG） -->
  <svg class="seal-rough" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <filter id={FILTER_ID}>
        <feTurbulence baseFrequency="0.04" numOctaves="2" seed="3"/>
        <feDisplacementMap in="SourceGraphic" scale="3"/>
      </filter>
    </defs>
    <rect x="0" y="0" width="100" height="100"
          fill="none" stroke="currentColor" stroke-width="0.6"
          filter="url(#{FILTER_ID})" opacity="0.4"/>
  </svg>
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
    /* 🆕 v2.7+ 旋转 + 缩放过渡（盖落感） */
    transform: rotate(var(--seal-rotate, -3deg));
    transition:
      background-color var(--duration-normal) var(--ease-ink),
      transform 200ms cubic-bezier(0.7, 0, 0.3, 1),
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

  /* 🆕 v2.7+ 残缺纹理层：覆盖整个按钮，制造破边 */
  .seal-rough {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    color: var(--color-cinnabar-dark);
    pointer-events: none;
    mix-blend-mode: multiply;
  }

  /* 边角磨损（保留原效果） */
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

  /* 🆕 v2.7+ Hover: 微微缩放 + 旋转角度不变（印章抬起） */
  .seal:hover:not(:disabled) {
    transform: rotate(var(--seal-rotate, -3deg)) scale(1.03);
    box-shadow:
      inset 0 0 0 1px rgba(245, 239, 225, 0.2),
      0 2px 4px rgba(122, 31, 31, 0.4);
  }

  /* 🆕 v2.7+ Active: 盖落（缩 + 轻旋），配合 100ms 短促过渡 */
  .seal:active:not(:disabled) {
    transform: rotate(calc(var(--seal-rotate, -3deg) + 1deg)) scale(0.96);
    transition-duration: 100ms;
    box-shadow:
      inset 0 0 0 1px rgba(245, 239, 225, 0.3),
      inset 0 0 12px rgba(122, 31, 31, 0.6);
  }

  /* Pulse: 印泥脉冲（用 aesthetic.css 的 sealPulse） */
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
