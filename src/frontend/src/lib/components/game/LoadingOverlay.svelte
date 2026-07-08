<!--
  LoadingOverlay - DM 思考中的等待覆盖层

  🆕 v1.7.32: LLM 推理 1-2 分钟，玩家需要"可见"的等待：
    - 进度条（呼吸式，慢节奏）表示"正在工作"
    - 旋转展示加载提示（每 4 秒切一条，fade in/out）
    - 国风：卷草纹标题 + 宣纸色

  设计理念：
    - 不要技术化百分比（不知道会多久）— 用呼吸式动画传达"活的状态"
    - 用历史 tip（来自 era.json iron_laws）填充等待时间，玩家可学到东西
-->
<script lang="ts">
  import { randomTip, type LoadingTip } from '$lib/data/loadingTips';
  import { onMount } from 'svelte';

  interface Props {
    /** 是否显示 */
    visible: boolean;
    /** 是否显示进度条（false 则只显示 spinner + tips） */
    showProgress?: boolean;
  }

  let { visible, showProgress = true }: Props = $props();

  let currentTip: LoadingTip = $state(randomTip());
  let fadeIn = $state(true);
  let intervalId: ReturnType<typeof setInterval> | undefined;

  // 进度条（呼吸式：从 0 缓慢推进到 80%，然后停顿后归零重启动）
  let progress = $state(0);
  let direction = $state(1); // 1 = forward, -1 = back

  onMount(() => {
    intervalId = setInterval(() => {
      // 切下一条
      fadeIn = false;
      setTimeout(() => {
        currentTip = randomTip();
        fadeIn = true;
      }, 350);  // 等淡出完成
    }, 4200);
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  });

  // 呼吸式进度（每 200ms 推进）。
  // 用 $effect 在 visible=true 时启动一个内部 ticker。
  $effect(() => {
    if (!visible) {
      progress = 0;
      return;
    }
    const tick = setInterval(() => {
      if (direction === 1) {
        progress = Math.min(100, progress + 2);
        if (progress >= 100) direction = -1;
      } else {
        progress = Math.max(0, progress - 1.5);
        if (progress <= 0) direction = 1;
      }
    }, 180);
    return () => clearInterval(tick);
  });

  // 给 category 一个图标
  const categoryIcon = {
    history: '◈',
    atmosphere: '❀',
    system: '◌',
  };
</script>

{#if visible}
  <div class="loading-overlay" aria-live="polite" aria-busy="true" role="status">
    <!-- 半透明遮罩 -->
    <div class="overlay-backdrop"></div>

    <!-- 主体内容 -->
    <div class="overlay-card">
      <!-- 卷草纹标题 -->
      <div class="overlay-title">
        <span class="title-ornament">❀</span>
        <h2 class="title-text">命数推演中</h2>
        <span class="title-ornament">❀</span>
      </div>

      <!-- 进度条（呼吸式）-->
      {#if showProgress}
        <div class="progress-wrap">
          <div class="progress-track">
            <div
              class="progress-bar"
              style="width: {progress}%"
            ></div>
          </div>
          <p class="progress-label">DM 正在织这段命数…</p>
        </div>
      {/if}

      <!-- Tip 旋转区 -->
      <div class="tip-wrap" data-fading={!fadeIn}>
        <span class="tip-category">
          {categoryIcon[currentTip.category]}
        </span>
        <p class="tip-text">{currentTip.text}</p>
        <p class="tip-source">—《{currentTip.source}》</p>
      </div>
    </div>
  </div>
{/if}

<style>
  .loading-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    pointer-events: all;
  }

  .overlay-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(28, 22, 14, 0.55);  /* 墨色半透明 */
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
  }

  .overlay-card {
    position: relative;
    background: var(--color-paper-aged, #f5efe1);
    border: 1px solid var(--color-bronze, #b08e54);
    border-radius: 14px;
    padding: var(--space-7, 32px) var(--space-8, 48px);
    min-width: 360px;
    max-width: 520px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    color: var(--color-ink, #2c2416);
    text-align: center;
    animation: cardIn 0.5s ease-out;
  }

  @keyframes cardIn {
    from { opacity: 0; transform: translateY(8px) scale(0.96); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }

  .overlay-title {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-3, 12px);
    margin-bottom: var(--space-6, 24px);
  }

  .title-ornament {
    color: var(--color-vermilion, #a02828);
    font-size: 1.2em;
  }

  .title-text {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 500;
    letter-spacing: 0.4em;
    color: var(--color-ink-deep, #1a1410);
  }

  .progress-wrap {
    margin-bottom: var(--space-6, 24px);
  }

  .progress-track {
    height: 4px;
    background: rgba(176, 142, 84, 0.18);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }

  .progress-bar {
    height: 100%;
    background: linear-gradient(90deg,
      var(--color-bronze, #b08e54) 0%,
      var(--color-vermilion, #a02828) 100%);
    border-radius: 2px;
    transition: width 0.18s ease-out;
  }

  .progress-label {
    margin: var(--space-2, 8px) 0 0;
    font-size: 0.85rem;
    font-style: italic;
    color: var(--color-ink-faint, rgba(44, 36, 22, 0.55));
  }

  .tip-wrap {
    transition: opacity 0.35s ease-in-out;
    min-height: 96px;
  }

  .tip-wrap[data-fading="true"] {
    opacity: 0;
  }

  .tip-category {
    display: inline-block;
    color: var(--color-vermilion, #a02828);
    font-size: 1.2em;
    margin-bottom: var(--space-2, 8px);
  }

  .tip-text {
    font-size: 1rem;
    line-height: 1.7;
    color: var(--color-ink, #2c2416);
    margin: 0 0 var(--space-3, 12px);
    letter-spacing: 0.05em;
  }

  .tip-source {
    font-size: 0.8rem;
    font-style: italic;
    color: var(--color-ink-faint, rgba(44, 36, 22, 0.55));
    margin: 0;
    letter-spacing: 0.1em;
  }
</style>
