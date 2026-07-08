<script lang="ts">
  /**
   * SkipLink - 跳过导航
   *
   * a11y：键盘用户按 Tab 第一个元素就是"跳到主要内容"
   */
  interface Props {
    href?: string;
    label?: string;
  }

  let { href = '#main-content', label = '跳到主要内容' }: Props = $props();
</script>

<a {href} class="skip-link">{label}</a>

<style>
  .skip-link {
    position: absolute;
    top: -40px;
    left: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: var(--color-cinnabar);
    color: var(--color-paper);
    text-decoration: none;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 600;
    border-radius: var(--radius-sm);
    z-index: var(--z-tooltip);
    transition: top var(--duration-quick) var(--ease-ink);
  }

  .skip-link:focus {
    top: var(--space-3);
  }
</style>
