<script lang="ts">
  /**
   * 步骤 3：确认信息
   * 显示所有信息（来自身份预设 + 玩家输入的姓名）
   * "入 局" 印章 → 调 /api/start
   */
  import { wizard, IDENTITY_PRESETS } from '$lib/stores';
  import type { Identity } from '$lib/api/types';

  const identityData = $derived(
    wizard.state.identity ? IDENTITY_PRESETS[wizard.state.identity as Identity] : null
  );
</script>

<div class="step-confirm">
  <header class="step-header">
    <h2 class="step-title">请确认你的角色</h2>
    <p class="step-desc">天下将倾，你我皆是这历史洪流中的一滴水。</p>
  </header>

  {#if wizard.state.identity && wizard.inferredProfile && identityData}
    <div class="confirm-card">
      <div class="confirm-row">
        <span class="confirm-label">姓名</span>
        <span class="confirm-value confirm-name">{wizard.state.name}</span>
      </div>
      <div class="confirm-row">
        <span class="confirm-label">身份</span>
        <span class="confirm-value">
          {identityData.name}
          <span class="confirm-badge">
            {wizard.inferredGender === 'male' ? '男' : '女'}
          </span>
        </span>
      </div>
      <div class="confirm-row">
        <span class="confirm-label">年龄</span>
        <span class="confirm-value">{wizard.inferredProfile.age} 岁</span>
      </div>
      <div class="confirm-row">
        <span class="confirm-label">职业</span>
        <span class="confirm-value">{wizard.inferredProfile.occupation}</span>
      </div>
      <div class="confirm-row">
        <span class="confirm-label">家乡</span>
        <span class="confirm-value">{wizard.inferredProfile.hometown}</span>
      </div>
      <div class="confirm-row">
        <span class="confirm-label">朝代</span>
        <span class="confirm-value">万历十五年（1587）</span>
      </div>
    </div>

    <p class="confirm-note">
      「一切已备。你的故事，从此刻开始。」
    </p>
  {:else}
    <p class="confirm-error">请先完成前两步</p>
  {/if}
</div>

<style>
  .step-confirm {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    max-width: 560px;
    margin: 0 auto;
  }

  .step-header {
    text-align: center;
  }

  .step-title {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0 0 var(--space-2);
  }

  .step-desc {
    font-family: var(--font-body);
    font-size: var(--text-md);
    color: var(--color-ink-light);
  }

  .confirm-card {
    background: var(--color-paper-aged);
    border: 2px solid var(--color-bronze);
    border-radius: var(--radius-md);
    padding: var(--space-5);
  }

  .confirm-row {
    display: flex;
    align-items: center;
    padding: var(--space-2) 0;
    border-bottom: 1px dashed var(--color-ink-faint);
  }
  .confirm-row:last-child {
    border-bottom: none;
  }

  .confirm-label {
    flex: 0 0 80px;
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
    letter-spacing: var(--tracking-wide);
  }

  .confirm-value {
    flex: 1 1 0;
    font-family: var(--font-body);
    font-size: var(--text-md);
    color: var(--color-ink);
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .confirm-name {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    color: var(--color-cinnabar);
    font-weight: 600;
  }

  .confirm-badge {
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    padding: 2px 8px;
    background: var(--color-paper);
    border-radius: var(--radius-sm);
    font-weight: 600;
  }

  .confirm-note {
    text-align: center;
    font-family: var(--font-display);
    font-size: var(--text-base);
    color: var(--color-ink-light);
    font-style: italic;
    margin: 0;
  }

  .confirm-error {
    text-align: center;
    color: var(--color-cinnabar);
  }
</style>
