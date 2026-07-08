<script lang="ts">
  /**
   * EraCard 朝代卡片
   * 用于"开始新游戏"前选择朝代
   */
  import type { Era } from '$lib/api/types';
  import { Card } from '$lib/components/design-system';

  interface Props {
    era: Era;
    selected?: boolean;
    onclick?: () => void;
  }

  let { era, selected = false, onclick }: Props = $props();
</script>

<button
  type="button"
  class="era-card"
  class:era-card-selected={selected}
  onclick={onclick}
  aria-pressed={selected}
>
  <span class="era-card-icon" aria-hidden="true">{era.icon}</span>
  <span class="era-card-name">{era.name}</span>
  <span class="era-card-years">{era.year_start} — {era.year_end}</span>
  <span class="era-card-desc">{era.description}</span>
</button>

<style>
  .era-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-5);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    text-align: left;
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    width: 100%;
  }

  .era-card:hover {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze-dark);
    transform: translateY(-2px);
    box-shadow: var(--shadow-fold);
  }

  .era-card-selected {
    background: var(--color-paper-aged);
    border-color: var(--color-cinnabar);
    border-width: 2px;
  }

  .era-card-icon {
    font-size: var(--text-2xl);
    line-height: 1;
  }

  .era-card-name {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-ink);
  }

  .era-card-years {
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
    letter-spacing: var(--tracking-wide);
  }

  .era-card-desc {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: var(--leading-snug);
  }
</style>
