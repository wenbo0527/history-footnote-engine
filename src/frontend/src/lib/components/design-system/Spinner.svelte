<script lang="ts">
  /**
   * Spinner 笔触动画
   *
   * 不是传统的圆环旋转，而是 SVG 笔触动画
   * 体现"提笔中..."的国风感
   *
   * mode:
   *   - brush  笔触往返（默认，慢节奏 1.2s）
   *   - circle 圆环旋转（传统 0.8s）
   */
  interface Props {
    size?: number;
    mode?: 'brush' | 'circle';
    label?: string;
  }

  let { size = 32, mode = 'brush', label = '加载中' }: Props = $props();
</script>

<div
  class="spinner"
  class:spinner-brush={mode === 'brush'}
  class:spinner-circle={mode === 'circle'}
  style="--spinner-size: {size}px"
  role="status"
  aria-label={label}
>
  {#if mode === 'brush'}
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
      <!-- 笔触动画：从左到右来回 -->
      <line
        x1="10"
        y1="50"
        x2="90"
        y2="50"
        stroke="currentColor"
        stroke-width="3"
        stroke-linecap="round"
        class="brush-line"
      />
      <circle cx="50" cy="50" r="4" class="brush-dot" />
    </svg>
  {:else}
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
      <circle
        cx="50"
        cy="50"
        r="40"
        fill="none"
        stroke="currentColor"
        stroke-width="6"
        stroke-linecap="round"
        stroke-dasharray="60 200"
        class="circle-arc"
      />
    </svg>
  {/if}
  <span class="sr-only">{label}</span>
</div>

<style>
  .spinner {
    display: inline-flex;
    color: var(--color-bronze);
  }

  /* Brush 模式：笔触往返 */
  .brush-line {
    stroke-dasharray: 80 80;
    stroke-dashoffset: 0;
    animation: brush-stroke 1.4s var(--ease-ink) infinite;
  }
  .brush-dot {
    fill: currentColor;
    animation: brush-dot-move 1.4s var(--ease-ink) infinite;
  }
  @keyframes brush-stroke {
    0%   { stroke-dashoffset: 80; opacity: 0.4; }
    50%  { stroke-dashoffset: 0;  opacity: 1; }
    100% { stroke-dashoffset: -80; opacity: 0.4; }
  }
  @keyframes brush-dot-move {
    0%   { transform: translateX(-40px); opacity: 0.6; }
    50%  { transform: translateX(0);     opacity: 1; }
    100% { transform: translateX(40px);  opacity: 0.6; }
  }

  /* Circle 模式：传统旋转 */
  .circle-arc {
    transform-origin: center;
    animation: circle-spin 0.9s linear infinite;
  }
  @keyframes circle-spin {
    to { transform: rotate(360deg); }
  }

  /* Screen reader only */
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
