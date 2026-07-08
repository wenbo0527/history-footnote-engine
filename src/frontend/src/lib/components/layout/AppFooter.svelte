<script lang="ts">
  /**
   * AppFooter - 底部
   *
   * variant:
   *   - home   关于 + 版本
   *   - game   （空，由 GameView 内的 input area 接管）
   *   - wizard （空）
   */
  import { session } from '$lib/stores';
  import { sessionActions } from '$lib/stores';

  type Variant = 'home' | 'game' | 'wizard';

  interface Props {
    variant?: Variant;
  }

  let { variant = 'home' }: Props = $props();

  function handleLogout() {
    sessionActions.logout();
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
  }
</script>

<footer class="app-footer" data-variant={variant}>
  {#if variant === 'home'}
    <div class="app-footer-content">
      <span class="app-footer-version">v2.0.0 · Svelte 5</span>
      <span class="app-footer-divider">·</span>
      <a href="/about" class="app-footer-link">关于</a>
      <span class="app-footer-divider">·</span>
      <a href="/docs" class="app-footer-link">文档</a>
      {#if $session.isLoggedIn}
        <span class="app-footer-divider">·</span>
        <button type="button" class="app-footer-link app-footer-btn" onclick={handleLogout}>
          退出
        </button>
      {/if}
    </div>
  {/if}
</footer>

<style>
  .app-footer {
    flex: 0 0 auto;
    padding: var(--space-3) var(--space-5);
    padding-bottom: max(var(--space-3), env(safe-area-inset-bottom));
    background: var(--color-paper-aged);
    border-top: 1px solid var(--color-ink-faint);
    text-align: center;
  }

  .app-footer[data-variant='game'],
  .app-footer[data-variant='wizard'] {
    display: none;
  }

  .app-footer-content {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }

  .app-footer-divider {
    opacity: 0.5;
  }

  .app-footer-link {
    color: var(--color-ink-light);
    text-decoration: none;
    transition: color var(--duration-quick) var(--ease-ink);
  }
  .app-footer-link:hover {
    color: var(--color-cinnabar);
  }

  .app-footer-btn {
    background: none;
    border: none;
    font: inherit;
    cursor: pointer;
    padding: 0;
  }
</style>
