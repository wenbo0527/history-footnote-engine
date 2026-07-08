<script lang="ts">
  /**
   * SettingsModal - 系统设置
   *
   * - 字号：S / M / L
   * - 动画：开 / 关
   * - 音效：开 / 关（占位）
   * - 暗色模式：开 / 关
   */
  import { browser } from '$app/environment';
  import { Chapter, Button, Seal, toast } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  let { open, onclose }: Props = $props();

  type FontSize = 'sm' | 'md' | 'lg';
  let fontSize = $state<FontSize>('md');
  let animation = $state(true);
  let sound = $state(false);
  let darkMode = $state(false);

  // 加载本地存储
  $effect(() => {
    if (!browser) return;
    const saved = localStorage.getItem('hfe_settings');
    if (saved) {
      try {
        const s = JSON.parse(saved);
        fontSize = s.fontSize ?? 'md';
        animation = s.animation ?? true;
        sound = s.sound ?? false;
        darkMode = s.darkMode ?? false;
      } catch { /* ignore */ }
    }
  });

  // 应用设置
  $effect(() => {
    if (!browser) return;
    document.documentElement.setAttribute('data-font-size', fontSize);
    document.documentElement.setAttribute('data-animation', String(animation));
    document.documentElement.setAttribute('data-sound', String(sound));
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
    // 保存
    localStorage.setItem('hfe_settings', JSON.stringify({
      fontSize, animation, sound, darkMode
    }));
  });

  function handleReset() {
    fontSize = 'md';
    animation = true;
    sound = false;
    darkMode = false;
    toast.info('已恢复默认设置');
  }
</script>

<ModalShell {open} {onclose} title="系 统 设 置" size="sm">
  <div class="settings-form">
    <section class="settings-section">
      <Chapter title="字号" level={3} />
      <div class="settings-options">
        {#each [['sm', '小'], ['md', '中'], ['lg', '大']] as opt (opt[0])}
          <button
            type="button"
            class="settings-option"
            class:settings-option-selected={fontSize === opt[0]}
            onclick={() => fontSize = opt[0] as FontSize}
          >{opt[1]}</button>
        {/each}
      </div>
    </section>

    <section class="settings-section">
      <Chapter title="动画" level={3} />
      <div class="settings-toggle">
        <button
          type="button"
          class="settings-switch"
          class:settings-switch-on={animation}
          onclick={() => animation = !animation}
          aria-pressed={animation}
          aria-label="动画"
        >
          <span class="settings-switch-knob"></span>
        </button>
        <span class="settings-toggle-label">{animation ? '已开启' : '已关闭'}</span>
      </div>
    </section>

    <section class="settings-section">
      <Chapter title="音效" level={3} />
      <div class="settings-toggle">
        <button
          type="button"
          class="settings-switch"
          class:settings-switch-on={sound}
          onclick={() => sound = !sound}
          aria-pressed={sound}
          aria-label="音效"
        >
          <span class="settings-switch-knob"></span>
        </button>
        <span class="settings-toggle-label">{sound ? '已开启' : '已关闭'}</span>
      </div>
      <p class="settings-hint">后续版本支持</p>
    </section>

    <section class="settings-section">
      <Chapter title="暗色模式" level={3} />
      <div class="settings-toggle">
        <button
          type="button"
          class="settings-switch"
          class:settings-switch-on={darkMode}
          onclick={() => darkMode = !darkMode}
          aria-pressed={darkMode}
          aria-label="暗色模式"
        >
          <span class="settings-switch-knob"></span>
        </button>
        <span class="settings-toggle-label">{darkMode ? '已开启' : '已关闭'}</span>
      </div>
      <p class="settings-hint">实验性功能</p>
    </section>
  </div>

  {#snippet footer()}
    <Button variant="ghost" onclick={handleReset}>恢复默认</Button>
    <Seal text="确 认" size="md" onclick={onclose} />
  {/snippet}
</ModalShell>

<style>
  .settings-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  .settings-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .settings-options {
    display: flex;
    gap: var(--space-2);
  }

  .settings-option {
    flex: 1 1 0;
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    color: var(--color-ink);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .settings-option:hover {
    background: var(--color-paper-aged);
  }
  .settings-option-selected {
    background: var(--color-paper-aged);
    border-color: var(--color-cinnabar);
    box-shadow: 0 0 0 1px var(--color-cinnabar);
  }

  .settings-toggle {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .settings-switch {
    position: relative;
    width: 48px;
    height: 24px;
    background: var(--color-ink-faint);
    border: none;
    border-radius: var(--radius-full);
    cursor: pointer;
    transition: background var(--duration-normal) var(--ease-ink);
  }
  .settings-switch-on {
    background: var(--color-success);
  }
  .settings-switch-knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: var(--color-paper);
    border-radius: 50%;
    box-shadow: var(--shadow-paper);
    transition: transform var(--duration-normal) var(--ease-ink);
  }
  .settings-switch-on .settings-switch-knob {
    transform: translateX(24px);
  }

  .settings-toggle-label {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
  }

  .settings-hint {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    font-style: italic;
    margin: 0;
  }
</style>
