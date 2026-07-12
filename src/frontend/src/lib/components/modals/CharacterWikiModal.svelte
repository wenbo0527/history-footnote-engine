<script lang="ts">
  /**
   * CharacterWikiModal - 人物关系 Wiki（v2.3 完整版）
   *
   * 🐛 v2.3 修复清单（合计 14 个细节）：
   *   基础 8 项：二次打开/切 session/字段容错/markdown 高度/家人合并/刷新按钮/关闭清状态/章节合并
   *   增量 6 项：
   *     9.  主角卡（玩家自己）置顶 — 让玩家有"这是我"的代入感
   *     10. 描述为空时显示"未详细记录"灰色提示
   *     11. 按"认识时间"排序（先认识在前）
   *     12. affinity 色条（红/黄/绿 = 敌/中/友）
   *     13. 状态徽章（逝/失踪/在世）
   *     14. 错误状态有"返回游戏"按钮
   */
  import { game, gameActions } from '$lib/stores';
  import { getCharacterWiki } from '$lib/api/wiki';
  import { Chapter, Spinner, Button } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';
  import CharacterCard from './CharacterCard.svelte';
  import type { WikiResponse, WikiCharacter, PlayerCharacter, FateNpcEffect, ActiveBuff } from '$lib/api/types';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  // 🆕 v2.10.1 fix: open 不再 $bindable（svelte-check 误报）
  let { open, onclose }: Props = $props();

  let loading = $state(false);
  let wiki: WikiResponse | null = $state(null);
  let error = $state<string | null>(null);
  let lastLoadedSessionId = $state<string | null>(null);
  // 🆕 v2.6.2 命运卡数据
  let npcRelations: Array<[string, number]> = $state([]);
  let fateNpcEffects: FateNpcEffect[] = $state([]);
  let activeBuffs: ActiveBuff[] = $state([]);

  // 🆕 v2.10.2 fix: 关系详注派生（用 wiki.relationships 替代后端不存在的 wiki.markdown）
  const relationshipNotes = $derived.by(() => {
    if (!wiki) return [];
    const notes: Array<{ key: string; name: string; value: string }> = [];
    const rels = (wiki as any).relationships || {};
    for (const [name, info] of Object.entries(rels)) {
      if (typeof info === 'string') {
        notes.push({ key: name, name, value: info });
      } else if (info && typeof info === 'object') {
        // info 可能是 {relation: '家人', level: 5, note: '...'}
        const value = (info as any).note
          || (info as any).relation
          || (info as any).level
          || JSON.stringify(info);
        notes.push({ key: name, name, value: String(value) });
      }
    }
    return notes;
  });

  $effect(() => {
    const sid = $game?.session_id ?? null;
    if (open && sid) {
      if (lastLoadedSessionId !== sid) {
        loadWiki();
      }
    } else if (!open) {
      wiki = null;
      error = null;
    }
  });

  async function loadWiki(force = false) {
    if (!$game) return;
    if (loading) return;
    if (!force && lastLoadedSessionId === $game.session_id && wiki) {
      return;
    }
    loading = true;
    error = null;
    try {
      // 🆕 v2.6.2: getCharacterWiki 返回扩展数据（含 npc_relations/fate_npc_effects/active_buffs）
      const res = await getCharacterWiki($game.session_id) as any;
      wiki = res.wiki ?? res;
      npcRelations = res.npc_relations ?? [];
      fateNpcEffects = res.fate_npc_effects ?? [];
      activeBuffs = res.active_buffs ?? [];
      lastLoadedSessionId = $game.session_id;
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    } finally {
      loading = false;
    }
  }

  function handleRefresh() {
    loadWiki(true);
  }

  // 🆕 主角卡（从 $game 提取）
  const player: PlayerCharacter | null = $derived.by(() => {
    if (!$game?.character) return null;
    return {
      name: $game.character.name || '我',
      identity: $game.character.identity || $game.character.occupation || '织户',
      age: $game.character.age,
      portrait: $game.character.portrait
    };
  });

  // 家庭成员（来自 $game.family）
  const familyChars = $derived(
    ($game?.family ?? []).map((f) => ({
      name: f.name,
      relation: f.relation || '家人',
      age: f.age,
      description: f.status ? `现状：${f.status}` : '一直在身边的人',
      status: 'alive' as const,
      first_met_round: 0,  // 家人开局就在
      isFamily: true,
      affinity: 80  // 默认家人亲近
    }))
  );

  // NPC（来自 wiki）
  const npcs = $derived(wiki?.characters ?? []);

  // 合并去重：家人优先（按 name + identity 标识）
  const allChars = $derived.by(() => {
    const map = new Map<string, WikiCharacter & { isFamily?: boolean; affinity?: number }>();
    // 优先放家人
    for (const f of familyChars) {
      map.set(f.name, f as any);
    }
    // NPC 不同名才加入
    for (const n of npcs) {
      if (!map.has(n.name)) {
        map.set(n.name, { ...n, isFamily: false });
      }
    }
    return Array.from(map.values());
  });

  // 按"认识时间"排序：先认识在前（first_met_round 升序）
  // 同回合按姓名拼音
  const sortedChars = $derived.by(() => {
    return [...allChars].sort((a, b) => {
      const aR = a.first_met_round ?? 999;
      const bR = b.first_met_round ?? 999;
      if (aR !== bR) return aR - bR;
      return a.name.localeCompare(b.name, 'zh-CN');
    });
  });
</script>

<ModalShell {open} {onclose} title="人 物 档 案" size="lg">
  {#snippet headerActions()}
    {#if !loading}
      <button
        type="button"
        class="wiki-refresh"
        onclick={handleRefresh}
        disabled={!$game}
        title="重新拉取人物关系"
        aria-label="刷新人物档案"
      >↻</button>
    {/if}
  {/snippet}

  {#if loading}
    <div class="wiki-loading">
      <Spinner mode="brush" size={48} />
      <p>正在整理人物关系...</p>
    </div>
  {:else if error}
    <!-- 🆕 BUG14: 错误状态有"返回游戏"按钮 -->
    <div class="wiki-error">
      <p class="wiki-error-icon" aria-hidden="true">⚠</p>
      <p class="wiki-error-msg">{error}</p>
      <p class="wiki-error-hint">检查网络后重试，或先继续游戏</p>
      <div class="wiki-error-actions">
        <Button variant="ghost" onclick={onclose}>先继续游戏</Button>
        <Button variant="primary" onclick={() => loadWiki(true)}>重试</Button>
      </div>
    </div>
  {:else}
    <div class="wiki-content">
      <!-- 顶部统计 -->
      <div class="wiki-stats">
        <div class="wiki-stat">
          <span class="wiki-stat-val">{familyChars.length}</span>
          <span class="wiki-stat-label">家人</span>
        </div>
        <div class="wiki-stat">
          <span class="wiki-stat-val">{npcs.length}</span>
          <span class="wiki-stat-label">已登场</span>
        </div>
        <div class="wiki-stat">
          <span class="wiki-stat-val">{sortedChars.length}</span>
          <span class="wiki-stat-label">合计</span>
        </div>
      </div>

      <!-- 🆕 BUG9: 主角卡置顶 -->
      {#if player}
        <Chapter title="我" level={3} />
        <article class="wiki-char-card wiki-char-card-player">
          <div class="wiki-char-portrait" aria-hidden="true">
            {#if player.portrait}
              <img src={player.portrait} alt={player.name} />
            {:else}
              <span class="wiki-char-portrait-emoji">🧑</span>
            {/if}
          </div>
          <div class="wiki-char-body">
            <header class="wiki-char-name">
              <span class="wiki-char-name-text">{player.name}</span>
              <span class="wiki-char-relation wiki-char-relation-self">{player.identity}</span>
            </header>
            {#if player.age}
              <p class="wiki-char-age">{player.age}岁</p>
            {/if}
            <p class="wiki-char-desc">这是你。一切的开始。</p>
          </div>
        </article>
      {/if}

      <!-- 🆕 v2.6.2: 命运卡影响（NPC 关系 + 当前 buff） -->
      {#if fateNpcEffects.length > 0 || activeBuffs.length > 0}
        <Chapter title="🎴 命运影响" level={3} />
        <div class="wiki-fate-effects">
          {#if fateNpcEffects.length > 0}
            <div class="wiki-fate-group">
              <p class="wiki-fate-label">命运卡 → 人物关系：</p>
              <div class="wiki-fate-list">
                {#each fateNpcEffects as eff (eff.card_id + eff.npc)}
                  <div
                    class="wiki-fate-effect"
                    class:wiki-fate-positive={eff.affinity_delta > 0}
                    class:wiki-fate-negative={eff.affinity_delta < 0}
                  >
                    <span class="wiki-fate-icon" aria-hidden="true">{eff.card_icon}</span>
                    <span class="wiki-fate-name">{eff.card_name}</span>
                    <span class="wiki-fate-arrow">→</span>
                    <span class="wiki-fate-npc">{eff.npc}</span>
                    <span class="wiki-fate-delta">
                      {eff.affinity_delta > 0 ? '+' : ''}{eff.affinity_delta}
                    </span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
          {#if activeBuffs.length > 0}
            <div class="wiki-fate-group">
              <p class="wiki-fate-label">当前生效 buff：</p>
              <div class="wiki-fate-list">
                {#each activeBuffs as buff (buff.name)}
                  <div class="wiki-fate-buff">
                    <span class="wiki-fate-icon" aria-hidden="true">✨</span>
                    <span class="wiki-fate-name">{buff.name}</span>
                    <span class="wiki-fate-rounds">剩 {buff.rounds_left} 回合</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      {/if}

      <!-- 登场人物 -->
      <Chapter title="登场人物" level={3} />

      {#if sortedChars.length === 0}
        <div class="wiki-empty-inline">
          <p>还没遇到任何人。继续游戏，他们会出现。</p>
        </div>
      {:else}
        <div class="wiki-characters">
          {#each sortedChars as c, i (i)}
            <CharacterCard character={c} />
          {/each}
        </div>
      {/if}

      <!-- 🆕 v2.10.2 fix: 关系详注（用 wiki.relationships 派生，后端无 markdown 字段） -->
      {#if relationshipNotes.length > 0}
        <Chapter title="关系详注" level={4} />
        <div class="wiki-relations">
          {#each relationshipNotes as note (note.key)}
            <div class="wiki-relation-item">
              <span class="wiki-relation-name">{note.name}</span>
              <span class="wiki-relation-sep">·</span>
              <span class="wiki-relation-value">{note.value}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</ModalShell>

<style>
  .wiki-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-7);
    color: var(--color-ink-light);
    font-style: italic;
  }

  /* 🆕 BUG14: 错误状态视觉 */
  .wiki-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-7);
    text-align: center;
  }
  .wiki-error-icon {
    font-size: 48px;
    color: var(--color-cinnabar);
    margin: 0;
  }
  .wiki-error-msg {
    font-family: var(--font-display);
    font-size: var(--text-md);
    color: var(--color-ink);
    margin: 0;
  }
  .wiki-error-hint {
    font-size: var(--text-sm);
    color: var(--color-ink-faint);
    font-style: italic;
    margin: 0 0 var(--space-3);
  }
  .wiki-error-actions {
    display: flex;
    gap: var(--space-2);
  }

  .wiki-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .wiki-stats {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--color-paper-aged);
    border: 1px dashed var(--color-bronze);
    border-radius: var(--radius-sm);
  }

  .wiki-stat {
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }

  .wiki-stat-val {
    font-family: var(--font-numeric);
    font-size: var(--text-xl);
    font-weight: 600;
    color: var(--color-bronze-dark);
    line-height: 1;
  }

  .wiki-stat-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }

  .wiki-refresh {
    flex: 0 0 auto;
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid var(--color-ink-faint);
    border-radius: 50%;
    color: var(--color-ink-light);
    font-size: 16px;
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }
  .wiki-refresh:hover:not(:disabled) {
    background: var(--color-bronze);
    border-color: var(--color-bronze-dark);
    color: var(--color-paper);
    transform: rotate(45deg);
  }
  .wiki-refresh:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .wiki-markdown {
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
    padding: var(--space-4);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    line-height: var(--leading-relaxed);
    color: var(--color-ink);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 50vh;
    overflow-y: auto;
  }

  .wiki-characters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: var(--space-3);
  }

  .wiki-char-card {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    border-left: 3px solid var(--color-bronze);
    position: relative;
  }

  .wiki-char-card-family {
    background: linear-gradient(135deg, var(--color-paper) 0%, rgba(184, 134, 11, 0.06) 100%);
    border-color: var(--color-bronze-dark);
    border-left-color: var(--color-bronze-dark);
  }

  /* 🆕 BUG9: 主角卡用朱砂色边框 */
  .wiki-char-card-player {
    background: linear-gradient(135deg, rgba(165, 40, 40, 0.08) 0%, var(--color-paper) 100%);
    border-color: var(--color-cinnabar);
    border-left: 4px solid var(--color-cinnabar);
  }

  /* 🆕 BUG12: affinity 色条 */
  .wiki-char-card[style*='--aff-color'] {
    border-left-color: var(--aff-color, var(--color-bronze));
  }

  .wiki-char-portrait {
    flex: 0 0 56px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
  }

  .wiki-char-portrait img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .wiki-char-portrait-emoji {
    font-size: 28px;
  }

  /* 🆕 BUG13: 状态徽章 */
  .wiki-char-status {
    position: absolute;
    top: -4px;
    right: -4px;
    font-size: 10px;
    color: white;
    padding: 1px 4px;
    border-radius: 4px;
    line-height: 1.2;
    letter-spacing: -0.5px;
  }

  .wiki-char-body {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .wiki-char-name {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-display);
    font-size: var(--text-base);
    font-weight: 600;
    color: var(--color-ink);
  }

  .wiki-char-name-text {
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .wiki-char-relation {
    flex: 0 0 auto;
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    padding: 2px 8px;
    background: var(--color-paper-aged);
    border-radius: var(--radius-sm);
    white-space: nowrap;
  }

  .wiki-char-relation-family {
    color: var(--color-bronze-dark);
    background: rgba(184, 134, 11, 0.12);
  }

  .wiki-char-relation-self {
    color: white;
    background: var(--color-cinnabar);
  }

  .wiki-char-meta {
    font-family: var(--font-numeric);
    font-size: 11px;
    color: var(--color-ink-faint);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .wiki-char-meta-sep {
    color: var(--color-ink-faint);
  }

  .wiki-char-desc {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    line-height: var(--leading-snug);
    margin: 0;
  }

  /* 🆕 BUG10: 描述为空的灰提示 */
  .wiki-char-desc-empty {
    color: var(--color-ink-faint);
    font-style: italic;
  }

  /* 🆕 BUG12: affinity 条 */
  .wiki-char-aff {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 4px;
  }

  .wiki-char-aff-bar {
    flex: 1 1 auto;
    height: 4px;
    border-radius: 2px;
    opacity: 0.7;
    transition: width var(--duration-slow) var(--ease-ink);
  }

  .wiki-char-aff-label {
    font-family: var(--font-display);
    font-size: 10px;
    color: var(--color-ink-light);
    flex: 0 0 auto;
    letter-spacing: var(--tracking-wide);
  }

  .wiki-char-age {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-ink-faint);
    margin: 0;
  }

  .wiki-empty-inline {
    text-align: center;
    color: var(--color-ink-faint);
    font-style: italic;
    padding: var(--space-4) 0;
  }

  /* 🆕 v2.6.2 命运影响段 */
  .wiki-fate-effects {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2);
    background: linear-gradient(180deg, var(--color-paper-aged) 0%, var(--color-paper) 100%);
    border: 1px dashed var(--color-bronze);
    border-radius: var(--radius-sm);
  }

  .wiki-fate-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .wiki-fate-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    margin: 0;
  }

  .wiki-fate-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .wiki-fate-effect,
  .wiki-fate-buff {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: 12px;
    font-family: var(--font-body);
    font-size: var(--text-xs);
  }

  .wiki-fate-positive {
    border-color: #6b8b5a;
    background: rgba(107, 139, 90, 0.08);
  }

  .wiki-fate-negative {
    border-color: #a52828;
    background: rgba(165, 40, 40, 0.08);
  }

  .wiki-fate-icon {
    font-size: var(--text-sm);
    line-height: 1;
  }

  .wiki-fate-name {
    color: var(--color-ink);
    font-weight: 600;
  }

  .wiki-fate-arrow {
    color: var(--color-ink-faint);
  }

  .wiki-fate-npc {
    color: var(--color-ink-light);
  }

  .wiki-fate-delta {
    font-family: var(--font-numeric);
    font-weight: 600;
    color: #6b8b5a;
  }
  .wiki-fate-negative .wiki-fate-delta {
    color: #a52828;
  }

  .wiki-fate-rounds {
    font-family: var(--font-numeric);
    color: var(--color-bronze-dark);
    font-size: 10px;
  }

  @media (max-width: 600px) {
    .wiki-characters {
      grid-template-columns: 1fr;
    }
    .wiki-char-card {
      padding: var(--space-2);
    }
  }

  /* 🆕 v2.10.2 fix: 关系详注样式 */
  .wiki-relations {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-3);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-md);
  }
  .wiki-relation-item {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
    font-size: var(--text-sm);
    line-height: var(--leading-snug);
  }
  .wiki-relation-name {
    font-family: var(--font-display);
    font-weight: 600;
    color: var(--color-ink);
    min-width: 60px;
  }
  .wiki-relation-sep {
    color: var(--color-ink-faint);
  }
  .wiki-relation-value {
    flex: 1 1 auto;
    color: var(--color-ink-light);
  }
</style>
