<script lang="ts">
  /**
   * Tabs 标签页
   *
   * 横向 + 滑动指示器（朱砂色下划线）
   * 用于弹层内的"角色 Wiki / 关系网 / 关系时间线"等切换
   */
  import type { Snippet } from 'svelte';

  interface TabItem {
    id: string;
    label: string;
    icon?: string;
  }

  interface Props {
    tabs: TabItem[];
    value: string;          // 绑定当前 tab id
    onchange?: (id: string) => void;
    children: Snippet;      // 当前 tab 的内容（外部用 {#if value === tab.id} 渲染）
  }

  let { tabs, value = $bindable(), onchange, children }: Props = $props();
  // 🆕 v1.7.32 容错：children 不是必填（一些 Modal 只用 Tabs 当标题头不传 content）
  const safeChildren = $derived(typeof children === 'function' ? children : null);

  function handleClick(id: string) {
    value = id;
    onchange?.(id);
  }

  function handleKey(e: KeyboardEvent, idx: number) {
    let next = idx;
    if (e.key === 'ArrowRight') {
      next = (idx + 1) % tabs.length;
      e.preventDefault();
    } else if (e.key === 'ArrowLeft') {
      next = (idx - 1 + tabs.length) % tabs.length;
      e.preventDefault();
    }
    if (next !== idx) {
      handleClick(tabs[next].id);
      // focus next tab
      const buttons = (e.currentTarget as HTMLElement).parentElement?.querySelectorAll<HTMLButtonElement>('.tab-btn');
      buttons?.[next]?.focus();
    }
  }
</script>

<div class="tabs" role="tablist">
  {#each tabs as tab, i (tab.id)}
    <button
      type="button"
      role="tab"
      aria-selected={value === tab.id}
      class="tab-btn"
      class:tab-btn-active={value === tab.id}
      onclick={() => handleClick(tab.id)}
      onkeydown={(e) => handleKey(e, i)}
      tabindex={value === tab.id ? 0 : -1}
    >
      {#if tab.icon}<span class="tab-icon" aria-hidden="true">{tab.icon}</span>{/if}
      <span class="tab-label">{tab.label}</span>
    </button>
  {/each}
</div>

<div class="tab-content" role="tabpanel">
  {#if safeChildren}{@render safeChildren()}{/if}
</div>

<style>
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--color-ink-faint);
    overflow-x: auto;
    scrollbar-width: none;
  }
  .tabs::-webkit-scrollbar { display: none; }

  .tab-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    border-bottom: 2px solid transparent;
    cursor: pointer;
    white-space: nowrap;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .tab-btn:hover {
    color: var(--color-ink);
    background: var(--color-paper-aged);
  }

  .tab-btn-active {
    color: var(--color-cinnabar);
    border-bottom-color: var(--color-cinnabar);
    font-weight: 600;
  }

  .tab-icon {
    font-size: var(--text-base);
  }

  .tab-label {
    user-select: none;
  }

  .tab-content {
    padding-top: var(--space-4);
  }
</style>
