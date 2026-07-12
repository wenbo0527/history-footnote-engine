<script lang="ts">
  /**
   * Divider 分割线
   *
   * variant:
   *   - solid   实线
   *   - dashed  虚线
   *   - dotted  点线
   *   - center  居中文字（带卷草纹）
   *   - seal    朱砂色印章分割
   *   - brush   🆕 毛笔笔触分割
   */
  interface Props {
    variant?: 'solid' | 'dashed' | 'dotted' | 'center' | 'seal' | 'brush';
    text?: string;          // center / seal 变体
    spacing?: 'sm' | 'md' | 'lg';
  }

  let { variant = 'solid', text, spacing = 'md' }: Props = $props();
</script>

{#if variant === 'center' || variant === 'seal'}
  <div
    class="divider divider-center"
    class:divider-seal={variant === 'seal'}
    data-spacing={spacing}
  >
    <span class="divider-line"></span>
    <span class="divider-text">{text}</span>
    <span class="divider-line"></span>
  </div>
{:else}
  <hr class="divider divider-line-only" data-variant={variant} data-spacing={spacing} />
{/if}

<style>
  .divider {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    border: none;
  }
  .divider[data-spacing='sm'] { margin: var(--space-3) 0; }
  .divider[data-spacing='md'] { margin: var(--space-5) 0; }
  .divider[data-spacing='lg'] { margin: var(--space-7) 0; }

  /* line-only */
  .divider-line-only {
    height: 1px;
    background: var(--color-ink-faint);
    width: 100%;
  }
  .divider-line-only[data-variant='dashed'] {
    background: none;
    border-top: 1px dashed var(--color-ink-faint);
  }
  .divider-line-only[data-variant='dotted'] {
    background: none;
    border-top: 1px dotted var(--color-ink-faint);
  }
  /* 🆕 brush: 毛笔笔触分割（不规则粗细） */
  .divider-line-only[data-variant='brush'] {
    background: none;
    height: 8px;
    background-image: linear-gradient(
      90deg,
      transparent 0%,
      var(--color-ink) 5%,
      var(--color-ink) 25%,
      var(--color-ink-light) 50%,
      var(--color-ink) 75%,
      var(--color-ink) 95%,
      transparent 100%
    );
    opacity: 0.6;
    border-radius: 50%;
  }

  /* center / seal */
  .divider-line {
    flex: 1 1 0;
    height: 1px;
    background: linear-gradient(
      to right,
      transparent,
      var(--color-ink-faint) 20%,
      var(--color-ink-faint) 80%,
      transparent
    );
  }

  .divider-text {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    letter-spacing: var(--tracking-wide);
    padding: 0 var(--space-2);
    flex: 0 0 auto;
  }

  /* seal: 朱砂色文字 + 朱砂线 */
  .divider-seal .divider-text {
    color: var(--color-cinnabar);
    font-weight: 600;
    letter-spacing: var(--tracking-mega);
    text-transform: uppercase;
  }
  .divider-seal .divider-line {
    background: linear-gradient(
      to right,
      transparent,
      var(--color-cinnabar) 20%,
      var(--color-cinnabar) 80%,
      transparent
    );
  }
</style>
