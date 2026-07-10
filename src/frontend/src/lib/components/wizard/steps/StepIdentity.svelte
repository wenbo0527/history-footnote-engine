<script lang="ts">
  /**
   * 步骤 1：选择身份
   * 4 个身份卡片（织工/织女/牙商/佃户）
   * 选择身份后自动绑定性别 + 年龄 + 职业 + 家乡
   */
  import { wizard, IDENTITIES, IDENTITY_PRESETS, type WizardState } from '$lib/stores';
  import type { Identity } from '$lib/api/types';

  function select(id: Identity) {
    wizard.setIdentity(id);
  }

  // 类型守卫：循环 item.id 是 string，转 Identity
  function preset(id: string) {
    return IDENTITY_PRESETS[id as Identity];
  }
</script>

<div class="step-identity">
  <header class="step-header">
    <h2 class="step-title">请选择你的身份</h2>
    <p class="step-desc">万历年间，苏州盛泽。这是你在这个时代的立足之本。</p>
  </header>

  <div class="identity-grid">
    {#each IDENTITIES as item (item.id)}
      {@const selected = wizard.state.identity === item.id}
      {@const p = preset(item.id)}
      {@const genderLabel = p.gender === 'male' ? '男' : '女'}
      <button
        type="button"
        class="identity-card"
        class:identity-card-selected={selected}
        onclick={() => select(item.id as Identity)}
      >
        <span class="identity-icon" aria-hidden="true">
          <img src={item.icon} alt="" class="identity-icon-img" />
        </span>
        <span class="identity-name">{item.name}</span>
        <span class="identity-gender">{genderLabel}</span>
        <span class="identity-desc">{item.desc}</span>
        <span class="identity-preset">
          {p.profile.age}岁 · {p.profile.occupation}
        </span>
      </button>
    {/each}
  </div>
</div>

<style>
  .step-identity {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
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
    line-height: var(--leading-snug);
  }

  .identity-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--space-4);
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
  }

  .identity-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    background: var(--color-paper);
    border: 2px solid var(--color-ink-faint);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    text-align: center;
  }

  .identity-card:hover {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
    transform: translateY(-2px);
    box-shadow: var(--shadow-fold);
  }

  .identity-card-selected {
    background: var(--color-paper-aged);
    border-color: var(--color-cinnabar);
    box-shadow: 0 0 0 1px var(--color-cinnabar), var(--shadow-fold);
  }

  .identity-icon {
    display: inline-flex;
    line-height: 1;
  }

  .identity-icon-img {
    width: 2.5em;
    height: 2.5em;
    object-fit: contain;
  }

  .identity-name {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-ink);
  }

  .identity-gender {
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    padding: 2px 8px;
    background: var(--color-paper);
    border-radius: var(--radius-sm);
    font-weight: 600;
  }

  .identity-desc {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: var(--leading-snug);
  }

  .identity-preset {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
    padding-top: var(--space-1);
    border-top: 1px dashed var(--color-ink-faint);
    margin-top: var(--space-1);
  }

  /* 移动端 */
  @media (max-width: 767px) {
    .identity-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: var(--space-3);
    }
    .identity-card {
      padding: var(--space-3);
    }
    .identity-icon {
      font-size: var(--text-2xl);
    }
    .identity-icon-img {
      width: 2em;
      height: 2em;
    }
  }
</style>
