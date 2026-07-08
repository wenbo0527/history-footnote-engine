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
  import { Toast, toast } from '$lib/components/design-system';
  import CharCard from './CharCard.svelte';
  import SidebarPanel from './SidebarPanel.svelte';
  import NarrativeArea from './NarrativeArea.svelte';
  import ActionPanel from './ActionPanel.svelte';
  import LoadingOverlay from './LoadingOverlay.svelte';

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
      if (err.data?.error) {
        const friendly = err.data.suggestion || err.data.message || '提交失败';
        toast.warning(friendly);
      } else {
        toast.error(err.message || '提交失败');
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
</script>

{#if $game}
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

<style>
  /* ============================================================
   * 豆包式双栏布局
   * - 左栏 280px：档案 + 任务 + 备忘（可独立滚动）
   * - 右栏 1fr：叙事（可滚） + 行动面板（固定底部）
   * - 整体高度撑满 viewport，叙事区可独立滚动
   * ============================================================ */
  .game-view {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
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
   * Wide (≥ 1400): 边栏稍宽
   * ============================================================ */
  @media (min-width: 1400px) {
    .game-view {
      grid-template-columns: 320px minmax(0, 1fr);
    }
  }
</style>
