<script lang="ts">
  /**
   * 🆕 v2.10.16 Phase 10 — 故事模式 Demo 页
   *
   * 完全不依赖 LLM 的剧本体验。
   * 玩《第一章：家贫》 — 4 节点 + 20 选项
   *
   * 演示 D&D 风格的:
   * - 有限选项 (3-5 个 voice_options)
   * - flag 组合 (met_zhang, has_debt)
   * - effects (cash/debt/rice/looms/city)
   * - inner_voice DM 内心独白
   * - 节点跳转 (intro_1 → intro_2_* → climax_* → resolution)
   */

  import { onMount } from 'svelte';

  interface VoiceOption {
    voice_id: string;
    voice_name: string;
    description: string;
    inner_voice?: string;
  }

  interface ScriptedResponse {
    narrative: string;
    voice_options: VoiceOption[];
    scripted_node_id?: string;
    chapter_complete?: boolean;
    effects_applied?: Record<string, any>;
    flag_added?: string[];
    cash?: number;
    debt?: number;
    rice?: number;
    looms?: number;
    city?: string;
    scripted_flags?: string[];
    llm_calls?: number;
    error?: string;
  }

  let sessionId = $state('');
  let narrative = $state('');
  let voiceOptions: VoiceOption[] = $state([]);
  let effectsApplied: Record<string, any> = $state({});
  let flagAdded: string[] = $state([]);
  let scriptedFlags: string[] = $state([]);
  let chapterComplete = $state(false);
  let nodeId = $state('');
  let llmCalls = $state(0);
  let totalSteps = $state(0);
  let error = $state('');
  let loading = $state(false);
  let isStarted = $state(false);

  async function startChapter() {
    error = '';
    loading = true;
    totalSteps = 0;
    scriptedFlags = [];

    try {
      // 1. 创建 session
      const startRes = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: `story_${Date.now()}`,
          era_id: 'wanli1587',
        }),
      });
      const startData = await startRes.json();
      sessionId = startData.session_id;

      // 2. 启动故事模式
      const res = await fetch('/api/scripted/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, chapter_id: 1 }),
      });
      const data: ScriptedResponse = await res.json();
      if (data.error) {
        error = data.error;
      } else {
        narrative = data.narrative;
        voiceOptions = data.voice_options;
        nodeId = data.scripted_node_id || '';
        llmCalls = data.llm_calls || 0;
        isStarted = true;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  async function choose(voiceId: string) {
    error = '';
    loading = true;

    try {
      const res = await fetch('/api/scripted/input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input: voiceId }),
      });
      const data: ScriptedResponse = await res.json();
      if (data.error) {
        error = data.error;
      } else {
        narrative = data.narrative;
        voiceOptions = data.voice_options;
        effectsApplied = data.effects_applied || {};
        flagAdded = data.flag_added || [];
        scriptedFlags = data.scripted_flags || [];
        nodeId = data.scripted_node_id || '';
        chapterComplete = data.chapter_complete || false;
        llmCalls = data.llm_calls || 0;
        totalSteps += 1;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  function formatEffect(k: string, v: any): string {
    if (k.endsWith('_delta')) {
      const sign = (v as number) >= 0 ? '+' : '';
      return `${k.replace('_delta', '')} ${sign}${v}`;
    }
    if (k === 'city_move') return `城 → ${v}`;
    if (k === 'flag_set') return `+flag`;
    return `${k}=${v}`;
  }
</script>

<svelte:head>
  <title>故事模式 · 历史注脚</title>
</svelte:head>

<main class="story-mode-demo">
  <header class="demo-header">
    <h1>🎭 故事模式 · 第一章</h1>
    <p class="subtitle">万历十五年三月 · 盛泽镇 · <strong>0 LLM 调用</strong></p>
    <div class="meta-bar">
      <span>节点: <code>{nodeId || '(未开始)'}</code></span>
      <span>步数: <strong>{totalSteps}</strong></span>
      <span class="llm-badge">🤖 LLM: <strong>{llmCalls}</strong></span>
    </div>
  </header>

  {#if !isStarted}
    <section class="start-section">
      <h2>第一章：家贫</h2>
      <p>父亲病重、债台初筑、织工小子在江南的春日抉择。</p>
      <button onclick={startChapter} disabled={loading}>
        {loading ? '加载中…' : '▶ 开始游戏'}
      </button>
      {#if error}
        <p class="error">⚠ {error}</p>
      {/if}
    </section>
  {:else}
    <section class="narrative-section">
      <pre class="narrative">{narrative}</pre>

      {#if effectsApplied && Object.keys(effectsApplied).length > 0}
        <div class="effects-bar">
          <strong>效果：</strong>
          {#each Object.entries(effectsApplied) as [k, v]}
            <span class="effect-chip">{formatEffect(k, v)}</span>
          {/each}
        </div>
      {/if}

      {#if flagAdded && flagAdded.length > 0}
        <div class="effects-bar">
          <strong>+Flag：</strong>
          {#each flagAdded as f}
            <span class="flag-chip">{f}</span>
          {/each}
        </div>
      {/if}

      {#if scriptedFlags && scriptedFlags.length > 0}
        <div class="flags-section">
          <strong>已解锁 flag：</strong>
          {#each scriptedFlags as f}
            <span class="flag-chip active">{f}</span>
          {/each}
        </div>
      {/if}
    </section>

    {#if !chapterComplete}
      <section class="choices-section">
        <h3>你会怎么选？</h3>
        <div class="choices-grid">
          {#each voiceOptions as opt (opt.voice_id)}
            <button
              class="choice-btn"
              onclick={() => choose(opt.voice_id)}
              disabled={loading}
            >
              <div class="choice-name">{opt.voice_name}</div>
              {#if opt.description}
                <div class="choice-desc">{opt.description}</div>
              {/if}
              {#if opt.inner_voice}
                <div class="choice-inner">💭 {opt.inner_voice}</div>
              {/if}
            </button>
          {/each}
        </div>
      </section>
    {:else}
      <section class="complete-section">
        <h3>✅ 第一章完成！</h3>
        <p>总步数: {totalSteps} | LLM 调用: {llmCalls} | Flags: {scriptedFlags.length}</p>
        <button onclick={startChapter}>↺ 重玩</button>
      </section>
    {/if}

    {#if error}
      <p class="error">⚠ {error}</p>
    {/if}
  {/if}

  <footer class="demo-footer">
    <details>
      <summary>📚 设计说明</summary>
      <ul>
        <li><strong>零 LLM</strong>: 完全剧本化，零依赖</li>
        <li><strong>D&D 风格</strong>: flag 组合 + 触发条件 + effects</li>
        <li><strong>有限选项</strong>: 每节点 3-5 个 voice_options</li>
        <li><strong>inner_voice</strong>: 玩家会看到的 DM 内心独白</li>
        <li><strong>10 节点</strong>: intro_1 + 4 escalation + 3 climax + resolution</li>
        <li><strong>历史依据</strong>: 参考《吴江县志》《万历邸钞》</li>
      </ul>
    </details>
  </footer>
</main>

<style>
  .story-mode-demo {
    max-width: 920px;
    margin: 0 auto;
    padding: 32px;
    font-family: 'STKaiti', 'KaiTi', serif;
    background: #e8d8b0;
    color: #1a1612;
    min-height: 100vh;
  }

  .demo-header {
    border-bottom: 2px solid #5a4a36;
    padding-bottom: 16px;
    margin-bottom: 24px;
  }

  .demo-header h1 {
    margin: 0;
    font-size: 28px;
    letter-spacing: 4px;
  }

  .subtitle {
    margin: 4px 0 12px;
    color: #5a4a36;
    font-size: 14px;
  }

  .meta-bar {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 12px;
    color: #5a4a36;
  }

  .llm-badge {
    background: #c44536;
    color: #fff8e1;
    padding: 2px 8px;
    border-radius: 4px;
  }

  .start-section,
  .narrative-section,
  .choices-section,
  .complete-section {
    margin-bottom: 32px;
    padding: 24px;
    background: #fff8e1;
    border: 1px solid #5a4a36;
    border-radius: 4px;
  }

  .narrative {
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 16px;
    line-height: 1.8;
    white-space: pre-wrap;
    margin: 0;
    color: #1a1612;
  }

  .effects-bar,
  .flags-section {
    margin-top: 12px;
    font-size: 13px;
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .effect-chip {
    background: #d4a373;
    color: #1a1612;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: 600;
  }

  .flag-chip {
    background: #2c5e6f;
    color: #fff8e1;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
  }

  .flag-chip.active {
    background: #c44536;
  }

  .choices-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 16px;
  }

  .choice-btn {
    background: #fff8e1;
    border: 2px solid #5a4a36;
    border-radius: 4px;
    padding: 16px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    transition: all 0.15s;
  }

  .choice-btn:hover:not(:disabled) {
    background: #f5d290;
    border-color: #c44536;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(196, 69, 54, 0.2);
  }

  .choice-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .choice-name {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .choice-desc {
    font-size: 14px;
    color: #5a4a36;
    margin-bottom: 4px;
  }

  .choice-inner {
    font-size: 12px;
    color: #8b1a1a;
    font-style: italic;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px dashed #5a4a36;
  }

  button {
    background: #c44536;
    color: #fff8e1;
    border: none;
    padding: 12px 32px;
    font-size: 16px;
    font-family: inherit;
    font-weight: 600;
    cursor: pointer;
    border-radius: 4px;
    transition: background 0.15s;
  }

  button:hover:not(:disabled) {
    background: #8b1a1a;
  }

  button:disabled {
    background: #5a4a36;
    cursor: not-allowed;
  }

  .error {
    color: #c44536;
    background: #fff8e1;
    padding: 12px;
    border-left: 3px solid #c44536;
    margin-top: 12px;
  }

  .complete-section {
    text-align: center;
  }

  .demo-footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px dashed #5a4a36;
    font-size: 13px;
  }

  details summary {
    cursor: pointer;
    color: #5a4a36;
  }
</style>