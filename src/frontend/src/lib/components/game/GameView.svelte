<script lang="ts">
  /**
   * GameView - 豆包式双栏布局（v2.2 重构）
   *
   * 布局（参考豆包 AI 对话）：
   *   ┌──────┬──────────────────────────────────────┐
   *   │ 档案 │  叙事区（可独立滚动）                │
   *   │ 任务 │   ...                                │
   *   │ 备忘 │                                      │
   *   │      ├──────────────────────────────────────┤
   *   │      │  💭 脑海中的声音（横向胶囊）          │
   *   │      ├──────────────────────────────────────┤
   *   │      │  [输入框........................][→]│  ← 输入条固定
   *   └──────┴──────────────────────────────────────┘
   *
   * 设计原则（v2.2）：
   *   - 左栏：CharCard + 任务/财务（始终可见，可独立滚动）
   *   - 右栏：叙事区 + ActionPanel（叙事可滚，ActionPanel 固定底部）
   *   - 移动端：左栏折叠为顶部抽屉
   *   - 横向胶囊：高度 ≤ 56px，支持横向滚动溢出
   */
  import { game, isLoading, gameActions } from '$lib/stores';
  import { submitInput } from '$lib/api/input';
  import { fateEmergencyCheck } from '$lib/api/fate';
  import { confirmCityChange, rejectCityChange } from '$lib/api/state';
  // 🆕 W77: 修正路径（modal 在 modals/ 子目录）
  import CityChangeModal from '../modals/CityChangeModal.svelte';
  import { Toast, toast } from '$lib/components/design-system';
  import CharCard from './CharCard.svelte';
  import SidebarPanel from './SidebarPanel.svelte';
  import NarrativeArea from './NarrativeArea.svelte';
  import ActionPanel from './ActionPanel.svelte';
  import LoadingOverlay from './LoadingOverlay.svelte';
  import EmergencyModal from './EmergencyModal.svelte';
  import ChapterProgressBar from './ChapterProgressBar.svelte';
  import ChapterHistoryDrawer from './ChapterHistoryDrawer.svelte';
  import ChapterIntro from './ChapterIntro.svelte';
  // 🆕 v2.9.x W50: admin 模式组件（?admin=true 时显示）
  import PlateMap from './PlateMap.svelte';
  import ChapterTimeline from './ChapterTimeline.svelte';
  import MetricsPanel from './MetricsPanel.svelte';
  import { isAdminMode } from './adminMode';
  import type { FateCard } from '$lib/api/types';

  // 🆕 v2.9.x W50: admin 模式开关（URL ?admin=true）
  const showAdminTools = isAdminMode();

  // 🆕 v2.10.1 W69: 章节开场遮罩
  // 后端 /api/state 返：round_number（总回合）+ recent_narratives[0].round (0=开场)
  // 检测策略：仅在 round_number === 1 时显示开场（之后不再显示）
  // 这样避免：每次新回合 round 变化再次触发开场
  let showChapterIntro = $state(true);
  let introShownKey = $state<string | null>(null);

  $effect(() => {
    if (!$game) return;
    const round = ($game as any).round_number ?? 0;
    const stateKey = `${$game.session_id}`;
    // 仅在 round_number === 1（即首次进入）显示开场
    // round > 1 表示之前已游玩过，不应再显示
    if (round === 1 && introShownKey !== stateKey) {
      showChapterIntro = true;
    } else {
      showChapterIntro = false;
    }
  });

  function handleStartChapter() {
    showChapterIntro = false;
    introShownKey = $game?.session_id ?? null;
  }

  // 🆕 v2.10.1 W77: 城市变更确认
  $effect(() => {
    if (!$game) return;
    const pending = ($game as any).pending_city_change;
    if (pending) {
      // 自动弹出确认（避免被遮罩）
    }
  });

  async function handleConfirmCity() {
    if (!$game) return;
    try {
      const updated = await confirmCityChange($game.session_id);
      gameActions.set(updated);
      toast.success('已到达新城市');
    } catch (e) {
      const err = e as Error;
      toast.error(err.message || '确认失败');
    }
  }

  async function handleRejectCity() {
    if (!$game) return;
    try {
      const updated = await rejectCityChange($game.session_id);
      gameActions.set(updated);
      toast.info('已留下，原地不动');
    } catch (e) {
      const err = e as Error;
      toast.error(err.message || '操作失败');
    }
  }

  async function handleSelectVoice(voice: { voice_id: string; voice_name: string; intent_text?: string }) {
    if (!$game || $isLoading) return;
    isLoading.set(true);
    try {
      const updated = await submitInput({
        session_id: $game.session_id,
        voice_id: voice.voice_id,
        voice_name: voice.voice_name,
        intent_text: voice.intent_text ?? voice.voice_name,
      });
      gameActions.set(updated);
      const warning = (updated as any).soft_warning;
      if (warning) toast.warning(warning.message);
      // 🆕 v2.6 检查应急状态
      checkEmergency();
    } catch (e) {
      const err = e as Error & { status?: number; data?: any };
      if (err.data?.error) {
        toast.warning(err.data.suggestion || err.data.message || '提交失败');
      } else {
        toast.error(err.message || '提交失败');
      }
    } finally {
      isLoading.set(false);
    }
  }

  async function handleFreeInput(text: string) {
    if (!$game || $isLoading) return;
    isLoading.set(true);
    try {
      const updated = await submitInput({
        session_id: $game.session_id,
        text
      });
      gameActions.set(updated);
      const warning = (updated as any).soft_warning;
      if (warning) toast.warning(warning.message);
    } catch (e) {
      const err = e as Error & { status?: number; data?: any };
      // 🆕 v2.10.1 W71: 区分输入级错误（warning = 重试）vs 系统错误（error）
      if (err.status === 400 && err.data?.error) {
        // 玩家输入问题（meta_query/empty/too_long/era_violation）→ warning + 重新输入
        const friendly = err.data.suggestion || err.data.message || '请检查输入';
        toast.warning(friendly);
      } else if (err.status && err.status >= 500) {
        // LLM 失败等系统错误 → error
        toast.error(err.message || '提交失败，请稍后重试');
      } else {
        toast.warning(err.message || '提交失败');
      }
    } finally {
      isLoading.set(false);
    }
  }

  /**
   * 🆕 v2.3: ActionPanel "换一批声音" 回调
   * 拉回新选项后，直接更新 $game.last_voice_options（不动其他字段）
   * 注意：不写回 server state（voice_suggest 注释：建议选项不写回避免污染 DM 下次输入）
   */
  function handleRefreshVoices(newVoices: any[]) {
    if (!$game) return;
    gameActions.set({
      ...$game,
      last_voice_options: newVoices
    });
  }

  // 🆕 v2.6: 应急状态（自动弹窗）
  let emergencyState = $state<{
    show: boolean;
    reason: string;
    trigger: string;
    cards: FateCard[];
  }>({ show: false, reason: '', trigger: '', cards: [] });

  /** 每次叙事更新后检查 emergency 状态 */
  async function checkEmergency() {
    if (!$game) return;
    try {
      const res = await fateEmergencyCheck($game.session_id);
      if (res.is_emergency && res.available_cards.length > 0) {
        emergencyState = {
          show: true,
          reason: res.reason_zh || '紧急时刻',
          trigger: res.trigger || '',
          cards: res.available_cards,
        };
      }
    } catch (e) {
      // 静默失败
    }
  }

  function closeEmergency(usedCardId?: string) {
    emergencyState = { show: false, reason: '', trigger: '', cards: [] };
    if (usedCardId) {
      // 使用了卡：触发后端重新计算（下次 checkEmergency 会反映）
      setTimeout(() => checkEmergency(), 500);
    }
  }
</script>

{#if $game}
  <!-- 🆕 v2.10.1 W69: 章节开场遮罩（开场 narrative round=0 时显示） -->
  {#if showChapterIntro}
    {@const firstNarrative = ($game as any)?.recent_narratives?.[0] ?? null}
    <ChapterIntro
      chapterTitle={firstNarrative?.summary ?? '万历十五年'}
      chapterNumber={1}
      totalChapters={($game as any)?.total_chapters ?? 10}
      summary={firstNarrative?.narrative?.slice(0, 200) ?? ''}
      eraName={$game?.era_name ?? $game?.era_id ?? ''}
      onStart={handleStartChapter}
    />
  {/if}

  <!-- 🆕 v2.10.1 W77: 城市变更确认弹窗 -->
  {#if ($game as any)?.pending_city_change}
    <CityChangeModal
      open={true}
      fromCity={($game as any).pending_city_change.from_city}
      toCity={($game as any).pending_city_change.to_city}
      narrative={($game as any).pending_city_change.narrative ?? ''}
      onConfirm={handleConfirmCity}
      onReject={handleRejectCity}
    />
  {/if}

  <div class="game-view" data-loading={$isLoading}>
    <!-- 左栏：档案 + 任务 + 备忘（豆包式侧栏） -->
    <aside class="game-sidebar">
      <CharCard
        character={$game.character}
        family={$game.family}
        skills={$game.skills}
        collapsible={true}
      />
      <SidebarPanel game={$game} />
    </aside>

    <!-- 右栏：叙事区 + 行动面板（输入条固定底部） -->
    <main class="game-main">
      <!-- 🆕 v2.9.x W50: admin 模式工具面板（?admin=true 才显示） -->
      {#if showAdminTools}
        <aside class="game-admin-panel" aria-label="Admin 工具面板">
          <header class="game-admin-panel-header">
            <h3>🛠️ Admin 模式</h3>
            <a class="game-admin-close" href="?admin=false" aria-label="关闭 admin 模式">
              关闭 ✕
            </a>
          </header>
          <div class="game-admin-grid">
            <PlateMap sessionId={$game.session_id} />
            <ChapterTimeline
              sessionId={$game.session_id}
              currentChapter={$game.current_chapter ?? 0}
              totalChapters={$game.total_chapters ?? 10}
            />
            <MetricsPanel />
          </div>
        </aside>
      {/if}
      <div class="game-narrative-scroll">
        <NarrativeArea narrative={$game.narrative} game={$game} autoScroll={true} />
      </div>
      <ActionPanel
        voices={$game.last_voice_options ?? []}
        valueLevels={($game as any).value_shifts ?? {}}
        sessionId={$game.session_id}
        onselect={handleSelectVoice}
        onfreetext={handleFreeInput}
        onrefresh={handleRefreshVoices}
        loading={$isLoading}
      />
    </main>
  </div>
{:else}
  <div class="game-empty">
    <p>游戏未开始，请先创建角色</p>
  </div>
{/if}

<LoadingOverlay visible={$isLoading} />
<Toast />

<!-- 🆕 v2.6 应急弹出（自动检查 cash<1 / debt>=2 等） -->
{#if $game}
  <EmergencyModal
    show={emergencyState.show}
    sessionId={$game.session_id}
    reason={emergencyState.reason}
    trigger={emergencyState.trigger}
    cards={emergencyState.cards}
    onclose={closeEmergency}
    timeout={emergencyState.cards.length > 0 ? 8 : 0}
  />
{/if}

<style>
  /* ============================================================
   * 豆包式双栏布局
   * - 左栏 280px：档案 + 任务 + 备忘（可独立滚动）
   * - 右栏 1fr：叙事（可滚） + 行动面板（固定底部）
   * - 整体高度撑满 viewport，叙事区可独立滚动
   * ============================================================ */
  .game-view {
    display: grid;
    /* 🆕 v2.7 自适应布局：clamp() 让侧边栏在所有视口平滑变化
     *  - 最小 220px（mobile 不挤压）
     *  - 视口 < 1400 时：clamp(220, 22vw, 280)
     *  - 视口 >= 1400 时：固定 320px
     *  - 右栏始终 1fr
     */
    grid-template-columns: clamp(220px, 22vw, 280px) minmax(0, 1fr);
    gap: var(--space-3);
    padding: var(--space-3);
    height: 100%;
    max-width: 1600px;
    margin: 0 auto;
    overflow: hidden;
  }

  /* 左栏：可独立滚动 */
  .game-sidebar {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: var(--space-1);
  }

  /* 右栏：垂直堆叠（叙事 + 行动面板） */
  .game-main {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
  }

  /* 叙事滚动容器：占满中间区域 */
  .game-narrative-scroll {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .game-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-ink-light);
    font-style: italic;
  }

  /* 加载态 */
  .game-view[data-loading='true'] {
    opacity: 0.7;
    pointer-events: none;
  }

  /* ============================================================
   * Tablet (768-1023): 边栏缩窄
   * ============================================================ */
  @media (max-width: 1023px) {
    .game-view {
      grid-template-columns: 240px minmax(0, 1fr);
      padding: var(--space-2);
      gap: var(--space-2);
    }
  }

  /* ============================================================
   * Mobile (≤ 767): 左栏折叠为顶部横条
   * ============================================================ */
  @media (max-width: 767px) {
    .game-view {
      grid-template-columns: 1fr;
      grid-template-rows: auto minmax(0, 1fr);
      padding: var(--space-2);
      gap: var(--space-2);
    }
    .game-sidebar {
      max-height: 200px;
      flex-direction: row;
      overflow-x: auto;
      overflow-y: hidden;
    }
    .game-sidebar :global(.char-card),
    .game-sidebar :global(.sidebar-panel) {
      flex: 0 0 240px;
    }
  }

  /* ============================================================
   * Wide (≥ 1400): 边栏稍宽（保持 clamp 上限一致）
   * ============================================================ */
  @media (min-width: 1400px) {
    .game-view {
      grid-template-columns: 320px minmax(0, 1fr);
    }
  }

  /* 🆕 v2.7 超大屏（≥ 1800）：边栏定宽，左侧留白 */
  @media (min-width: 1800px) {
    .game-view {
      grid-template-columns: 340px minmax(0, 1fr);
    }
  }

  /* 🆕 v2.7 极窄屏（≤ 480）：侧边栏仅显示 CharCard（命运卡可点展开） */
  @media (max-width: 480px) {
    .game-view {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: auto 1fr;
    }
  }

  /* 🆕 v2.8.x W28 板块地图切换按钮 */
  .plate-map-toggle {
    background: transparent;
    border: 1px dashed rgba(143, 75, 40, 0.4);
    color: var(--color-bronze-dark, #8b6914);
    font-family: var(--font-body);
    font-size: var(--text-xs);
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    margin: 4px 0;
    align-self: flex-start;
  }
  .plate-map-toggle:hover {
    background: rgba(143, 75, 40, 0.06);
  }
  .plate-map-container {
    margin-bottom: var(--space-2);
  }

  /* 🆕 v2.9.x W50: admin 面板样式 */
  .game-admin-panel {
    margin: var(--space-2);
    padding: var(--space-3);
    background: rgba(143, 75, 40, 0.05);
    border: 2px dashed rgba(143, 75, 40, 0.4);
    border-radius: var(--radius-sm);
  }
  .game-admin-panel-header {
    display: flex;
    align-items: center;
    margin-bottom: var(--space-2);
  }
  .game-admin-panel-header h3 {
    margin: 0;
    font-size: var(--text-base);
    color: var(--color-bronze-dark);
  }
  .game-admin-close {
    margin-left: auto;
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    text-decoration: none;
  }
  .game-admin-close:hover {
    color: var(--color-crimson-dark);
  }
  .game-admin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: var(--space-2);
  }
</style>
