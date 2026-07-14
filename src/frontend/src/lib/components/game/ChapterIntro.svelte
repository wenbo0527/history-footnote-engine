<!--
  🆕 v2.10.1 W69: 章节开场遮罩

  在新章节（current_round=0 或章节变化）首次进入时显示
  - 显示章节名 + 简介
  - 点击"开始"才进入回合 1
-->
<script lang="ts">
  interface Props {
    chapterTitle: string;
    chapterNumber: number;
    totalChapters: number;
    summary?: string;
    eraName?: string;
    onStart: () => void;
  }

  let { chapterTitle, chapterNumber, totalChapters, summary = '', eraName = '', onStart }: Props = $props();

  let starting = $state(false);
  function handleStart() {
    if (starting) return;
    starting = true;
    onStart();
    setTimeout(() => { starting = false; }, 1000);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleStart();
    }
  }
</script>

<div
  class="chapter-intro"
  role="dialog"
  aria-modal="true"
  aria-labelledby="chapter-intro-title"
  tabindex="-1"
  onkeydown={handleKeydown}
>
  <div class="chapter-intro-bg"></div>
  <div class="chapter-intro-card">
    <p class="chapter-intro-eyebrow">{eraName ? `${eraName} · ` : ''}章节 {chapterNumber} / {totalChapters}</p>
    <h2 class="chapter-intro-title" id="chapter-intro-title">{chapterTitle}</h2>
    {#if summary}
      <p class="chapter-intro-summary">{summary}</p>
    {/if}
    <button
      class="chapter-intro-button"
      onclick={handleStart}
      disabled={starting}
      aria-label="开始章节"
    >
      <span>{starting ? '准备中...' : '开始本章节'}</span>
    </button>
    <p class="chapter-intro-hint">按 Enter 或空格直接开始</p>
  </div>
</div>

<style>
  .chapter-intro {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9000;
    animation: chapter-intro-fade 400ms ease-out;
  }
  @keyframes chapter-intro-fade {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .chapter-intro-bg {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      ellipse at center,
      rgba(245, 240, 225, 0.96) 0%,
      rgba(225, 210, 180, 0.98) 100%
    );
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }
  .chapter-intro-card {
    position: relative;
    max-width: 480px;
    width: 90%;
    padding: var(--space-7, 32px) var(--space-6, 24px);
    background: rgba(255, 250, 235, 0.95);
    border: 1px solid rgba(143, 75, 40, 0.25);
    border-radius: var(--radius-lg, 12px);
    box-shadow:
      0 16px 48px rgba(143, 75, 40, 0.2),
      0 0 0 1px rgba(255, 255, 255, 0.5) inset;
    text-align: center;
    animation: chapter-intro-rise 600ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes chapter-intro-rise {
    from { opacity: 0; transform: translateY(20px) scale(0.96); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  .chapter-intro-eyebrow {
    margin: 0 0 var(--space-3, 12px);
    font-size: var(--text-sm, 12px);
    color: var(--color-bronze-dark, #5a3a25);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
  }
  .chapter-intro-title {
    margin: 0 0 var(--space-4, 16px);
    font-family: var(--font-heading, serif);
    font-size: var(--text-3xl, 28px);
    color: var(--color-ink, #2a1a0a);
    line-height: 1.3;
    font-weight: 700;
  }
  .chapter-intro-summary {
    margin: 0 0 var(--space-5, 20px);
    font-size: var(--text-base, 14px);
    color: var(--color-ink-light, #6a5a4a);
    line-height: 1.7;
  }
  .chapter-intro-button {
    display: inline-block;
    padding: var(--space-3, 12px) var(--space-6, 24px);
    background: linear-gradient(135deg, #8f4b28 0%, #5a3a25 100%);
    color: #f5f0e1;
    border: 0;
    border-radius: var(--radius-md, 8px);
    font-family: var(--font-heading, serif);
    font-size: var(--text-lg, 16px);
    font-weight: 600;
    cursor: pointer;
    transition: transform 150ms ease, box-shadow 150ms ease;
    box-shadow: 0 4px 12px rgba(143, 75, 40, 0.3);
  }
  .chapter-intro-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(143, 75, 40, 0.4);
  }
  .chapter-intro-button:active:not(:disabled) {
    transform: translateY(0);
  }
  .chapter-intro-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .chapter-intro-hint {
    margin: var(--space-3, 12px) 0 0;
    font-size: var(--text-xs, 11px);
    color: var(--color-ink-light, #6a5a4a);
    opacity: 0.7;
  }

  /* 🆕 v2.10.8: mobile 适配（≤767）
     - 浮层宽度从 90% 改为 94%，左右 padding 缩小
     - 标题字号缩小，避免在 ≤360 屏宽上折行挤压按钮
     - 按钮区域 ≥ 44px（iOS HIG 最小可点击） */
  @media (max-width: 767px) {
    .chapter-intro-card {
      width: 94%;
      max-width: none;
      padding: var(--space-5, 20px) var(--space-4, 16px);
    }
    .chapter-intro-title {
      font-size: var(--text-2xl, 22px);
    }
    .chapter-intro-summary {
      font-size: var(--text-sm, 13px);
      line-height: 1.6;
    }
    .chapter-intro-button {
      padding: var(--space-3, 12px) var(--space-5, 20px);
      font-size: var(--text-base, 14px);
      min-height: 44px;
    }
  }

  /* 极窄屏（≤360）进一步压缩 */
  @media (max-width: 360px) {
    .chapter-intro-card {
      width: 96%;
      padding: var(--space-4, 16px) var(--space-3, 12px);
    }
    .chapter-intro-title {
      font-size: var(--text-xl, 18px);
    }
  }
</style>
