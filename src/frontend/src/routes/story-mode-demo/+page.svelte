<script lang="ts">
  /**
   * 🆕 v2.10.20 — 故事模式 Demo 页 (升级版)
   *
   * 支持:
   * - 章节切换 (ch1 家贫 / ch2 织染)
   * - 章节信息显示 (节点数/选项数/结局数/随机事件数)
   * - 跨章回响显示 (🆕 第一章回响)
   * - LLM 降级提示
   * - 多结局解锁提示
   *
   * 完全不依赖 LLM 的剧本体验。
   * 玩《第一章：家贫》(22 节点 55 选项 5 结局) + 《第二章：织染》(33 节点 90 选项 7 结局)
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
    scripted_chapter_id?: number;
    chapter_complete?: boolean;
    effects_applied?: Record<string, any>;
    flag_added?: string[];
    cash?: number;
    debt?: number;
    rice?: number;
    looms?: number;
    city?: string;
    scripted_flags?: string[];
    scripted_visits?: string[];
    scripted_chapter_complete?: boolean;
    llm_calls?: number;
    error?: string;
  }

  // 章节元信息
  const CHAPTERS = [
    {
      id: 1,
      title: '家贫',
      subtitle: '万历十五年三月 · 盛泽镇',
      desc: '父亲病重、债台初筑、织工小子在江南的春日抉择。',
      nodes: 22,
      options: 55,
      endings: 5,
      encounters: 3,
      estimatedMinutes: 10,
      theme: '抉择 / 求生',
    },
    {
      id: 2,
      title: '织染',
      subtitle: '万历十五年六月至九月 · 盛泽镇 / 苏州府',
      desc: '苏州订单 · 家庭考验 · 织机扩张 · 染色危机 · 父亲秘密。',
      nodes: 33,
      options: 90,
      endings: 7,
      encounters: 5,
      estimatedMinutes: 15,
      theme: '抉择 / 兴衰 / 家庭',
    },
    {
      id: 3,
      title: '丝绢案',
      subtitle: '万历十五年九月至次年二月 · 盛泽镇 / 苏州府 / 织造衙门',
      desc: '织造太监采办 · 税关压迫 · 父亲冤案 · 抗税起义。',
      nodes: 22,
      options: 54,
      endings: 7,
      encounters: 6,
      estimatedMinutes: 15,
      theme: '抉择 / 政治 / 复仇 / 生死',
    },
  ];

  let selectedChapter = $state(1);
  let sessionId = $state('');
  let narrative = $state('');
  let voiceOptions: VoiceOption[] = $state([]);
  let effectsApplied: Record<string, any> = $state({});
  let flagAdded: string[] = $state([]);
  let scriptedFlags: string[] = $state([]);
  let chapterComplete = $state(false);
  let currentChapter = $state(1);
  let nodeId = $state('');
  let llmCalls = $state(0);
  let totalSteps = $state(0);
  let error = $state('');
  let loading = $state(false);
  let isStarted = $state(false);

  // 章节进度统计
  let visitedNodes = $state<string[]>([]);
  let chapterVisits = $state<Record<number, string[]>>({});

  let currentChapterInfo = $derived(
    CHAPTERS.find(c => c.id === selectedChapter) || CHAPTERS[0]
  );

  async function startChapter() {
    error = '';
    loading = true;
    totalSteps = 0;
    scriptedFlags = [];
    visitedNodes = [];

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

      // 2. 启动故事模式 (指定章节)
      const res = await fetch('/api/scripted/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          chapter_id: selectedChapter,
        }),
      });
      const data: ScriptedResponse = await res.json();
      if (data.error) {
        error = data.error;
      } else {
        narrative = data.narrative;
        voiceOptions = data.voice_options;
        currentChapter = data.scripted_chapter_id || selectedChapter;
        nodeId = data.scripted_node_id || '';
        llmCalls = data.llm_calls || 0;
        isStarted = true;
        visitedNodes = [data.scripted_node_id || ''].filter(Boolean);
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
        currentChapter = data.scripted_chapter_id || currentChapter;
        chapterComplete = data.chapter_complete || false;
        llmCalls = data.llm_calls || 0;
        totalSteps += 1;
        if (data.scripted_node_id) {
          nodeId = data.scripted_node_id;
          visitedNodes = [...visitedNodes, data.scripted_node_id];
        }
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

  function switchChapter(chapterId: number) {
    selectedChapter = chapterId;
    isStarted = false;
    narrative = '';
    voiceOptions = [];
    error = '';
    chapterComplete = false;
  }

  function getChapterEndings(chapterId: number): string[] {
    if (chapterId === 1) {
      return ['resolution', 'resolution_prosperous', 'resolution_bankrupt', 'resolution_outcast', 'resolution_father_dead'];
    } else if (chapterId === 2) {
      return ['ch2_resolution_prosperous', 'ch2_resolution_normal', 'ch2_resolution_loss',
              'ch2_resolution_outcast', 'ch2_resolution_widow', 'ch2_resolution_father_dead', 'ch2_resolution_fire'];
    } else {
      return ['ch3_resolution_vindicator', 'ch3_resolution_resistance_leader', 'ch3_resolution_survivor',
              'ch3_resolution_rich_traitor', 'ch3_resolution_fugitive', 'ch3_resolution_dead', 'ch3_resolution_loss'];
    }
  }
</script>

<svelte:head>
  <title>故事模式 · 历史注脚</title>
</svelte:head>

<main class="story-mode-demo">
  <header class="demo-header">
    <h1>🎭 故事模式</h1>
    <p class="subtitle"><strong>零 LLM</strong> · D&amp;D 风格 · 完整多章剧本</p>

    <nav class="chapter-tabs">
      {#each CHAPTERS as ch}
        <button
          class="chapter-tab"
          class:active={selectedChapter === ch.id}
          onclick={() => switchChapter(ch.id)}
          disabled={isStarted && currentChapter !== ch.id}
        >
          <span class="tab-num">第{ch.id}章</span>
          <span class="tab-title">{ch.title}</span>
          <span class="tab-meta">{ch.nodes}节点 · {ch.endings}结局</span>
        </button>
      {/each}
    </nav>

    <div class="chapter-info">
      <div class="info-row">
        <span>📖 章节</span>
        <strong>第{currentChapterInfo.id}章 · {currentChapterInfo.title}</strong>
      </div>
      <div class="info-row">
        <span>📍 时间</span>
        <strong>{currentChapterInfo.subtitle}</strong>
      </div>
      <div class="info-row stats">
        <span class="stat"><strong>{currentChapterInfo.nodes}</strong> 节点</span>
        <span class="stat"><strong>{currentChapterInfo.options}</strong> 选项</span>
        <span class="stat"><strong>{currentChapterInfo.endings}</strong> 结局</span>
        <span class="stat"><strong>{currentChapterInfo.encounters}</strong> 随机事件</span>
        <span class="stat"><strong>~{currentChapterInfo.estimatedMinutes}</strong> 分钟</span>
      </div>
      <div class="info-row theme">
        <span>🎭 主题: {currentChapterInfo.theme}</span>
      </div>
      <p class="chapter-desc">{currentChapterInfo.desc}</p>
    </div>

    {#if isStarted}
      <div class="state-bar">
        <span class="state-tag">节点: <code>{nodeId || '(未开始)'}</code></span>
        <span class="state-tag">步数: <strong>{totalSteps}</strong></span>
        <span class="state-tag">flags: <strong>{scriptedFlags.length}</strong></span>
        <span class="state-tag llm-badge">🤖 LLM: <strong>{llmCalls}</strong></span>
      </div>
    {/if}
  </header>

  {#if !isStarted}
    <section class="start-section">
      <h2>{currentChapterInfo.title}</h2>
      <p class="narrative">{currentChapterInfo.desc}</p>
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
            <span class="flag-chip new">{f}</span>
          {/each}
        </div>
      {/if}

      {#if scriptedFlags && scriptedFlags.length > 0}
        <div class="flags-section">
          <strong>已解锁 flag ({scriptedFlags.length})：</strong>
          {#each scriptedFlags as f}
            <span class="flag-chip active">{f}</span>
          {/each}
        </div>
      {/if}

      {#if visitedNodes.length > 1}
        <details class="path-trace">
          <summary>📍 已访问节点 ({visitedNodes.length})</summary>
          <ol>
            {#each visitedNodes as n, i}
              <li><code>{n}</code></li>
            {/each}
          </ol>
        </details>
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
        <h3>✅ 第{currentChapter}章完成！</h3>
        <div class="complete-stats">
          <span>总步数: <strong>{totalSteps}</strong></span>
          <span>LLM 调用: <strong>{llmCalls}</strong></span>
          <span>解锁 flags: <strong>{scriptedFlags.length}</strong></span>
        </div>
        <div class="complete-actions">
          {#if currentChapter < 2}
            <button onclick={() => switchChapter(2)}>▶ 进入第二章</button>
          {/if}
          <button onclick={() => { switchChapter(currentChapter); }}>↺ 重玩第{currentChapter}章</button>
        </div>
        <p class="complete-hint">本章节共 {currentChapterInfo.endings} 个结局，已解锁 1 个。</p>
      </section>
    {/if}

    {#if error}
      <p class="error">⚠ {error}</p>
    {/if}
  {/if}

  <footer class="demo-footer">
    <details>
      <summary>📚 设计说明 (v2.10.20)</summary>
      <ul>
        <li><strong>零 LLM</strong>: 完全剧本化，无外部依赖</li>
        <li><strong>D&amp;D 风格</strong>: flag 组合 + 触发条件 + d20 检定</li>
        <li><strong>有限选项</strong>: 每节点 3-5 个 voice_options</li>
        <li><strong>inner_voice</strong>: DM 内心独白</li>
        <li><strong>跨章回响</strong>: 第一章 flag 动态影响第二章 narrative</li>
        <li><strong>多章累计</strong>: 2 章合计 55 节点 145 选项 12 结局</li>
        <li><strong>历史依据</strong>: 《吴江县志》《万历邸钞》《金瓶梅》</li>
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
    margin: 4px 0 16px;
    color: #5a4a36;
    font-size: 14px;
  }

  .chapter-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .chapter-tab {
    flex: 1;
    min-width: 140px;
    padding: 10px 14px;
    background: #d4b896;
    border: 2px solid transparent;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s;
    color: #1a1612;
    text-align: left;
    font-family: inherit;
  }

  .chapter-tab:hover:not(:disabled) {
    background: #c8a978;
  }

  .chapter-tab.active {
    background: #c44536;
    color: #fff8e1;
    border-color: #8b1a1a;
  }

  .chapter-tab:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .tab-num {
    display: block;
    font-size: 11px;
    opacity: 0.8;
    margin-bottom: 2px;
  }

  .tab-title {
    display: block;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .tab-meta {
    display: block;
    font-size: 11px;
    opacity: 0.85;
  }

  .chapter-info {
    background: #f5e6c8;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 12px;
  }

  .info-row {
    display: flex;
    gap: 12px;
    align-items: baseline;
    font-size: 13px;
    padding: 3px 0;
  }

  .info-row.stats {
    gap: 16px;
    flex-wrap: wrap;
    padding-top: 6px;
    border-top: 1px dashed #5a4a36;
    margin-top: 4px;
  }

  .stat {
    background: #5a4a36;
    color: #fff8e1;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
  }

  .stat strong {
    color: #f5d290;
    margin-right: 4px;
  }

  .info-row.theme {
    font-style: italic;
    color: #5a4a36;
  }

  .chapter-desc {
    margin: 8px 0 0;
    font-size: 12px;
    color: #5a4a36;
    font-style: italic;
  }

  .state-bar {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 12px;
    color: #5a4a36;
    margin-top: 8px;
  }

  .state-tag {
    background: #d4b896;
    padding: 3px 10px;
    border-radius: 4px;
  }

  .llm-badge {
    background: #c44536;
    color: #fff8e1;
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

  .flag-chip.new {
    background: #c47c36;
    animation: pulse 1s ease-in-out;
  }

  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
  }

  .path-trace {
    margin-top: 16px;
    padding: 8px 12px;
    background: #f5e6c8;
    border-radius: 4px;
    font-size: 12px;
  }

  .path-trace ol {
    margin: 8px 0 0;
    padding-left: 24px;
  }

  .path-trace code {
    background: #d4b896;
    padding: 1px 6px;
    border-radius: 2px;
    font-size: 11px;
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
    color: #1a1612;
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
    color: #1a1612;
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

  .complete-stats {
    display: flex;
    gap: 16px;
    justify-content: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .complete-stats span {
    background: #f5e6c8;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 13px;
  }

  .complete-actions {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .complete-hint {
    text-align: center;
    color: #5a4a36;
    font-size: 13px;
    margin: 8px 0 0;
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

  details ul {
    padding-left: 20px;
    line-height: 1.8;
  }
</style>