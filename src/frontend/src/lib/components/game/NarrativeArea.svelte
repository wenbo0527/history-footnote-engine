<script lang="ts">
  /**
   * NarrativeArea - 叙事文学化（v2.5 markdown 渲染）
   *
   * 国风特色：
   *   - 章节标题（Chapter 装饰 ❀）
   *   - 首字下沉（朱砂色）
   *   - 行高 1.9（中文呼吸感）
   *   - max-width 36em（中文 32-36 字/行）
   *
   * 🆕 v2.5: markdown 渲染
   *   - 解析：表格 / 加粗 / 分隔线 / 标题 / 引用 / 列表
   *   - 表格：让王牙人给的三条路真的能读
   *   - 段间双换行：分割段落
   *   - 第一段用 FirstLetter
   */
  import { marked } from 'marked';
  import { Chapter, FirstLetter } from '$lib/components/design-system';
  import type { Narrative, GameState } from '$lib/api/types';
  import ShareCardButton from './ShareCardButton.svelte';

  interface Props {
    narrative: Narrative | null;
    game?: GameState | null;  // 🆕 v2.1: 用于金句截图
    autoScroll?: boolean;
  }

  let { narrative, game = null, autoScroll = true }: Props = $props();

  let containerEl: HTMLElement | undefined = $state();

  // 🆕 v2.5 markdown 解析
  // 配置 marked：GFM 表格 + 换行 → <br> + 安全
  marked.setOptions({
    gfm: true,
    breaks: true,
    pedantic: false,
  });

  /**
   * v2.5 解析 narrative.content 为结构化段落
   *
   * 策略：
   *   1. 按双换行分割
   *   2. 每段用 marked 解析（表格/加粗/分隔线都正确渲染）
   *   3. 第一段特殊处理：纯文本用 FirstLetter；有 markdown 标记直接用 marked
   */
  const parsedParagraphs = $derived.by(() => {
    if (!narrative?.content) return [] as { html: string; isFirst: boolean; isMarkdown: boolean }[];
    return narrative.content
      .split(/\n{2,}/)
      .map(p => p.trim())
      .filter(p => p.length > 0)
      .map((p, i) => {
        const isFirst = i === 0;
        // 检测是否含 markdown 标记
        const isMarkdown = /[|*_#`>|~-]/.test(p) || p.includes('---') || p.includes('|');
        if (isFirst && !isMarkdown) {
          // 首段纯文本：留给 FirstLetter 组件处理（不渲染 markdown）
          return { html: p, isFirst: true, isMarkdown: false };
        }
        // 渲染 markdown
        const html = marked.parse(p, { async: false }) as string;
        return { html, isFirst, isMarkdown: true };
      });
  });

  /** v2.5 旧版 paragraphs 仅用于 FirstLetter（首段纯文本） */
  const firstParagraphText = $derived(
    parsedParagraphs.length > 0 && parsedParagraphs[0].isFirst
      ? parsedParagraphs[0].html
      : ''
  );
  const restParagraphs = $derived(
    parsedParagraphs.slice(parsedParagraphs[0]?.isFirst ? 1 : 0)
  );

  /**
   * v2.1 重大重构：内心独白从叙事中移除
   *
   * 原设计：叙事中独立标"内"+ 单独的选项卡 = 两个心智模型，玩家点 2 次
   * v2.1：内心独白合并到 ActionPanel 的选项卡上（DE 思想内阁式）
   *   - 选显卡左侧色条 = 价值维度
   *   - 选显卡底部 italic 文本 = 选这个时的内心独白
   *   - 选显卡上方 5 维雷达条 = 当前各维度的"响亮度"
   *
   * 叙事正文回归"过日子感"：写场景、写对话、写细节，不再有"内"标打断节奏
   */
  // （isInnerVoice / voiceFlags 已删除——叙事不再独立标内心戏）

  // 自动滚动到底部
  $effect(() => {
    if (autoScroll && containerEl && parsedParagraphs.length > 0) {
      // 等 DOM 更新后滚
      requestAnimationFrame(() => {
        if (containerEl) {
          containerEl.scrollTo({ top: containerEl.scrollHeight, behavior: 'smooth' });
        }
      });
    }
  });
</script>

<article class="narrative-area" bind:this={containerEl as HTMLElement}>
  {#if narrative}
    {#if parsedParagraphs.length > 0}
      <!-- 🆕 v2.5: 标题 + 金句按钮（只首段上方） -->
      {#if parsedParagraphs[0]?.isFirst}
        <div class="narrative-header">
          <Chapter title="第 {narrative.round} 回合" level={2} />
          {#if game}
            <ShareCardButton {game} narrative={narrative.content} />
          {/if}
        </div>
        <!-- 首段纯文本：FirstLetter（带首字下沉） -->
        <FirstLetter>
          {firstParagraphText}
        </FirstLetter>
      {/if}

      <!-- 剩余段落：每段渲染 markdown -->
      {#each restParagraphs as p, i (i)}
        <div class="narrative-block narrative-markdown">
          {@html p.html}
        </div>
      {/each}

      <!-- 兜底：如果第一段本身是 markdown（不是纯文本），补一个 header -->
      {#if !parsedParagraphs[0]?.isFirst}
        <div class="narrative-header">
          <Chapter title="第 {narrative.round} 回合" level={2} />
          {#if game}
            <ShareCardButton {game} narrative={narrative.content} />
          {/if}
        </div>
        <div class="narrative-block narrative-markdown">
          {@html parsedParagraphs[0].html}
        </div>
      {/if}
    {:else}
      <p class="narrative-empty">暂无叙事内容</p>
    {/if}
  {:else}
    <p class="narrative-empty">游戏尚未开始</p>
  {/if}
</article>

<style>
  .narrative-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    margin: 0 auto var(--space-3);
    max-width: 36em;
    width: 100%;
  }

  .narrative-header > :global(.chapter) {
    flex: 1 1 auto;
    margin: 0;
  }

  .narrative-area {
    background: var(--color-paper);
    border-radius: var(--radius-md);
    padding: var(--space-6) var(--space-5);
  }

  /* 🆕 v2.0 墨水晕染动画 */
  .narrative-block {
    animation: hf-ink-emerge var(--duration-slow) var(--ease-ink) both;
  }

  .narrative-block:nth-child(1) { animation-delay: 0ms; }
  .narrative-block:nth-child(2) { animation-delay: 100ms; }
  .narrative-block:nth-child(3) { animation-delay: 200ms; }
  .narrative-block:nth-child(4) { animation-delay: 300ms; }
  .narrative-block:nth-child(5) { animation-delay: 400ms; }
  .narrative-block:nth-child(6) { animation-delay: 500ms; }

  .narrative-block {
    font-family: var(--font-body);
    font-size: var(--text-md);
    line-height: var(--leading-relaxed);
    letter-spacing: var(--tracking-cjk);
    color: var(--color-ink);
    margin: 0 auto var(--space-5);  /* 🆕 居中（之前只有 max-width 没有 margin auto，所以贴左） */
    text-indent: 2em;
    max-width: 36em;  /* 中文阅读最优 32-40 字 */
    width: 100%;
  }

  /* 窄屏：撑满 */
  @media (max-width: 600px) {
    .narrative-block {
      max-width: 100%;
    }
  }

  /* 中等宽屏：稍宽 */
  @media (min-width: 1200px) {
    .narrative-block {
      max-width: 42em;
    }
  }

  .narrative-block:last-child {
    margin-bottom: 0;
  }

  /* 🆕 v2.5 markdown 渲染样式 */
  .narrative-markdown {
    line-height: var(--leading-relaxed);
  }

  .narrative-markdown :global(p) {
    margin: 0 0 var(--space-3);
    text-indent: 2em;
  }

  .narrative-markdown :global(strong) {
    color: var(--color-cinnabar);
    font-weight: 700;
  }

  .narrative-markdown :global(em) {
    color: var(--color-bronze-dark);
    font-style: italic;
  }

  .narrative-markdown :global(hr) {
    border: none;
    text-align: center;
    margin: var(--space-4) 0;
    color: var(--color-bronze);
  }
  .narrative-markdown :global(hr)::before {
    content: '—— ❀ ——';
    letter-spacing: var(--tracking-wide);
  }

  .narrative-markdown :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: var(--space-3) 0;
    font-size: var(--text-sm);
    font-family: var(--font-body);
  }

  .narrative-markdown :global(th),
  .narrative-markdown :global(td) {
    border: 1px solid var(--color-bronze);
    padding: 6px 10px;
    text-align: left;
  }

  .narrative-markdown :global(th) {
    background: var(--color-paper-aged);
    color: var(--color-bronze-dark);
    font-family: var(--font-display);
    font-weight: 600;
  }

  .narrative-markdown :global(ul),
  .narrative-markdown :global(ol) {
    margin: var(--space-2) 0;
    padding-left: var(--space-5);
  }

  .narrative-markdown :global(li) {
    margin: 4px 0;
    text-indent: 0;
  }

  .narrative-markdown :global(blockquote) {
    margin: var(--space-3) 0;
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper-aged);
    border-left: 3px solid var(--color-bronze);
    color: var(--color-ink-light);
    font-style: italic;
  }

  .narrative-markdown :global(code) {
    font-family: var(--font-numeric);
    background: var(--color-paper-aged);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 0.9em;
  }

  .narrative-empty {
    text-align: center;
    color: var(--color-ink-faint);
    font-style: italic;
    padding: var(--space-7);
  }

  /* 移动端 */
  @media (max-width: 767px) {
    .narrative-area {
      padding: var(--space-4) var(--space-3);
    }
    .narrative-block {
      line-height: var(--leading-loose);
    }
  }
</style>
