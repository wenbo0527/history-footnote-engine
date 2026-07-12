<script lang="ts">
  /**
   * LoginForm - 登录/注册表单（login 路由子组件）
   *
   * 拆出理由：原 /login/+page.svelte 441 行
   * - 表单段 75 行 template + ~100 行样式 + 75 行 script 业务逻辑
   * - 拆出后主路由聚焦 page 容器 + 状态管理
   *
   * 🆕 v2.10.1 W52 P1-4A 续
   */
  import { Button } from '$lib/components/design-system';

  interface Props {
    mode: 'login' | 'register';
    loading: boolean;
    disabled: boolean;
    lockSeconds: number;
    error: string | null;
    username: string;
    password: string;
    inviteCode: string;
    switchLink: boolean;
    onsubmit: () => void;
    onusername: (v: string) => void;
    onpassword: (v: string) => void;
    oninvite: (v: string) => void;
    onswitchmode: () => void;
    onkeydown: (e: KeyboardEvent) => void;
  }

  let {
    mode, loading, disabled, lockSeconds, error,
    username, password, inviteCode, switchLink,
    onsubmit, onusername, onpassword, oninvite, onswitchmode, onkeydown,
  }: Props = $props();
</script>

<form
  class="login-form"
  onsubmit={(e) => { e.preventDefault(); onsubmit(); }}
>
  <input
    type="text"
    class="login-input"
    placeholder="用户名（如：沈青山）"
    value={username}
    oninput={(e) => onusername((e.currentTarget as HTMLInputElement).value)}
    onkeydown={onkeydown}
    disabled={loading || lockSeconds > 0}
    maxlength="20"
    autocomplete="username"
  />

  {#if mode === 'register'}
    <input
      type="text"
      class="login-input login-input-invite"
      placeholder="邀请码（如：INV-XXXX-XXXX）"
      value={inviteCode}
      oninput={(e) => oninvite((e.currentTarget as HTMLInputElement).value)}
      onkeydown={onkeydown}
      disabled={loading || lockSeconds > 0}
      maxlength="20"
      autocomplete="off"
    />
  {/if}

  <input
    type="password"
    class="login-input"
    placeholder="密码（至少 6 字符）"
    value={password}
    oninput={(e) => onpassword((e.currentTarget as HTMLInputElement).value)}
    onkeydown={onkeydown}
    disabled={loading || lockSeconds > 0}
    maxlength="64"
    autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
  />

  {#if error}
    <div class="login-error" role="alert">
      <span class="login-error-icon" aria-hidden="true">⚠</span>
      <span>{error}</span>
      {#if switchLink && error.includes('账户不存在')}
        <button type="button" class="login-error-link" onclick={onswitchmode}>
          立即注册 →
        </button>
      {/if}
    </div>
  {/if}

  <Button
    type="submit"
    variant="primary"
    size="lg"
    disabled={disabled || loading || lockSeconds > 0}
    loading={loading}
    fullWidth
  >
    {#if lockSeconds > 0}
      锁定中 ({lockSeconds}s)
    {:else if mode === 'login'}
      进入万历年
    {:else}
      创建账户
    {/if}
  </Button>

  <button
    type="button"
    class="login-switch"
    onclick={onswitchmode}
    disabled={loading}
  >
    {mode === 'login' ? '没有账户？立即注册' : '已有账户？返回登录'}
  </button>
</form>

<style>
  .login-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .login-input {
    width: 100%;
    padding: var(--space-3);
    font-family: var(--font-body);
    font-size: var(--text-base);
    color: var(--color-ink);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .login-input:focus {
    outline: none;
    border-color: var(--color-bronze);
    box-shadow: 0 0 0 3px rgba(184, 134, 11, 0.1);
  }
  .login-input:disabled {
    background: var(--color-paper-aged);
    color: var(--color-ink-faint);
    cursor: not-allowed;
  }
  .login-input::placeholder {
    color: var(--color-ink-faint);
  }

  .login-input-invite {
    border-left: 3px solid var(--color-cinnabar);
  }

  .login-error {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: rgba(165, 40, 40, 0.06);
    border: 1px solid rgba(165, 40, 40, 0.3);
    border-left: 3px solid var(--color-cinnabar);
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    color: var(--color-cinnabar);
  }
  .login-error-icon {
    flex: 0 0 auto;
  }
  .login-error-link {
    background: none;
    border: none;
    color: var(--color-cinnabar);
    text-decoration: underline;
    font-weight: 600;
    cursor: pointer;
    margin-left: auto;
  }
  .login-error-link:hover {
    color: var(--color-bronze-dark);
  }

  .login-switch {
    background: none;
    border: none;
    color: var(--color-bronze-dark);
    text-decoration: underline;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    cursor: pointer;
    padding: var(--space-2);
    transition: color var(--duration-normal) var(--ease-ink);
  }
  .login-switch:hover:not(:disabled) {
    color: var(--color-cinnabar);
  }
  .login-switch:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>