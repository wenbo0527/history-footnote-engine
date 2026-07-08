<script lang="ts">
  /**
   * GameToolbar - 游戏页工具栏
   *
   * 显示在 GameHeader 内（或独立浮动）的 4 个按钮：
   *   - 📜 档案（人物 Wiki）
   *   - 🔄 回顾（剧情回顾）
   *   - 📖 词条（词条查询）
   *   - 💬 反馈（反馈表单）
   *   - ⚙️ 设置
   */
  interface Props {
    onwiki?: () => void;
    onrecap?: () => void;
    onglossary?: () => void;
    onfeedback?: () => void;
    onsettings?: () => void;
  }

  let { onwiki, onrecap, onglossary, onfeedback, onsettings }: Props = $props();

  const tools = $derived([
    { id: 'wiki',      label: '档案', icon: '📜', onclick: onwiki },
    { id: 'recap',     label: '回顾', icon: '🔄', onclick: onrecap },
    { id: 'glossary',  label: '词条', icon: '📖', onclick: onglossary },
    { id: 'feedback',  label: '反馈', icon: '💬', onclick: onfeedback },
    { id: 'settings',  label: '设置', icon: '⚙️', onclick: onsettings }
  ]);
</script>

<div class="game-toolbar">
  {#each tools as t (t.id)}
    <button
      type="button"
      class="game-tool"
      onclick={t.onclick}
      aria-label={t.label}
      title={t.label}
    >
      <span class="game-tool-icon" aria-hidden="true">{t.icon}</span>
      <span class="game-tool-label">{t.label}</span>
    </button>
  {/each}
</div>

<style>
  .game-toolbar {
    display: flex;
    gap: var(--space-1);
    padding: var(--space-1);
    background: rgba(245, 239, 225, 0.1);
    border: 1px solid rgba(245, 239, 225, 0.2);
    border-radius: var(--radius-md);
  }

  .game-tool {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-2);
    background: none;
    border: none;
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-paper);
    cursor: pointer;
    transition: all var(--duration-quick) var(--ease-ink);
  }
  .game-tool:hover {
    background: rgba(245, 239, 225, 0.15);
    color: var(--color-bronze-light);
  }

  .game-tool-icon {
    font-size: var(--text-base);
  }

  /* 移动端：只显示图标 */
  @media (max-width: 767px) {
    .game-tool-label {
      display: none;
    }
  }
</style>
