<script lang="ts">
  /**
   * FeedbackModal - 玩家反馈表单
   *
   * 5 种类型：bug / idea / praise / question / other
   * 文本 + 联系方式（可选）
   *
   * 🆕 v1.7.30: 字段对齐后端（category, description, contact, session_id）
   */
  import { game } from '$lib/stores';
  import { submitFeedback, type FeedbackCategory } from '$lib/api/feedback';
  import { Chapter, Spinner, Button, Seal, toast } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  let { open, onclose }: Props = $props();

  let category = $state<FeedbackCategory>('bug');
  let description = $state('');
  let contact = $state('');
  let submitting = $state(false);

  $effect(() => {
    if (open) {
      category = 'bug';
      description = '';
      contact = '';
    }
  });

  const categories: { value: FeedbackCategory; label: string; icon: string }[] = [
    { value: 'bug',      label: '问题反馈', icon: '🐛' },
    { value: 'idea',     label: '建议想法', icon: '💡' },
    { value: 'praise',   label: '鼓励肯定', icon: '🌟' },
    { value: 'question', label: '咨询求助', icon: '❓' },
    { value: 'other',    label: '其他',     icon: '📝' }
  ];

  const canSubmit = $derived(description.trim().length > 0);

  async function handleSubmit() {
    if (!canSubmit || submitting) return;
    submitting = true;
    try {
      await submitFeedback({
        category,
        description: description.trim(),
        contact: contact.trim() || undefined,
        session_id: $game?.session_id,
        context: {
          round: $game?.round_current,
          current_date: $game?.narrative?.created_at,
          era: $game?.era_id
        }
      });
      toast.success('感谢你的反馈！');
      onclose();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '提交失败');
    } finally {
      submitting = false;
    }
  }
</script>

<ModalShell {open} {onclose} title="提 笔 留 言" size="md">
  <div class="feedback-form">
    <Chapter title="反馈类型" level={3} />
    <div class="feedback-types">
      {#each categories as t (t.value)}
        <button
          type="button"
          class="feedback-type"
          class:feedback-type-selected={category === t.value}
          onclick={() => category = t.value}
          disabled={submitting}
        >
          <span class="feedback-type-icon">{t.icon}</span>
          <span class="feedback-type-label">{t.label}</span>
        </button>
      {/each}
    </div>

    <Chapter title="详情描述" level={3} />
    <textarea
      class="feedback-textarea"
      placeholder="请详细描述你的反馈..."
      rows="5"
      maxlength="500"
      bind:value={description}
      disabled={submitting}
    ></textarea>
    <div class="feedback-counter">{description.length} / 500</div>

    <Chapter title="联系方式（可选）" level={3} />
    <input
      type="text"
      class="feedback-contact"
      placeholder="邮箱 / 微信 / QQ（方便我们回复你）"
      bind:value={contact}
      disabled={submitting}
    />
  </div>

  {#snippet footer()}
    <Button variant="ghost" onclick={onclose} disabled={submitting}>取消</Button>
    <Seal
      text={submitting ? '提 交 中' : '留 言'}
      size="md"
      onclick={handleSubmit}
    />
  {/snippet}
</ModalShell>

<style>
  .feedback-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .feedback-types {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: var(--space-2);
  }

  .feedback-type {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .feedback-type:hover:not(:disabled) {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
  }
  .feedback-type-selected {
    background: var(--color-paper-aged);
    border-color: var(--color-cinnabar);
    box-shadow: 0 0 0 1px var(--color-cinnabar);
  }
  .feedback-type:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .feedback-type-icon {
    font-size: var(--text-xl);
  }

  .feedback-type-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink);
  }

  .feedback-textarea {
    width: 100%;
    padding: var(--space-3);
    font-family: var(--font-body);
    font-size: var(--text-base);
    line-height: var(--leading-normal);
    color: var(--color-ink);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    resize: vertical;
    min-height: 100px;
  }
  .feedback-textarea:focus {
    outline: none;
    border-color: var(--color-bronze);
    background: var(--color-paper);
    box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.1);
  }

  .feedback-counter {
    text-align: right;
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }

  .feedback-contact {
    width: 100%;
    padding: var(--space-3);
    font-family: var(--font-body);
    font-size: var(--text-base);
    color: var(--color-ink);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
  }
  .feedback-contact:focus {
    outline: none;
    border-color: var(--color-bronze);
    background: var(--color-paper);
    box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.1);
  }
</style>
