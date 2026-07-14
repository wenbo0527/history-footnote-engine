<script lang="ts">
  /**
   * ActionPanel - 豆包式横向行动条（v2.2 重构）
   *
   * 布局（参考豆包 AI 对话）：
   *   ┌──────────────────────────────────────────┐
   *   │ [输入框...........................] [发送]│  ← 输入条
   *   ├──────────────────────────────────────────┤
   *   │  💭 脑海中的声音                          │
   *   │  [横向胶囊×4] [▾更多] [✍自由心声]         │  ← 横向选项条
   *   └──────────────────────────────────────────┘
   *
   * 关键设计：
   *   - 横向胶囊：高度 ≤ 56px，可滚动横向溢出
   *   - 价值维度用左侧 3px 细色条表示（不抢主色）
   *   - 内心独白 hover 才展开（默认折叠，节省空间）
   *   - 自由心声合并到输入条右侧的"✍"按钮
   *   - 输入条固定在叙事下方（叙事可独立滚动）
   */
  import type { VoiceOption, ValueDimension } from '$lib/api/types';
  import { VALUE_DIMENSION_META } from '$lib/api/types';
  import { toast } from '$lib/components/design-system/Toast.svelte';
  import VoicePill from './VoicePill.svelte';

  interface Props {
    voices: VoiceOption[];
    /** 当前各价值维度的等级（1-5） */
    valueLevels?: Partial<Record<Exclude<ValueDimension, null>, number>>;
    /** 会话 id（用于"换一批"调用 /api/voice_options/suggest） */
    sessionId?: string;
    onselect: (voice: VoiceOption) => void;
    onfreetext: (text: string) => void;
    /** 当 suggestVoices 拉回新选项时回调（让 GameView 更新 game state） */
    onrefresh?: (newVoices: VoiceOption[]) => void;
    loading?: boolean;
  }

  let { voices, valueLevels = {}, sessionId, onselect, onfreetext, onrefresh, loading = false }: Props = $props();

  // "换一批" 状态
  let refreshing = $state(false);
  let lastRefreshAt = $state<number>(0);

  async function handleRefresh() {
    if (refreshing || loading || !sessionId) return;
    // 节流：至少间隔 5 秒
    if (Date.now() - lastRefreshAt < 5000) {
      toast.warning('等等，DM 正在想……');
      return;
    }
    refreshing = true;
    lastRefreshAt = Date.now();
    try {
      const { suggestVoices } = await import('$lib/api/input');
      const newVoices = await suggestVoices({ session_id: sessionId });
      if (newVoices.length > 0) {
        onrefresh?.(newVoices);
        toast.success('换了一组声音');
      } else {
        toast.warning('没有更多主意了，试试自由输入');
      }
    } catch (e) {
      toast.error('换一批失败：' + (e instanceof Error ? e.message : '未知错误'));
    } finally {
      refreshing = false;
    }
  }

  // 自由输入（默认折叠）
  let freetextMode = $state(false);
  let text = $state('');

  // hover 状态：哪个胶囊被 hover（显示内心独白）
  let hoveredId = $state<string | null>(null);

  // 客户端预检
  const ACTION_CHARS = "去做开打买卖织想说看听问要绣食查察寻赶冲回";
  function clientValidate(t: string): string | null {
    if (!t || !t.trim()) return '你似乎还没输入什么';
    if (t.length > 200) return '内容超过 200 字，请精简';
    if (t.length <= 2 && /^[\u4e00-\u9fa5]+$/.test(t)) {
      if (![...t].some(c => ACTION_CHARS.includes(c))) {
        return `「${t}」意思太模糊了，请用完整句子`;
      }
    }
    return null;
  }

  function handleSend() {
    if (loading) return;
    const err = clientValidate(text);
    if (err) { toast.warning(err); return; }
    onfreetext(text.trim());
    text = '';
    freetextMode = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    // 🆕 v2.10.1 W79: Enter 直接发送（玩家预期）
    // 之前要求 Ctrl/⌘+Enter 但 placeholder 写"按 Enter 发送" → 体验错位
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === 'Escape' && freetextMode) {
      freetextMode = false;
      text = '';
    }
  }

  // 5 维顺序
  const DIM_ORDER: Array<Exclude<ValueDimension, null>> = [
    'tradition_vs_change',
    'duty_vs_freedom',
    'pragmatism_vs_idealism',
    'independence_vs_network',
    'acceptance_vs_resistance'
  ];
</script>

<section class="action-panel">
  <!-- 输入条（固定在叙事下方） -->
  <div class="input-bar" class:input-bar-freetext={freetextMode}>
    {#if !freetextMode}
      <!-- 默认模式：单行输入 + 发送 -->
      <div class="input-bar-row">
        <button
          type="button"
          class="input-bar-freetext-btn"
          onclick={() => (freetextMode = true)}
          disabled={loading}
          title="展开自由心声（多行输入）"
          aria-label="展开自由心声"
        >✍</button>
        <input
          class="input-bar-field"
          type="text"
          bind:value={text}
          onkeydown={handleKeydown}
          placeholder="你想做些什么？……（按 Enter 发送，Shift+Enter 换行）"
          maxlength="200"
          disabled={loading}
        />
        <button
          type="button"
          class="input-bar-send"
          onclick={handleSend}
          disabled={loading || !text.trim()}
          aria-label="发送"
        >
          <span aria-hidden="true">→</span>
        </button>
      </div>
    {:else}
      <!-- 自由心声模式：多行 + 高级控件 -->
      <div class="input-bar-freetext-wrap">
        <textarea
          class="input-bar-textarea"
          bind:value={text}
          onkeydown={handleKeydown}
          placeholder="你此刻想做些什么？……（Enter 发送，Shift+Enter 换行，Esc 收起）"
          rows="2"
          maxlength="200"
          disabled={loading}
        ></textarea>
        <div class="input-bar-freetext-actions">
          <span class="input-bar-counter">{text.length} / 200</span>
          <button
            type="button"
            class="input-bar-collapse"
            onclick={() => { freetextMode = false; text = ''; }}
            disabled={loading}
          >收起</button>
          <button
            type="button"
            class="input-bar-send input-bar-send-lg"
            onclick={handleSend}
            disabled={loading || !text.trim()}
          >说出</button>
        </div>
      </div>
    {/if}
  </div>

  <!-- 脑海中的声音（横向胶囊） -->
  <div class="voices-strip" class:voices-strip-disabled={loading}>
    <div class="voices-strip-label">
      <span class="voices-strip-icon" aria-hidden="true">💭</span>
      <span class="voices-strip-text">脑海中的声音</span>
      {#if voices.length > 0}
        <span class="voices-strip-count">{voices.length}</span>
      {/if}
      <!-- 🆕 v2.3: 换一批声音按钮（让玩家明确感知"声音会变"） -->
      {#if sessionId}
        <button
          type="button"
          class="voices-strip-refresh"
          class:voices-strip-refresh-busy={refreshing}
          onclick={handleRefresh}
          disabled={refreshing || loading}
          title="让 DM 重新想一组选项（基于当前局势）"
          aria-label="换一批声音"
        >
          <span class="voices-strip-refresh-icon" class:voices-strip-refresh-icon-spinning={refreshing} aria-hidden="true">↻</span>
        </button>
      {/if}
    </div>

    <div class="voices-strip-rail">
      {#if voices.length === 0}
        <div class="voices-strip-empty">
          <span>这一刻心思沉静——在输入框说出你想做的</span>
        </div>
      {:else}
        {#each voices as v (v.voice_id)}
          <VoicePill
            voice={v}
            hoveredId={hoveredId}
            loading={loading}
            onselect={onselect}
            onhover={(id) => (hoveredId = id)}
          />
        {/each}
      {/if}
    </div>
  </div>
</section>

<style>
  .action-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3) var(--space-3);
    background: var(--color-paper);
    border-top: 1px solid var(--color-ink-faint);
    flex: 0 0 auto;
  }

  /* ============================================
   * 输入条（豆包风格：胶囊 + 圆角 + 内嵌按钮）
   * ============================================ */
  .input-bar {
    width: 100%;
  }

  .input-bar-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: 24px;
    padding: 4px 4px 4px var(--space-3);
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .input-bar-row:focus-within {
    border-color: var(--color-bronze);
    background: var(--color-paper);
    box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.08);
  }

  .input-bar-freetext-btn {
    flex: 0 0 auto;
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    border-radius: 50%;
    color: var(--color-ink-light);
    font-size: var(--text-md);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .input-bar-freetext-btn:hover:not(:disabled) {
    background: rgba(165, 40, 40, 0.1);
    color: var(--color-cinnabar);
  }

  .input-bar-field {
    flex: 1 1 auto;
    min-width: 0;
    background: transparent;
    border: none;
    outline: none;
    font-family: var(--font-body);
    font-size: var(--text-md);
    color: var(--color-ink);
    padding: var(--space-2) 0;
  }

  .input-bar-field::placeholder {
    color: var(--color-ink-faint);
  }

  .input-bar-send {
    flex: 0 0 auto;
    width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--color-bronze);
    border: none;
    border-radius: 50%;
    color: var(--color-paper);
    font-size: var(--text-lg);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .input-bar-send:hover:not(:disabled) {
    background: var(--color-bronze-dark);
    transform: scale(1.05);
  }

  .input-bar-send:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .input-bar-send-lg {
    width: auto;
    height: auto;
    padding: var(--space-1) var(--space-4);
    border-radius: var(--radius-sm);
    font-family: var(--font-display);
    font-size: var(--text-sm);
  }

  /* 自由心声展开 */
  .input-bar-freetext-wrap {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-cinnabar);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
  }

  .input-bar-textarea {
    width: 100%;
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    padding: var(--space-2);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    line-height: var(--leading-normal);
    color: var(--color-ink);
    resize: vertical;
    min-height: 48px;
    max-height: 120px;
  }

  .input-bar-textarea:focus {
    outline: none;
    border-color: var(--color-cinnabar);
  }

  .input-bar-freetext-actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .input-bar-counter {
    flex: 1 1 auto;
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    font-family: var(--font-numeric);
  }

  .input-bar-collapse {
    padding: 4px var(--space-3);
    background: transparent;
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    color: var(--color-ink-light);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    cursor: pointer;
  }

  .input-bar-collapse:hover:not(:disabled) {
    background: var(--color-paper);
  }

  /* ============================================
   * 脑海中的声音（横向胶囊条）
   * ============================================ */
  .voices-strip {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .voices-strip-label {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    font-family: var(--font-display);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    background: rgba(184, 134, 11, 0.08);
    border-radius: var(--radius-sm);
    white-space: nowrap;
  }

  .voices-strip-icon {
    font-size: var(--text-sm);
  }

  .voices-strip-count {
    font-family: var(--font-numeric);
    font-size: 10px;
    background: var(--color-bronze);
    color: var(--color-paper);
    padding: 0 4px;
    border-radius: 8px;
  }

  /* 🆕 v2.3 换一批声音按钮 */
  .voices-strip-refresh {
    flex: 0 0 auto;
    width: 22px;
    height: 22px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid var(--color-ink-faint);
    border-radius: 50%;
    color: var(--color-ink-light);
    font-size: 13px;
    line-height: 1;
    cursor: pointer;
    margin-left: 4px;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .voices-strip-refresh:hover:not(:disabled) {
    background: var(--color-bronze);
    border-color: var(--color-bronze-dark);
    color: var(--color-paper);
    transform: rotate(45deg);
  }

  .voices-strip-refresh:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .voices-strip-refresh-busy {
    background: var(--color-bronze-light);
  }

  .voices-strip-refresh-icon {
    display: inline-block;
  }

  .voices-strip-refresh-icon-spinning {
    animation: refresh-spin 0.8s linear infinite;
  }

  @keyframes refresh-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .voices-strip-rail {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    gap: var(--space-2);
    overflow-x: auto;
    overflow-y: visible;  /* 允许 popover 溢出 */
    padding: 2px 0 4px;
    scrollbar-width: thin;
    scrollbar-color: var(--color-bronze) transparent;
  }

  .voices-strip-rail::-webkit-scrollbar {
    height: 4px;
  }
  .voices-strip-rail::-webkit-scrollbar-thumb {
    background: var(--color-bronze);
    border-radius: 2px;
  }
  .voices-strip-rail::-webkit-scrollbar-track {
    background: transparent;
  }

  .voices-strip-disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  .voices-strip-empty {
    flex: 1 1 auto;
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    font-style: italic;
    text-align: center;
  }

  /* 🆕 v2.10.8: 删除重复 voice-pill 样式（移到 VoicePill.svelte 后这里变死代码）
     - 之前 ActionPanel 和 VoicePill 都定义了同一套 .voice-pill-* 类
     - 实际渲染的是子组件 VoicePill.svelte（Svelte 5 自动 scope 类名）
     - 这里保留的是死代码，且和子组件定义冲突，导致 mobile 上 popover 样式不对
     - 删掉 120 行，统一由 VoicePill.svelte 负责 */

  /* ============================================================
   * 🆕 v2.10.8 移动端适配
   * - 输入框字号 ≥ 16px（防 iOS 自动放大）
   * - 发送按钮 ≥ 44×44（iOS HIG 最小可点击区域）
   * - 自由心声按钮同步放大
   * - 脑海声音条横向滚动更顺滑
   * ============================================================ */
  @media (max-width: 767px) {
    .action-panel {
      padding: var(--space-2);
    }

    /* 输入条：字号 16px（防 iOS 放大），按钮区域更大 */
    .input-bar-row {
      padding: 2px 2px 2px var(--space-2);
      gap: var(--space-1);
    }
    .input-bar-field {
      font-size: 16px;          /* iOS Safari 自动放大的阈值 */
      padding: var(--space-2) 0;
    }
    .input-bar-freetext-btn {
      width: 40px;
      height: 40px;
    }
    .input-bar-send {
      width: 44px;
      height: 44px;              /* iOS HIG 最小可点击区域 */
    }

    /* 自由心声模式：底部加 safe area 适配 */
    .input-bar-freetext-wrap {
      padding-bottom: calc(var(--space-2) + env(safe-area-inset-bottom, 0px));
    }
    .input-bar-textarea {
      font-size: 16px;           /* 防 iOS 放大 */
    }

    /* 脑海声音：横向滚动条更顺滑 */
    .voices-strip {
      flex-wrap: wrap;
      gap: var(--space-1);
    }
    .voices-strip-label {
      font-size: var(--text-2xs, 11px);
    }
    .voices-strip-rail {
      flex: 1 1 100%;
      order: 2;
      gap: var(--space-1);
      -webkit-overflow-scrolling: touch;
      overscroll-behavior-x: contain;
    }
  }

  /* 极窄屏（≤360）输入条更紧凑 */
  @media (max-width: 360px) {
    .input-bar-freetext-btn {
      width: 36px;
      height: 36px;
    }
    .input-bar-send {
      width: 40px;
      height: 40px;
    }
  }
</style>
