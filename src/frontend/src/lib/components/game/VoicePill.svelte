<script lang="ts">
  /**
   * VoicePill - 单个声音选项胶囊（ActionPanel 子组件）
   *
   * 拆出理由：原 ActionPanel.svelte 674 行
   * - voice-pill 模板 42 行（行 217-258）+ 样式 ~100 行
   * - 拆出后主组件减少 ~140 行
   * - 单胶囊可独立复用（未来 NPC 列表 / 决策树）
   *
   * 🆕 v2.10.1 W52 P1-4A 拆分
   */
  import { VALUE_DIMENSION_META } from '$lib/api/types';
  import type { VoiceOption } from '$lib/api/types';

  interface Props {
    voice: VoiceOption;
    hoveredId: string | null;
    loading?: boolean;
    onselect: (voice: VoiceOption) => void;
    onhover: (id: string | null) => void;
  }

  let { voice, hoveredId, loading = false, onselect, onhover }: Props = $props();

  const dimMeta = $derived(voice.value_dimension ? VALUE_DIMENSION_META[voice.value_dimension] : null);
  const lv = $derived(voice.value_level ?? 0);
  const isHovered = $derived(hoveredId === voice.voice_id);
</script>

<button
  type="button"
  class="voice-pill"
  class:voice-pill-freetext={voice.is_freetext}
  class:voice-pill-loud={lv >= 4}
  style={dimMeta ? `--pill-color: ${dimMeta.color}` : ''}
  onmouseenter={() => onhover(voice.voice_id)}
  onmouseleave={() => onhover(null)}
  onclick={() => onselect(voice)}
  disabled={loading}
  title={voice.intent_text}
>
  <!-- 左侧色条 -->
  {#if dimMeta}
    <span class="voice-pill-bar" style="background: {dimMeta.color}" aria-hidden="true"></span>
  {/if}

  <!-- 声音名 + intent 缩略 -->
  <span class="voice-pill-main">
    <span class="voice-pill-name">{voice.voice_name}</span>
    <span class="voice-pill-intent">{voice.intent_text}</span>
  </span>

  <!-- 等级星（仅在 loud 时显示） -->
  {#if dimMeta && lv > 0}
    <span class="voice-pill-stars" style="color: {dimMeta.color}">
      {'★'.repeat(lv)}
    </span>
  {/if}

  <!-- hover 浮层：内心独白 -->
  {#if voice.inner_voice && isHovered}
    <span
      class="voice-pill-popover"
      style={dimMeta ? `border-left-color: ${dimMeta.color}` : ''}
    >
      <span class="voice-pill-popover-mark" aria-hidden="true">💭</span>
      {voice.inner_voice}
    </span>
  {/if}
</button>

<style>
  .voice-pill {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: 100px;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
    white-space: nowrap;
    max-width: 280px;
    flex: 0 0 auto;
  }
  .voice-pill:hover:not(:disabled) {
    background: var(--color-paper-aged);
    border-color: var(--pill-color, var(--color-bronze));
    transform: translateY(-1px);
    box-shadow: var(--shadow-1);
  }
  .voice-pill:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* 左侧色条 */
  .voice-pill-bar {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    border-radius: 100px 0 0 100px;
  }

  /* 自由心声样式 */
  .voice-pill-freetext {
    background: var(--color-paper-aged);
    border-color: var(--color-bronze);
    font-style: italic;
  }

  /* loud 等级 */
  .voice-pill-loud {
    border-width: 2px;
    box-shadow: 0 0 0 1px var(--pill-color, var(--color-bronze));
  }

  .voice-pill-main {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    min-width: 0;
  }
  .voice-pill-name {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }
  .voice-pill-intent {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }

  .voice-pill-stars {
    font-size: 10px;
    letter-spacing: 1px;
    flex: 0 0 auto;
  }

  /* hover 浮层：内心独白 */
  .voice-pill-popover {
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-top: var(--space-1);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-left: 3px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-2);
    font-size: var(--text-xs);
    color: var(--color-ink);
    line-height: 1.5;
    white-space: normal;
    width: 240px;
    z-index: 10;
  }
  .voice-pill-popover-mark {
    color: var(--color-bronze-dark);
    margin-right: 4px;
  }
</style>