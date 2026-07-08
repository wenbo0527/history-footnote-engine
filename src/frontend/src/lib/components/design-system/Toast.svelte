<script lang="ts" module>
  /**
   * Toast 模块：全局 toast 队列管理
   * 用法: import { toast } from '$lib/components/design-system/Toast.svelte';
   *       toast.success('保存成功');
   */
  type ToastType = 'success' | 'warning' | 'error' | 'info';
  interface ToastItem {
    id: number;
    type: ToastType;
    message: string;
    duration: number;
  }

  const items: ToastItem[] = $state([]);
  let nextId = 0;

  export const toast = {
    show(message: string, options?: { type?: ToastType; duration?: number }) {
      const id = nextId++;
      const type = options?.type ?? 'info';
      const duration = options?.duration ?? 3000;
      items.push({ id, type, message, duration });
      if (duration > 0) {
        setTimeout(() => this.dismiss(id), duration);
      }
      return id;
    },
    success(message: string, duration?: number) {
      return this.show(message, { type: 'success', duration });
    },
    warning(message: string, duration?: number) {
      return this.show(message, { type: 'warning', duration });
    },
    error(message: string, duration?: number) {
      return this.show(message, { type: 'error', duration });
    },
    info(message: string, duration?: number) {
      return this.show(message, { type: 'info', duration });
    },
    dismiss(id: number) {
      const idx = items.findIndex(t => t.id === id);
      if (idx >= 0) items.splice(idx, 1);
    }
  };
</script>

<script lang="ts">
  /**
   * Toast 容器（通常放在根 layout）
   * 显示右上角堆叠通知
   */
  import { fade, fly } from 'svelte/transition';

  function getIcon(type: ToastType): string {
    return {
      success: '✓',
      warning: '⚠',
      error: '✕',
      info: 'ℹ'
    }[type];
  }
</script>

<div class="toast-container" role="region" aria-label="通知">
  {#each items as t (t.id)}
    <div
      class="toast"
      class:toast-success={t.type === 'success'}
      class:toast-warning={t.type === 'warning'}
      class:toast-error={t.type === 'error'}
      class:toast-info={t.type === 'info'}
      role="status"
      transition:fly={{ y: -20, duration: 400 }}
    >
      <span class="toast-icon" aria-hidden="true">{getIcon(t.type)}</span>
      <span class="toast-message">{t.message}</span>
      <button
        type="button"
        class="toast-close"
        onclick={() => toast.dismiss(t.id)}
        aria-label="关闭通知"
      >×</button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: var(--space-4);
    right: var(--space-4);
    z-index: var(--z-toast);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    max-width: 360px;
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-ink);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    pointer-events: auto;
    min-width: 240px;
  }

  .toast-icon {
    width: 24px;
    height: 24px;
    border-radius: var(--radius-full);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 14px;
    color: var(--color-paper);
    flex-shrink: 0;
  }

  .toast-success { border-left: 3px solid var(--color-success); }
  .toast-success .toast-icon { background: var(--color-success); }

  .toast-warning { border-left: 3px solid var(--color-warning); }
  .toast-warning .toast-icon { background: var(--color-warning); }

  .toast-error { border-left: 3px solid var(--color-cinnabar); }
  .toast-error .toast-icon { background: var(--color-cinnabar); }

  .toast-info { border-left: 3px solid var(--color-info); }
  .toast-info .toast-icon { background: var(--color-info); }

  .toast-message {
    flex: 1 1 0;
    line-height: var(--leading-snug);
  }

  .toast-close {
    width: 20px;
    height: 20px;
    color: var(--color-ink-light);
    font-size: 18px;
    line-height: 1;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
  }
  .toast-close:hover {
    color: var(--color-ink);
    background: var(--color-paper-aged);
  }
</style>
