<script lang="ts">
  /**
   * WizardShell - Wizard 根容器（v2.0 简化版）
   * 3 步流程：身份 → 姓名 → 确认
   * 提交时调 /api/start，用 wizard.inferredProfile
   */
  import { goto } from '$app/navigation';
  import { wizard } from '$lib/stores';
  import { gameActions } from '$lib/stores';
  import { startGame } from '$lib/api/start';
  import { Button, Seal, Spinner } from '$lib/components/design-system';
  import WizardProgress from './WizardProgress.svelte';
  import StepIdentity from './steps/StepIdentity.svelte';
  import StepName from './steps/StepName.svelte';
  import StepConfirm from './steps/StepConfirm.svelte';

  const steps = [
    { title: '你的身份', label: '身份' },
    { title: '你的名字', label: '名字' },
    { title: '确认与入局', label: '入局' }
  ];

  let submitting = $state(false);
  let submitError = $state<string | null>(null);

  async function handleSubmit() {
    if (!wizard.canProceed || !wizard.isLastStep) return;
    if (!wizard.state.identity || !wizard.inferredProfile) return;

    submitting = true;
    submitError = null;

    try {
      const data = await startGame({
        era_id: 'wanli1587',
        identity: wizard.state.identity,
        gender: wizard.inferredGender!,
        character: {
          name: wizard.state.name,
          age: wizard.inferredProfile.age,
          occupation: wizard.inferredProfile.occupation,
          hometown: wizard.inferredProfile.hometown
        }
      });

      gameActions.set(data);
      wizard.reset();
      // 🆕 v1.7.30: 跳到 game 页时带 session_id（startGame 已写 localStorage）
      goto(`/game?session=${data.session_id}`);
    } catch (e) {
      submitError = e instanceof Error ? e.message : '开始游戏失败';
    } finally {
      submitting = false;
    }
  }
</script>

<div class="wizard-shell">
  <WizardProgress
    {steps}
    current={wizard.state.currentStep}
    onstep={(i) => wizard.goTo(i)}
  />

  <div class="wizard-body">
    <div class="wizard-step">
      {#if wizard.state.currentStep === 0}
        <StepIdentity />
      {:else if wizard.state.currentStep === 1}
        <StepName />
      {:else}
        <StepConfirm />
      {/if}
    </div>

    {#if submitError}
      <div class="wizard-error" role="alert">
        <strong>出错了：</strong>{submitError}
      </div>
    {/if}
  </div>

  <footer class="wizard-nav">
    <div class="wizard-nav-inner">
      <Button
        variant="ghost"
        onclick={() => wizard.prev()}
        disabled={wizard.state.currentStep === 0 || submitting}
      >
        ← 上一步
      </Button>

      <span class="wizard-nav-spacer"></span>

      {#if wizard.isLastStep}
        <Seal
          text="入 局"
          size="lg"
          pulse={!submitting && wizard.canProceed}
          onclick={handleSubmit}
        />
      {:else}
        <Button
          variant="primary"
          size="lg"
          onclick={() => wizard.next()}
          disabled={!wizard.canProceed || submitting}
        >
          下一步 →
        </Button>
      {/if}
    </div>
  </footer>
</div>

<style>
  .wizard-shell {
    display: flex;
    flex-direction: column;
    min-height: 100%;
  }

  .wizard-body {
    flex: 1 1 0;
    padding: var(--space-7) var(--space-5);
    max-width: 960px;
    margin: 0 auto;
    width: 100%;
    animation: wizard-fade var(--duration-slow) var(--ease-ink);
  }

  @keyframes wizard-fade {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .wizard-error {
    margin-top: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-cinnabar);
    border-left-width: 3px;
    border-radius: var(--radius-md);
    color: var(--color-cinnabar);
    font-family: var(--font-body);
    font-size: var(--text-sm);
  }

  .wizard-nav {
    flex: 0 0 auto;
    padding: var(--space-4) var(--space-5);
    padding-bottom: max(var(--space-4), env(safe-area-inset-bottom));
    background: var(--color-paper-aged);
    border-top: 1px solid var(--color-ink-faint);
  }

  .wizard-nav-inner {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    max-width: 960px;
    margin: 0 auto;
  }

  .wizard-nav-spacer {
    flex: 1 1 0;
  }

  @media (max-width: 767px) {
    .wizard-body {
      padding: var(--space-4) var(--space-3);
    }
    .wizard-nav-inner {
      gap: var(--space-2);
    }
  }
</style>
