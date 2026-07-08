<script lang="ts">
  /**
   * ModalShell - 弹层外壳
   *
   * 包装 HTML5 <dialog>：
   *   - 国风：宣纸色 + 古铜边 + 朱砂标题
   *   - 自动焦点 + ESC 关闭 + 蒙层
   *   - 移动端：底部抽屉（sheet 变体）
   *   - 桌面：居中弹层
   */
  import type { Snippet } from 'svelte';
  import { onMount, untrack, tick } from 'svelte';

  interface Props {
    open: boolean;
    onclose: () => void;
    title?: string;
    size?: 'sm' | 'md' | 'lg' | 'xl';
    variant?: 'default' | 'sheet';
    children: Snippet;
    footer?: Snippet;
    /** 🆕 v2.3: 头部右侧操作区（如刷新按钮） */
    headerActions?: Snippet;
  }

  let {
    open = $bindable(),
    onclose,
    title,
    size = 'md',
    variant = 'default',
    children,
    footer,
    headerActions
  }: Props = $props();

  let dialogEl: HTMLDialogElement | undefined = $state();

  // 🆕 v1.7.32 修复：dialog 必须用 showModal() 才能进入 top layer (有 ::backdrop)。
  // 但 Svelte 5 $effect 在 mount 第一次触发时，bind:this 可能还未就绪。
  // 用 $effect.pre 替代默认 effect（在 DOM 更新前执行）确保 dialogEl 已 bind。
  $effect.pre(() => {
    void open;  // 订阅
    if (typeof window === 'undefined') return;
    // 用 tick + untrack 等待 dialogEl 准备好
    if (open && !dialogEl) {
      tick().then(() => {
        if (dialogEl && open && !dialogEl.open) {
          dialogEl.showModal();
        }
      });
      return;
    }
    untrack(() => {
      if (!dialogEl) return;
      if (open && !dialogEl.open) {
        dialogEl.showModal();
      } else if (!open && dialogEl.open) {
        dialogEl.close();
      }
    });
  });

  function handleClose() {
    open = false;
    onclose?.();
  }
</script>

<dialog
  bind:this={dialogEl}
  class="modal-shell"
  class:modal-sheet={variant === 'sheet'}
  class:modal-sm={size === 'sm'}
  class:modal-md={size === 'md'}
  class:modal-lg={size === 'lg'}
  class:modal-xl={size === 'xl'}
  aria-label={title}
  onclose={handleClose}
  open={open || undefined}
>
  <article class="modal-content">
    {#if title}
      <header class="modal-header">
        <h2 class="modal-title">{title}</h2>
        <div class="modal-header-right">
          {#if headerActions}
            {@render headerActions()}
          {/if}
          <button
            type="button"
            class="modal-close"
            onclick={handleClose}
            aria-label="关闭"
          >
            ×
          </button>
        </div>
      </header>
    {/if}

    <div class="modal-body">
      {@render children()}
    </div>

    {#if footer}
      <footer class="modal-footer">
        {@render footer()}
      </footer>
    {/if}
  </article>
</dialog>

<style>
  .modal-shell {
    border: none;
    padding: 0;
    background: transparent;
    color: var(--color-ink);
    max-width: min(92vw, var(--container-md));
    max-height: 90vh;
    min-height: 400px;       /* 🆕 v1.7.32: 兜底最小高度，让 body 有显示空间 */
    width: 100%;
    height: auto;
    margin: auto;
  }

  .modal-shell::backdrop {
    background: rgba(44, 36, 22, 0.55);
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
  }

  /* Sizes */
  .modal-sm { max-width: min(92vw, 440px); }
  .modal-md { max-width: min(92vw, 640px); }
  .modal-lg { max-width: min(92vw, 800px); }
  .modal-xl { max-width: min(92vw, 1200px); }

  /* Sheet 变体：底部抽屉（移动端） */
  .modal-sheet {
    max-width: 100vw;
    max-height: 90vh;
    width: 100%;
    margin: auto 0 0 0;
  }

  .modal-content {
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-ink-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    max-height: 90vh;
    min-height: 0;          /* 🆕 v1.7.32: 允许 flex children 收缩 */
    height: 100%;           /* 撑满 dialog（dialog 有 max-width 但高度由内容决定） */
    width: 100%;
    animation: modal-appear var(--duration-normal) var(--ease-ink);
  }

  .modal-sheet .modal-content {
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  @keyframes modal-appear {
    from {
      opacity: 0;
      transform: translateY(20px) scale(0.96);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .modal-sheet .modal-content {
    animation-name: sheet-appear;
  }
  @keyframes sheet-appear {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--color-ink-faint);
    background: var(--color-paper-aged);
    gap: var(--space-3);
  }

  .modal-header-right {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: 0 0 auto;
  }

  .modal-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-ink);
    margin: 0;
    letter-spacing: var(--tracking-wide);
  }

  .modal-close {
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
  .modal-close:hover {
    background: var(--color-paper-dark);
    color: var(--color-cinnabar);
  }

  .modal-body {
    padding: var(--space-5);
    overflow-y: auto;
    flex: 1 1 0;
    min-height: 0;
  }

  .modal-footer {
    padding: var(--space-3) var(--space-5);
    border-top: 1px solid var(--color-ink-faint);
    background: var(--color-paper-aged);
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
  }
</style>
