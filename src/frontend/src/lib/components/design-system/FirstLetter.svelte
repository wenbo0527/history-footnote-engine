<script lang="ts">
  /**
   * FirstLetter 首字下沉
   *
   * 中文段落第一个字放大 + 朱砂色（国风特色）
   * 用于 narrative 章节第一段
   */
  import type { Snippet } from 'svelte';

  interface Props {
    size?: 'sm' | 'md' | 'lg';
    children: Snippet;
  }

  let { size = 'md', children }: Props = $props();
</script>

<p class="first-letter" data-size={size}>
  {@render children()}
</p>

<style>
  .first-letter {
    margin: 0 auto;        /* 🆕 居中 */
    max-width: 36em;       /* 🆕 与 narrative-block 一致 */
    width: 100%;
  }
  .first-letter::first-letter {
    font-family: var(--font-display);
    color: var(--color-cinnabar);
    font-weight: 700;
    float: left;
    line-height: 0.9;
    margin-right: 0.1em;
    margin-top: 0.05em;
  }

  .first-letter[data-size='sm']::first-letter {
    font-size: 1.8em;
  }
  .first-letter[data-size='md']::first-letter {
    font-size: 2.5em;
  }
  .first-letter[data-size='lg']::first-letter {
    font-size: 3.2em;
    margin-right: 0.12em;
  }
</style>
