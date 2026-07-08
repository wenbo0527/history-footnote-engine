<script lang="ts">
  /**
   * Reveal - 滚动进入视口时淡入
   *
   * 用 IntersectionObserver 实现：
   *   - 元素进入视口时添加 .hf-revealed class
   *   - 离开视口时移除（可重新触发动画）
   *
   * 用途：narrative 段落、timeline 列表、archive 卡片等
   */
  import { onMount } from 'svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    /** 重复触发：默认 false（动画只触发一次）*/
    repeat?: boolean;
    /** 视口比例阈值 */
    threshold?: number;
    /** 自定义 class */
    class?: string;
    children: Snippet;
  }

  let {
    repeat = false,
    threshold = 0.1,
    class: className = '',
    children
  }: Props = $props();

  let el: HTMLDivElement | undefined = $state();
  let revealed = $state(false);

  onMount(() => {
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      revealed = true;
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            revealed = true;
            if (!repeat) observer.disconnect();
          } else if (repeat) {
            revealed = false;
          }
        }
      },
      { threshold }
    );

    observer.observe(el);

    return () => observer.disconnect();
  });
</script>

<div
  bind:this={el}
  class="hf-reveal {className}"
  class:hf-revealed={revealed}
>
  {@render children()}
</div>
