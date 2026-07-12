<script lang="ts">
  /**
   * StartMenuCard - 首页通用卡片（StartMenu 子组件）
   *
   * 拆出理由：原 StartMenu.svelte 556 行
   * - 3 处 .start-menu-card（开始 / 账户 / 设置）
   * - 拆出后主组件减少 ~50 行
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import type { Snippet } from 'svelte';

  interface Props {
    iconSrc?: string;       // 图标 URL（webp）— 与 iconEmoji 二选一
    iconEmoji?: string;     // 图标 emoji — 与 iconSrc 二选一
    title: string;
    description?: string | Snippet;
    primary?: boolean;      // 主要卡片（如"开始新游戏"）— 突出样式
    action?: Snippet;       // 底部操作区（按钮/seal）
  }

  let { iconSrc, iconEmoji, title, description, primary = false, action }: Props = $props();
</script>

<div class="start-menu-card" class:start-menu-card-primary={primary}>
  {#if iconSrc}
    <img src={iconSrc} alt="" class="start-menu-card-icon" />
  {:else if iconEmoji}
    <div class="start-menu-card-icon">{iconEmoji}</div>
  {/if}
  <h2 class="start-menu-card-title">{title}</h2>
  <p class="start-menu-card-desc">
    <!-- 🆕 v2.10.2 fix: description 是 optional，未传时跳过 -->
    {#if description !== undefined}
      {#if typeof description === 'string'}
        {description}
      {:else}
        {@render description()}
      {/if}
    {/if}
  </p>
  {#if action}
    <div class="start-menu-card-action">
      {@render action()}
    </div>
  {/if}
</div>

<style>
  .start-menu-card {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding: var(--space-4);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-md);
    transition: all var(--duration-normal) var(--ease-ink);
    box-shadow: var(--shadow-1);
  }
  .start-menu-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-2);
  }

  /* 主卡片样式（如"开始新游戏"）— 朱砂边框突出 */
  .start-menu-card-primary {
    background: linear-gradient(135deg, var(--color-paper) 0%, rgba(165, 40, 40, 0.04) 100%);
    border-color: var(--color-cinnabar);
    border-width: 2px;
  }
  .start-menu-card-primary:hover {
    border-color: var(--color-cinnabar);
    background: linear-gradient(135deg, var(--color-paper-aged) 0%, rgba(165, 40, 40, 0.08) 100%);
  }

  .start-menu-card-icon {
    width: 48px;
    height: 48px;
    margin-bottom: var(--space-2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
    object-fit: contain;
  }

  .start-menu-card-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    color: var(--color-ink);
    font-weight: 600;
    margin: 0 0 var(--space-2);
  }

  .start-menu-card-desc {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: 1.6;
    margin: 0 0 var(--space-3);
    flex: 1 1 auto;
  }

  .start-menu-card-hint {
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    font-style: italic;
  }

  .start-menu-card-action {
    margin-top: auto;
  }
</style>