<script lang="ts">
  /**
   * Dialog 弹层
   *
   * 包装 HTML5 <dialog> 元素：
   *   - 原生焦点陷阱（focus trap）
   *   - ESC 自动关闭
   *   - 蒙层
   *   - a11y 完整
   *
   * variant:
   *   - default  居中弹层
   *   - sheet    底部抽屉（移动端）
   */
  import type { Snippet } from 'svelte';

  interface Props {
    open: boolean;
    onclose: () => void;
    title?: string;
    size?: 'sm' | 'md' | 'lg' | 'xl';
    variant?: 'default' | 'sheet';
    children: Snippet;
    footer?: Snippet;
  }

  let {
    open = $bindable(),
    onclose,
    title,
    size = 'md',
    variant = 'default',
    children,
    footer
  }: Props = $props();

  let dialogEl: HTMLDialogElement | undefined = $state();

  $effect(() => {
    if (!dialogEl) return;
    if (open && !dialogEl.open) {
      dialogEl.showModal();
    } else if (!open && dialogEl.open) {
      dialogEl.close();
    }
  });

  function handleClose() {
    open = false;
    onclose?.();
  }

  function handleClick(e: MouseEvent) {
    // 点击蒙层关闭（点击 dialog 自身时）
    if (e.target === dialogEl) {
      const rect = dialogEl.getBoundingClientRect();
      const inDialog =
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom;
      if (!inDialog) {
        handleClose();
      }
    }
  }
</script>

<dialog
  bind:this={dialogEl}
  class="dialog"
  class:dialog-sheet={variant === 'sheet'}
  class:dialog-sm={size === 'sm'}
  class:dialog-md={size === 'md'}
  class:dialog-lg={size === 'lg'}
  class:dialog-xl={size === 'xl'}
  aria-label={title}
  onclick={handleClick}
  onclose={handleClose}
>
  <article class="dialog-content">
    {#if title}
      <header class="dialog-header">
        <h2 class="dialog-title">{title}</h2>
        <button
          type="button"
          class="dialog-close"
          onclick={handleClose}
          aria-label="关闭"
        >
          ×
        </button>
      </header>
    {/if}

    <div class="dialog-body">
      {@render children()}
    </div>

    {#if footer}
      <footer class="dialog-footer">
        {@render footer()}
      </footer>
    {/if}
  </article>
</dialog>

<style>
  /* dialog 元素重置 */
  .dialog {
    border: none;
    padding: 0;
    background: transparent;
    color: var(--color-ink);
    max-width: min(90vw, var(--container-md));
    max-height: 90vh;
    margin: auto;
  }

  /* 蒙层 */
  .dialog::backdrop {
    background: rgba(44, 36, 22, 0.5);
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
  }

  /* Sizes */
  .dialog-sm { max-width: min(90vw, 400px); }
  .dialog-md { max-width: min(90vw, 600px); }
  .dialog-lg { max-width: min(90vw, 800px); }
  .dialog-xl { max-width: min(90vw, 1200px); }

  /* Sheet: 底部抽屉（移动端） */
  .dialog-sheet {
    max-width: 100vw;
    max-height: 90vh;
    width: 100%;
    margin: auto 0 0 0;
  }

  .dialog-content {
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-ink-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    max-height: 90vh;
    animation: dialog-appear var(--duration-normal) var(--ease-ink);
  }

  .dialog-sheet .dialog-content {
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  @keyframes dialog-appear {
    from {
      opacity: 0;
      transform: translateY(20px) scale(0.96);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .dialog-sheet .dialog-content {
    animation: sheet-appear var(--duration-normal) var(--ease-ink);
  }
  @keyframes sheet-appear {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
  }

  .dialog-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--color-ink-faint);
    background: var(--color-paper-aged);
  }

  .dialog-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0;
  }

  .dialog-close {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-md);
    font-size: 24px;
    line-height: 1;
    color: var(--color-ink-light);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .dialog-close:hover {
    background: var(--color-paper-dark);
    color: var(--color-ink);
  }

  .dialog-body {
    padding: var(--space-5);
    overflow-y: auto;
    flex: 1 1 0;
    min-height: 0;
  }

  .dialog-footer {
    padding: var(--space-4) var(--space-5);
    border-top: 1px solid var(--color-ink-faint);
    background: var(--color-paper-aged);
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
  }
</style>
