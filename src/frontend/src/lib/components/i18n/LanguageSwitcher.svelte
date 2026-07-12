<!--
  🆕 v2.10.1 W66: LanguageSwitcher 组件
  
  中/英切换 + 显示当前 locale flag
-->
<script lang="ts">
  import { locale, setLocale, LOCALE_FLAGS, LOCALE_LABELS, SUPPORTED_LOCALES, type Locale } from '$lib/i18n';

  function onChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    setLocale(target.value as Locale);
  }
</script>

<div class="language-switcher" aria-label="语言切换">
  <span class="language-switcher-icon">🌐</span>
  <select class="language-switcher-select" value={$locale} onchange={onChange} aria-label="选择语言">
    {#each SUPPORTED_LOCALES as l (l)}
      <option value={l}>{LOCALE_FLAGS[l]} {LOCALE_LABELS[l]}</option>
    {/each}
  </select>
</div>

<style>
  .language-switcher {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1, 4px);
    padding: 2px 8px;
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(143, 75, 40, 0.2);
    border-radius: var(--radius-sm, 4px);
  }
  .language-switcher-icon {
    font-size: 14px;
  }
  .language-switcher-select {
    font-family: var(--font-body);
    font-size: var(--text-xs, 11px);
    color: var(--color-ink, #2a1a0a);
    background: transparent;
    border: 0;
    cursor: pointer;
    padding: 2px 4px;
  }
  .language-switcher-select:focus {
    outline: 1px solid var(--color-bronze, #8f4b28);
  }
</style>
