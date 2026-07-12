<script lang="ts">
  /**
   * 游戏页 - 完整集成
   *
   * 🆕 v1.7.30 联调：
   * - 优先从 URL ?session=xxx 拿 session_id
   * - fallback 到 localStorage 'hfe_session_id'
   * - 调 /api/state 拿真实 game state
   * - debug 模式：?demo=1 仍可用 mock（QA 截图用）
   */
  import { game, gameActions, isLoading } from '$lib/stores';
  import { GameView, GameHeader } from '$lib/components/game';
  // 🆕 v2.10.1 W73: 恢复静态 import（W66 dynamic import 导致 modal 不可用）
  import {
    CharacterWikiModal,
    RecapModal,
    GlossaryModal,
    FeedbackModal,
    SettingsModal,
  } from '$lib/components/modals';
  import { getSessionId } from '$lib/api/start';
  import { getState } from '$lib/api/state';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { Spinner, toast } from '$lib/components/design-system';

  // Mock 数据（仅 demo=1 QA 截图用）
  const MOCK_GAME = {
    session_id: 'demo-1',
    account_username: 'demo',
    character: { name: '沈织户', age: 30, occupation: '织工', hometown: '盛泽镇' },
    family: [
      { relation: '妻', name: '张氏', age: 27, status: '在世' },
      { relation: '母', name: '沈王氏', age: 58, status: '在世' },
      { relation: '子', name: '大毛', age: 7, status: '在世' }
    ],
    skills: [
      { name: '挽丝', level: 3 },
      { name: '织绸', level: 2 }
    ],
    city: '盛泽镇',
    year_current: 1587,
    year_max: 1601,
    round_current: 1,
    cash: 1.20,
    rice: 0,
    looms: 1,
    debt: 3.60,
    monthly_burn: 0.42,
    reputation: 5,
    identity: 'weaving_male' as const,
    gender: 'male' as const,
    era_id: 'wanli1587',
    timeline: [
      { year: 1587, event: '你出生', highlight: false },
      { year: 1588, event: '入行学徒', highlight: false },
      { year: 1596, event: '矿税监设立', highlight: false },
      { year: 1601, event: '葛贤抗税', highlight: true }
    ],
    sidebar: {
      active_tasks: [
        { title: '送牙行束脩（约 1.2 两）', urgency: 'high' as const },
        { title: '购置干青桑叶', urgency: 'medium' as const }
      ],
      upcoming_deadlines: [
        { name: '赵牙人束脩', days_estimate: 10, amount: '1.20 两' }
      ],
      financial_status: { cash: 1.20, rice: 0, debt: 3.60, monthly_burn: 0.42 }
    },
    narrative: {
      round: 1,
      content: `欢迎来到【万历十五年】。你是 沈青山 — 苏州府吴江县盛泽镇东栅巷。家庭：妻张氏 27岁，操持灶房与机后的事；子大毛 7岁尚未开蒙、二丫头 4岁常跟在张氏脚边；母沈王氏 58岁半瘫在床，住在后屋。

【来历】沈家原在吴江县城外，祖上以耕读传家。祖父辈在镇上开过一间小当铺，后被倭寇烧毁，家道中落。父亲沈青山自幼随邻人学织，到你这辈已是第三代织工。

【开局处境】万历十五年十月廿三。手里现银只有四钱三分，欠牙行束脩一两二钱。米缸见底，老娘的药快没了。

十月的夜来得早。沈青山从织机前站起身的时候，膝盖咯吧一响，腰像是被人拿绳子勒过一道。张氏在后屋哄二丫头睡着了，灶房里还有一点药味没散——是给老娘熬的最后一副。`,
      type: 'opening' as const,
      created_at: '2026-07-08'
    },
    narrative_history: [],
    last_voice_options: [
      { voice_id: 'v1', voice_name: '先看看家里情况', intent_text: '我先扫一眼家里有什么，银钱还剩多少，灶房是什么光景' },
      { voice_id: 'v2', voice_name: '出门找活路', intent_text: '我去牙行问最近有没有活计可接' },
      { voice_id: 'v3', voice_name: '先顾眼前', intent_text: '我想想今天的米缸还够不够，今天必须先吃饱' },
      { voice_id: 'free', voice_name: '✍️ 自由输入', intent_text: '都不对？自己描述要做什么', is_freetext: true }
    ]
  };

  // 5 个弹层开关
  let wikiOpen = $state(false);
  let recapOpen = $state(false);
  let glossaryOpen = $state(false);
  let feedbackOpen = $state(false);
  let settingsOpen = $state(false);
  let loading = $state(false);
  let loadError = $state<string | null>(null);

  onMount(async () => {
    // 调试模式：mock data
    if ($page.url.searchParams.get('demo') === '1') {
      gameActions.set(MOCK_GAME as any);
      return;
    }

    // 1. 拿 session_id（URL 优先 > localStorage）
    const sessionId =
      $page.url.searchParams.get('session') ??
      getSessionId();

    if (!sessionId) {
      toast.warning('没有 session_id，请先创建角色');
      goto('/');
      return;
    }

    // 2. 调 /api/state 拿真实 state
    loading = true;
    try {
      const state = await getState(sessionId);
      gameActions.set(state as any);
    } catch (e) {
      const err = e as Error;
      loadError = err.message ?? '加载失败';
      toast.error(`加载游戏失败：${loadError}`);
      // session 失效 → 回首页
      setTimeout(() => goto('/'), 1500);
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>游戏中 · 历史注脚</title>
</svelte:head>

{#if loading}
  <div class="game-loading">
    <Spinner mode="brush" size={48} />
    <p>正在进入万历十五年...</p>
  </div>
{:else if $game}
  <div class="game-page">
    <GameHeader
      game={$game}
      onwiki={() => wikiOpen = true}
      onrecap={() => recapOpen = true}
      onglossary={() => glossaryOpen = true}
      onfeedback={() => feedbackOpen = true}
      onsettings={() => settingsOpen = true}
    />
    <div class="game-page-body">
      <GameView />
    </div>
  </div>

  <!-- 🆕 v2.10.1 fix: 用 onclose 替代 bind:open (svelte-check 报 non-bindable) -->
  <CharacterWikiModal open={wikiOpen} onclose={() => wikiOpen = false} />
  <RecapModal open={recapOpen} onclose={() => recapOpen = false} />
  <GlossaryModal open={glossaryOpen} onclose={() => glossaryOpen = false} />
  <FeedbackModal open={feedbackOpen} onclose={() => feedbackOpen = false} />
  <SettingsModal open={settingsOpen} onclose={() => settingsOpen = false} />
{:else if loadError}
  <div class="game-error">
    <p>⚠ {loadError}</p>
    <p>正在跳回首页...</p>
  </div>
{:else}
  <div class="game-loading">
    <p>加载中…</p>
  </div>
{/if}

<style>
  .game-page {
    display: flex;
    flex-direction: column;
    height: 100dvh;     /* 🆕 v2.2: dvh 解决移动浏览器地址栏 */
    min-height: 100vh;
  }

  .game-page-body {
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
  }

  .game-loading,
  .game-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-ink-light);
    gap: var(--space-3);
  }
  .game-error p {
    color: var(--color-cinnabar);
  }
</style>
