<script lang="ts">
  /**
   * WizardProgress - 步骤进度条
   *
   * 显示：
   *   - 当前步骤 / 总步骤
   *   - 圆点指示器（已完成 / 当前 / 未开始）
   *   - 步骤名称
   */
  interface Step {
    title: string;
    label: string;
  }

  interface Props {
    steps: Step[];
    current: number;        // 0-indexed
    onstep?: (idx: number) => void;  // 跳步（可选）
  }

  let { steps, current, onstep }: Props = $props();

  function handleStepClick(idx: number) {
    if (onstep) onstep(idx);
  }
</script>

<div class="wizard-progress">
  <div class="wizard-progress-bar">
    {#each steps as step, i (i)}
      {@const isComplete = i < current}
      {@const isCurrent = i === current}
      <button
        type="button"
        class="wizard-progress-step"
        class:wizard-progress-step-complete={isComplete}
        class:wizard-progress-step-current={isCurrent}
        onclick={() => handleStepClick(i)}
        disabled={!onstep || i > current}
        aria-current={isCurrent ? 'step' : undefined}
        aria-label={`第 ${i + 1} 步：${step.label}`}
      >
        <span class="wizard-progress-dot">
          {#if isComplete}
            <span aria-hidden="true">✓</span>
          {:else}
            <span>{i + 1}</span>
          {/if}
        </span>
        <span class="wizard-progress-label">{step.label}</span>
      </button>
      {#if i < steps.length - 1}
        <span
          class="wizard-progress-line"
          class:wizard-progress-line-complete={i < current}
          aria-hidden="true"
        ></span>
      {/if}
    {/each}
  </div>
  <div class="wizard-progress-meta">
    <span>第 <strong>{current + 1}</strong> / {steps.length} 步</span>
    <span class="wizard-progress-title">{steps[current]?.title ?? ''}</span>
  </div>
</div>

<style>
  .wizard-progress {
    padding: var(--space-4) var(--space-5);
    background: var(--color-paper-aged);
    border-bottom: 1px solid var(--color-ink-faint);
  }

  .wizard-progress-bar {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    max-width: 800px;
    margin: 0 auto;
  }

  .wizard-progress-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-1);
    background: none;
    border: none;
    cursor: pointer;
    padding: var(--space-1);
    transition: all var(--duration-normal) var(--ease-ink);
    flex: 0 0 auto;
  }
  .wizard-progress-step:disabled {
    cursor: not-allowed;
  }

  .wizard-progress-dot {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    font-weight: 600;
    background: var(--color-paper);
    color: var(--color-ink-light);
    border: 2px solid var(--color-ink-faint);
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .wizard-progress-step-complete .wizard-progress-dot {
    background: var(--color-success);
    color: var(--color-paper);
    border-color: var(--color-success);
  }

  .wizard-progress-step-current .wizard-progress-dot {
    background: var(--color-cinnabar);
    color: var(--color-paper);
    border-color: var(--color-cinnabar);
    box-shadow: 0 0 0 4px rgba(160, 40, 40, 0.15);
    transform: scale(1.05);
  }

  .wizard-progress-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    white-space: nowrap;
  }

  .wizard-progress-step-current .wizard-progress-label {
    color: var(--color-cinnabar);
    font-weight: 600;
  }

  .wizard-progress-line {
    flex: 1 1 0;
    height: 2px;
    background: var(--color-ink-faint);
    margin-top: -22px;        /* 跟 dot 居中 */
    transition: background var(--duration-normal) var(--ease-ink);
    min-width: 24px;
  }

  .wizard-progress-line-complete {
    background: var(--color-success);
  }

  .wizard-progress-meta {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    max-width: 800px;
    margin: var(--space-3) auto 0;
    padding: 0 var(--space-2);
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }

  .wizard-progress-meta strong {
    color: var(--color-cinnabar);
    font-weight: 700;
    font-size: var(--text-sm);
  }

  .wizard-progress-title {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink);
    font-weight: 500;
  }

  /* 移动端：隐藏 label，只显示 dot */
  @media (max-width: 767px) {
    .wizard-progress {
      padding: var(--space-3) var(--space-2);
    }
    .wizard-progress-label {
      display: none;
    }
    .wizard-progress-dot {
      width: 28px;
      height: 28px;
      font-size: var(--text-xs);
    }
    .wizard-progress-line {
      margin-top: -18px;
    }
  }
</style>
