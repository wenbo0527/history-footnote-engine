<script lang="ts">
  /**
   * Chapter 章节标题
   *
   * 🆕 v2.7+ 新增回字纹 SVG 装饰（meander）：
   * - meander 用真正的 SVG 路径，比 emoji 字符更精致
   * - 其他 ornament 仍保留字符方案（向后兼容）
   *
   * ornament:
   *   - meander  回字纹 SVG（🆕 v2.7+ 推荐）
   *   - flower   ❀
   *   - scroll   ╠═╣
   *   - dot      • • •
   *   - none     无装饰
   */
  interface Props {
    title: string;
    ornament?: 'meander' | 'flower' | 'scroll' | 'dot' | 'none';
    level?: 1 | 2 | 3 | 4;
  }

  let { title, ornament = 'meander', level = 2 }: Props = $props();

  const ornamentMap = {
    meander: null as null,  // 走 SVG 分支
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
  {#if ornament !== 'none' && ornament !== 'meander'}
    <span class="chapter-deco chapter-deco-left" aria-hidden="true">
      {ornamentMap[ornament]}
    </span>
  {/if}
  {#if ornament === 'meander'}
    <!-- 🆕 v2.7+ 回字纹 SVG -->
    <svg class="chapter-meander left" viewBox="0 0 40 12" aria-hidden="true">
      <path d="M0 6 L8 6 L8 0 L12 0 L12 12 L16 12 L16 0 L20 0 L20 6 L40 6
               M0 6 L8 6 L8 12 L12 12 L12 0 L16 0 L16 12 L20 12 L20 6 L40 6"
            fill="none" stroke="currentColor" stroke-width="1"/>
    </svg>
  {/if}
  <h2 class="chapter-title">{title}</h2>
  {#if ornament !== 'none' && ornament !== 'meander'}
    <span class="chapter-deco chapter-deco-right" aria-hidden="true">
      {ornamentMap[ornament]}
    </span>
  {/if}
  {#if ornament === 'meander'}
    <svg class="chapter-meander right" viewBox="0 0 40 12" aria-hidden="true">
      <path d="M40 6 L32 6 L32 0 L28 0 L28 12 L24 12 L24 0 L20 0 L20 6 L0 6
               M40 6 L32 6 L32 12 L28 12 L28 0 L24 0 L24 12 L20 12 L20 6 L0 6"
            fill="none" stroke="currentColor" stroke-width="1"/>
    </svg>
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
    flex: 0 0 auto;
  }

  /* 🆕 v2.7+ 回字纹 SVG 装饰 */
  .chapter-meander {
    width: 40px;
    height: 12px;
    flex-shrink: 0;
    color: var(--color-bronze);
    opacity: 0.5;
  }
  .chapter-meander.right { transform: scaleX(-1); }

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
</style>
