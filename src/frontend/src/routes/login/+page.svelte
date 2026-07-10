<script lang="ts">
  /**
   * /login - 登录/注册页（v1.7.30）
   *
   * 两态：
   *   1. 登录：username + password → /api/account/login
   *   2. 注册：username + invite_code + password → /api/account/register
   *
   * 邀请码：
   *   - 注册时必填
   *   - 暂存到 localStorage（v1.7.30 Demo 阶段简化）
   *
   * 失败处理：
   *   - 密码错误：显示"还有 N 次机会"
   *   - 账户不存在：提示注册
   *   - 锁定：显示剩余时间
   *
   * 访客模式：点"以访客身份进入" → 标记 localStorage → 跳首页
   */
  import { goto } from '$app/navigation';
  import {
    login, register, isLoggedIn, setGuest, getInviteCode, setInviteCode, ensureGuestAccountId
  } from '$lib/api/account';
  import { Chapter, Divider, Button, Seal, Spinner, toast } from '$lib/components/design-system';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';

  let mode = $state<'login' | 'register'>('login');
  let username = $state('');
  let password = $state('');
  let inviteCode = $state('');
  let loading = $state(false);
  let error = $state<string | null>(null);
  let failCount = $state(0);
  let lockedUntil = $state<number | null>(null);

  // 已登录则直接跳首页
  onMount(() => {
    if (isLoggedIn()) {
      const next = $page.url.searchParams.get('next') ?? '/';
      goto(next);
    }
    // 预填邀请码（之前注册过）
    const saved = getInviteCode();
    if (saved) inviteCode = saved;
  });

  async function handleSubmit() {
    if (!username.trim() || !password || loading) return;
    if (mode === 'register' && !inviteCode.trim()) {
      error = '注册需要邀请码';
      return;
    }
    loading = true;
    error = null;
    failCount = 0;
    try {
      if (mode === 'register') {
        await register(username.trim(), inviteCode.trim(), password);
        setInviteCode(inviteCode.trim());
        toast.success(`账户创建成功，${username.trim()}！`);
      } else {
        try {
          await login(username.trim(), password);
          toast.success(`欢迎回来，${username.trim()}！`);
        } catch (e: any) {
          // 错误细分
          if (e?.status === 404) {
            // 账户不存在 → 切到注册态
            mode = 'register';
            error = '账户不存在，请填写邀请码完成注册';
            toast.warning('请填写邀请码以注册新账户');
            return;
          } else if (e?.status === 429) {
            if (e?.data?.locked) {
              error = e.data.error;
              lockedUntil = Date.now() + (e.data.retry_after ?? 900) * 1000;
            } else if (e?.data?.retry_after) {
              error = e.data.error;
              lockedUntil = Date.now() + e.data.retry_after * 1000;
            } else {
              error = e.data?.error ?? '账户已锁定';
            }
            return;
          } else if (e?.status === 401) {
            error = e?.data?.error ?? '密码错误';
            failCount = e?.data?.fail_count ?? 0;
            return;
          } else {
            throw e;
          }
        }
      }
      const next = $page.url.searchParams.get('next') ?? '/';
      goto(next);
    } catch (e) {
      error = e instanceof Error ? e.message : '操作失败';
      toast.error(error);
    } finally {
      loading = false;
    }
  }

  function handleSwitchMode() {
    mode = mode === 'login' ? 'register' : 'login';
    error = null;
    failCount = 0;
  }

  async function handleGuest() {
    try {
      // 🆕 v2.7+: 先拿到真实 guest_id（后端 /api/menu 会幂等创建）
      // 这样后续 /api/archives 才能按 account_id 正确隔离存档
      await ensureGuestAccountId();
      setGuest();
      toast.success('以访客身份进入');
    } catch (e) {
      const msg = e instanceof Error ? e.message : '游客初始化失败';
      toast.error(msg);
      error = msg;
      return;
    }
    const next = $page.url.searchParams.get('next') ?? '/';
    goto(next);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }

  // 锁定倒计时
  function getLockSeconds(): number {
    if (!lockedUntil) return 0;
    return Math.max(0, Math.floor((lockedUntil - Date.now()) / 1000));
  }
  let lockSeconds = $state(0);
  $effect(() => {
    if (!lockedUntil) { lockSeconds = 0; return; }
    const t = setInterval(() => {
      lockSeconds = getLockSeconds();
      if (lockSeconds <= 0) clearInterval(t);
    }, 1000);
    return () => clearInterval(t);
  });
</script>

<svelte:head>
  <title>{mode === 'login' ? '登录' : '注册'} · 历史注脚</title>
</svelte:head>

<div class="login-page">
  <article class="login-card">
    <header class="login-header">
      <h1 class="login-title">历 史 注 脚</h1>
      <p class="login-subtitle">AI 驱动的明朝万历年间生存模拟</p>
    </header>

    <Divider variant="brush" spacing="md" />

    <Chapter title={mode === 'login' ? '登 录' : '注 册'} level={2} />

    <p class="login-hint">
      {#if mode === 'login'}
        已注册用户请直接登录。新用户请先"注册新账户"。
      {:else}
        填写用户名、邀请码和密码创建新账户。
        <br />
        <span class="login-hint-tip">测试邀请码：<code>INV-7L6Q-I3Y6</code></span>
      {/if}
    </p>

    <form
      class="login-form"
      onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}
    >
      <input
        type="text"
        class="login-input"
        placeholder="用户名（如：沈青山）"
        bind:value={username}
        onkeydown={handleKeydown}
        disabled={loading || lockSeconds > 0}
        maxlength="20"
        autocomplete="username"
      />

      {#if mode === 'register'}
        <input
          type="text"
          class="login-input login-input-invite"
          placeholder="邀请码（如：INV-XXXX-XXXX）"
          bind:value={inviteCode}
          onkeydown={handleKeydown}
          disabled={loading || lockSeconds > 0}
          maxlength="20"
          autocomplete="off"
        />
      {/if}

      <input
        type="password"
        class="login-input"
        placeholder="密码（至少 6 字符）"
        bind:value={password}
        onkeydown={handleKeydown}
        disabled={loading || lockSeconds > 0}
        maxlength="64"
        autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
      />

      {#if error}
        <div class="login-error" role="alert">
          <span class="login-error-icon" aria-hidden="true">⚠</span>
          <span>{error}</span>
          {#if mode === 'login' && error.includes('账户不存在')}
            <button type="button" class="login-error-link" onclick={handleSwitchMode}>
              立即注册 →
            </button>
          {/if}
        </div>
      {/if}

      <Button
        type="submit"
        variant="primary"
        size="lg"
        disabled={!username.trim() || !password || (mode === 'register' && !inviteCode.trim()) || loading || lockSeconds > 0}
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
        onclick={handleSwitchMode}
        disabled={loading}
      >
        {mode === 'login' ? '没有账户？立即注册' : '已有账户？返回登录'}
      </button>
    </form>

    <Divider variant="dashed" spacing="md" />

    <div class="login-guest">
      <p class="login-guest-hint">不想注册？</p>
      <Button
        variant="ghost"
        size="md"
        onclick={handleGuest}
        disabled={loading}
        fullWidth
      >
        以访客身份进入
      </Button>
      <p class="login-guest-note">
        访客模式：本地游戏，存档不上传云端
      </p>
    </div>
  </article>
</div>

<style>
  .login-page {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100%;
    padding: var(--space-4);
    background: var(--color-paper);
  }

  .login-card {
    width: 100%;
    max-width: 440px;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-fold);
    padding: var(--space-7) var(--space-6);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .login-header {
    text-align: center;
  }

  .login-title {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--color-cinnabar);
    margin: 0 0 var(--space-2);
    letter-spacing: var(--tracking-wide);
  }

  .login-subtitle {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0;
  }

  .login-hint {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: var(--leading-relaxed);
    margin: 0;
    text-align: center;
  }

  .login-hint-tip {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
  }

  .login-hint code {
    font-family: var(--font-numeric);
    padding: 1px 4px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
    color: var(--color-cinnabar);
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .login-input {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-family: var(--font-body);
    font-size: var(--text-md);
    color: var(--color-ink);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .login-input:focus {
    outline: none;
    border-color: var(--color-bronze);
    background: var(--color-paper);
    box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.1);
  }
  .login-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .login-input-invite {
    font-family: var(--font-numeric);
  }

  .login-error {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: rgba(160, 40, 40, 0.06);
    border: 1px solid var(--color-cinnabar);
    border-left-width: 3px;
    border-radius: var(--radius-sm);
    color: var(--color-cinnabar);
    font-family: var(--font-body);
    font-size: var(--text-sm);
  }

  .login-error-icon {
    font-size: var(--text-md);
  }

  .login-error-link {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--color-cinnabar);
    text-decoration: underline;
    cursor: pointer;
    font-family: inherit;
    font-size: inherit;
    padding: 0;
  }
  .login-error-link:hover {
    color: var(--color-cinnabar-dark, #8b1a1a);
  }

  .login-switch {
    background: none;
    border: none;
    color: var(--color-bronze-dark);
    text-decoration: underline;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    padding: var(--space-1) 0;
  }
  .login-switch:hover {
    color: var(--color-cinnabar);
  }
  .login-switch:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .login-guest {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .login-guest-hint {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    margin: 0;
  }

  .login-guest-note {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    margin: 0;
    font-style: italic;
  }
</style>
