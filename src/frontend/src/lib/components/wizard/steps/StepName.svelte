<script lang="ts">
  /**
   * 步骤 3：输入名字
   */
  import { wizard } from '$lib/stores';
</script>

<div class="step-name">
  <header class="step-header">
    <h2 class="step-title">请输入你的名字</h2>
    <p class="step-desc">姓甚名谁，落于纸笔。万历年间，姓名是你在世的凭证。</p>
  </header>

  <div class="name-input-wrap">
    <label class="name-label" for="wizard-name">姓名</label>
    <input
      id="wizard-name"
      type="text"
      class="name-input"
      placeholder="沈织户"
      maxlength="12"
      bind:value={wizard.state.name}
    />
    <div class="name-hint">
      <span>姓氏 + 称呼，如「沈织户」「张氏」「李半仙」</span>
      <span class="name-count">{wizard.state.name.length} / 12</span>
    </div>
  </div>
</div>

<style>
  .step-name {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    max-width: 500px;
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

  .name-input-wrap {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-5);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
  }

  .name-label {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-bronze-dark);
    letter-spacing: var(--tracking-wide);
  }

  .name-input {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-family: var(--font-display);
    font-size: var(--text-xl);
    color: var(--color-ink);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .name-input:focus {
    outline: none;
    border-color: var(--color-cinnabar);
    box-shadow: 0 0 0 3px rgba(160, 40, 40, 0.1);
  }

  .name-hint {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }

  .name-count {
    font-family: var(--font-numeric);
    color: var(--color-bronze-dark);
  }
</style>
