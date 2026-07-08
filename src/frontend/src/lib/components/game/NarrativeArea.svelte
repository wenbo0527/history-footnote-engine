<script lang="ts">
  /**
   * NarrativeArea - 叙事文学化
   *
   * 国风特色：
   *   - 章节标题（Chapter 装饰 ❀）
   *   - 首字下沉（朱砂色）
   *   - 行高 1.9（中文呼吸感）
   *   - max-width 32em（中文 32 字/行）
   *
   * 数据：narrative.content 是 markdown 或纯文本
   * 这里用简单的段落分割（双换行） + 简单首字下沉
   */
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

  // 派生：解析 narrative.content 为段落
  // 简单处理：按双换行分割，去除空段
  const paragraphs = $derived.by(() => {
    if (!narrative?.content) return [] as string[];
    return narrative.content
      .split(/\n{2,}/)
      .map(p => p.trim())
      .filter(p => p.length > 0);
  });

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
    if (autoScroll && containerEl && paragraphs.length > 0) {
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
    {#if paragraphs.length > 0}
      {#each paragraphs as p, i (i)}
        {#if i === 0}
          <div class="narrative-header">
            <Chapter title="第 {narrative.round} 回合" level={2} />
            {#if game}
              <ShareCardButton {game} narrative={narrative.content} />
            {/if}
          </div>
          <FirstLetter>
            {p}
          </FirstLetter>
        {:else}
          <p class="narrative-block">{p}</p>
        {/if}
      {/each}
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
