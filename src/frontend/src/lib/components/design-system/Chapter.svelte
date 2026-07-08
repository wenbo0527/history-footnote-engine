<script lang="ts">
  /**
   * Chapter 章节标题
   *
   * 国风特色：❀ 卷草纹装饰 + 居中 + 大量留白
   * 用于 narrative 章节分隔
   *
   * ornament:
   *   - flower   ❀（默认）
   *   - scroll   ╠═╣
   *   - dot      • • •
   *   - none     无装饰
   */
  interface Props {
    title: string;
    ornament?: 'flower' | 'scroll' | 'dot' | 'none';
    level?: 1 | 2 | 3 | 4;
  }

  let { title, ornament = 'flower', level = 2 }: Props = $props();

  const ornamentMap = {
    flower: '❀',
    scroll: '╠═',
    dot: '• • •',
    none: ''
  };
</script>

<header
  class="chapter"
  class:chapter-h1={level === 1}
  class:chapter-h2={level === 2}
  class:chapter-h3={level === 3}
  class:chapter-h4={level === 4}
>
  {#if ornament !== 'none'}
    <span class="chapter-deco chapter-deco-left" aria-hidden="true">
      {ornamentMap[ornament]}
    </span>
  {/if}
  <h2 class="chapter-title">{title}</h2>
  {#if ornament !== 'none'}
    <span class="chapter-deco chapter-deco-right" aria-hidden="true">
      {ornamentMap[ornament]}
    </span>
  {/if}
</header>

<style>
  .chapter {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-4);
    margin: var(--space-7) auto var(--space-5);
    text-align: center;
    max-width: 36em;
    width: 100%;
  }

  .chapter-deco {
    color: var(--color-bronze);
    font-size: var(--text-sm);
    letter-spacing: var(--tracking-wide);
    opacity: 0.7;
    user-select: none;
  }

  .chapter-title {
    font-family: var(--font-display);
    font-weight: 600;
    color: var(--color-ink);
    line-height: var(--leading-snug);
    margin: 0;
  }

  /* Levels */
  .chapter-h1 .chapter-title {
    font-size: var(--text-2xl);
    letter-spacing: var(--tracking-wide);
  }
  .chapter-h2 .chapter-title {
    font-size: var(--text-xl);
    letter-spacing: var(--tracking-wide);
  }
  .chapter-h3 .chapter-title {
    font-size: var(--text-lg);
    letter-spacing: var(--tracking-cjk);
  }
  .chapter-h4 .chapter-title {
    font-size: var(--text-md);
    letter-spacing: var(--tracking-cjk);
  }

  /* 装饰：流体感 */
  .chapter-deco {
    flex: 0 0 auto;
  }
</style>
