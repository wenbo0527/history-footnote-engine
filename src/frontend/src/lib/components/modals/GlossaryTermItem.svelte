<script lang="ts">
  /**
   * GlossaryTermItem - 词条项（GlossaryModal 子组件）
   *
   * 拆出理由：原 GlossaryModal.svelte 368 行
   * - 搜索结果列表中的单术语按钮 12 行 + 25 行样式
   * - 拆出后主 modal 减重 ~15 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { GlossaryTerm } from '$lib/api/types';

  interface Props {
    term: GlossaryTerm;
    disabled: boolean;
    onselect: (key: string) => void;
  }

  let { term, disabled, onselect }: Props = $props();
</script>

<button
  type="button"
  class="glossary-term-item"
  onclick={() => onselect(term.key)}
  disabled={disabled}
>
  <div class="glossary-term-header">
    <span class="glossary-term-key">{term.key}</span>
    <span class="glossary-term-category">{term.category}</span>
  </div>
  <p class="glossary-term-def">{term.definition}</p>
</button>

<style>
  .glossary-term-item {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-1);
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    text-align: left;
    cursor: pointer;
    font-family: var(--font-body);
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .glossary-term-item:hover:not(:disabled) {
    background: var(--color-paper-aged);
    border-left-color: var(--color-cinnabar);
    transform: translateX(2px);
    box-shadow: var(--shadow-1);
  }
  .glossary-term-item:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .glossary-term-header {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .glossary-term-key {
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink);
    font-weight: 600;
  }
  .glossary-term-category {
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    padding: 1px 6px;
    background: rgba(165, 40, 40, 0.06);
    border-radius: var(--radius-sm);
  }
  .glossary-term-def {
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: 1.5;
    margin: 0;
  }
</style>