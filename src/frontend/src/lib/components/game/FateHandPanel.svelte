<script lang="ts">
  /**
   * FateHandPanel - 命运卡手牌（v2.6 主动使用 + 禁用状态）
   *
   * 三种使用场景：
   *   - immediate: 玩家在自己回合主动点（最常用）
   *   - round_start: 回合开始时可点（buff/AP 卡）
   *   - emergency: 系统应急弹出（失败/危机时）
   *
   * 每张卡显示：
   *   - 卡面（图标 + 名字 + 描述）
   *   - use_hint（何时用最好）
   *   - 禁用原因（如 "R3 后才能用"）
   */
  import { game, gameActions } from '$lib/stores';
  import { fateHand, fateAvailable, fateUse } from '$lib/api/fate';
  import { toast } from '$lib/components/design-system/Toast.svelte';
  import type { FateCard } from '$lib/api/types';

  interface Props {
    hand: FateCard[];
    /** 当前使用场景（默认 immediate） */
    context?: 'immediate' | 'round_start' | 'emergency';
  }

  let { hand, context = 'immediate' }: Props = $props();

  let using = $state<string | null>(null);
  let expanded = $state(true);

  // 实时可用性：拉 /api/fate/available
  let availability = $state<Record<string, { can: boolean; reason: string }>>({});

  $effect(() => {
    if (!$game) return;
    if (hand.length === 0) return;
    fateAvailable($game.session_id, context).then(res => {
      const map: Record<string, { can: boolean; reason: string }> = {};
      for (const c of res.available) {
        map[c.id] = { can: true, reason: '' };
      }
      for (const c of res.unavailable) {
        map[c.id] = { can: false, reason: c._reason };
      }
      availability = map;
    }).catch(() => {});
  });

  async function handleUse(cardId: string) {
    if (using || !$game) return;
    const card = hand.find(c => c.id === cardId);
    if (!card || card.used) return;
    const avail = availability[cardId];
    if (avail && !avail.can) {
      toast.warning(avail.reason);
      return;
    }
    using = cardId;
    try {
      const res = await fateUse($game.session_id, cardId, context);
      if (res.messages && res.messages.length > 0) {
        toast.success(res.messages.join('，'));
      }
      // 更新 game state
      if (res.state) {
        gameActions.set({
          ...$game,
          ...res.state
        } as any);
      }
      // 重新拉取手牌
      const newHand = await fateHand($game.session_id);
      hand = newHand.hand;
    } catch (e) {
      const err = e as Error & { data?: any };
      toast.error(err.data?.reason || err.data?.error || err.message || '触发失败');
    } finally {
      using = null;
    }
  }

  const unused = $derived(hand.filter(c => !c.used));
  const availableCount = $derived(
    hand.filter(c => !c.used && availability[c.id]?.can).length
  );

  // 按 use_type 分组（视觉上分组）
  const grouped = $derived.by(() => {
    const groups: Record<string, FateCard[]> = {
      emergency: [], immediate: [], round_start: [],
    };
    for (const c of hand) {
      const t = c.use_type || 'immediate';
      if (!groups[t]) groups[t] = [];
      groups[t].push(c);
    }
    return groups;
  });

  // 🆕 v2.6.2 分享手牌到剪贴板
  let sharing = $state(false);
  async function handleShare() {
    if (sharing || hand.length === 0) return;
    sharing = true;
    try {
      const lines: string[] = [];
      lines.push('🎴 万历十五年 · 我的命运开局');
      lines.push('─'.repeat(20));
      // 角色名
      if ($game?.character) {
        lines.push(`👤 ${$game.character.name || '玩家'}（${$game.character.occupation || ''}）`);
      }
      lines.push(`🌱 seed: ${$game ? (($game as any).seed ?? '?') : '?'}`);
      lines.push('');
      // 按 use_type 分组展示
      for (const [type, cards] of Object.entries(grouped)) {
        if (cards.length === 0) continue;
        const label = type === 'emergency' ? '⚠️ 应急卡' : type === 'round_start' ? '🌅 回合卡' : '🎯 即时卡';
        lines.push(`【${label}】`);
        for (const c of cards) {
          const usedMark = c.used ? ' ✓已用' : '';
          lines.push(`  ${c.icon} ${c.name}${usedMark} — ${c.description}`);
          if (c.use_hint) {
            lines.push(`    💡 ${c.use_hint}`);
          }
        }
        lines.push('');
      }
      lines.push('— 来自《万历十五年》v2.6.2 —');
      const text = lines.join('\n');

      // 优先用 navigator.clipboard（现代浏览器）
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        toast.success('已复制到剪贴板！');
      } else {
        // 降级方案：旧浏览器/无 https
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        toast.success('已复制到剪贴板（降级方案）');
      }
    } catch (e) {
      toast.error('分享失败：' + (e as Error).message);
    } finally {
      sharing = false;
    }
  }
</script>

{#if hand && hand.length > 0}
  <section class="fate-panel">
    <button
      type="button"
      class="fate-toggle"
      onclick={() => (expanded = !expanded)}
    >
      <span class="fate-toggle-icon" aria-hidden="true">
        {expanded ? '▾' : '▸'}
      </span>
      <span class="fate-toggle-text">命运卡（{availableCount} 张可用）</span>
      <span class="fate-toggle-context" data-context={context}>
        {context === 'emergency' ? '⚠️ 应急' : context === 'round_start' ? '🌅 回合' : '🎯 立即'}
      </span>
    </button>
    <!-- 🆕 v2.6.2 分享按钮 -->
    <button
      type="button"
      class="fate-share"
      onclick={handleShare}
      disabled={sharing}
      title="复制手牌到剪贴板"
      aria-label="分享命运卡"
    >
      {sharing ? '⏳' : '📋'} 分享
    </button>

    {#if expanded}
      {#each Object.entries(grouped) as [type, cards] (type)}
        {#if cards.length > 0}
          <div class="fate-group">
            <div class="fate-group-label">
              {type === 'emergency' ? '⚠️ 应急卡' : type === 'round_start' ? '🌅 回合卡' : '🎯 即时卡'}
              <span class="fate-group-count">{cards.length}</span>
            </div>
            <div class="fate-rail">
              {#each cards as card (card.id)}
                {@const avail = availability[card.id]}
                {@const canUse = !card.used && (avail?.can ?? true)}
                {@const reason = avail?.reason ?? ''}
                <button
                  type="button"
                  class="fate-card"
                  class:fate-card-used={card.used}
                  class:fate-card-disabled={!canUse && !card.used}
                  class:fate-card-emergency={card.use_type === 'emergency'}
                  class:fate-card-round={card.use_type === 'round_start'}
                  disabled={!canUse || using === card.id}
                  onclick={() => handleUse(card.id)}
                  style="--card-color: {card.color}"
                  title={card.used ? '已使用' : (canUse ? card.description : reason)}
                >
                  <span class="fate-card-icon" aria-hidden="true">{card.icon}</span>
                  <span class="fate-card-name">{card.name}</span>
                  <span class="fate-card-desc">{card.description}</span>
                  {#if card.use_hint}
                    <span class="fate-card-hint">{card.use_hint}</span>
                  {/if}
                  {#if card.used}
                    <span class="fate-card-mark">已用</span>
                  {:else if !canUse && reason}
                    <span class="fate-card-lock">🔒 {reason}</span>
                  {/if}
                </button>
              {/each}
            </div>
          </div>
        {/if}
      {/each}
    {/if}
  </section>
{/if}

<style>
  .fate-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-sm);
  }

  .fate-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 0;
    background: transparent;
    border: none;
    color: var(--color-ink-light);
    font-family: var(--font-display);
    font-size: var(--text-xs);
    cursor: pointer;
    text-align: left;
  }

  .fate-toggle-text {
    flex: 1 1 auto;
  }

  .fate-toggle-context {
    flex: 0 0 auto;
    font-family: var(--font-numeric);
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    color: var(--color-paper);
  }
  .fate-toggle-context[data-context="immediate"] {
    background: var(--color-bronze);
  }
  .fate-toggle-context[data-context="round_start"] {
    background: var(--color-cinnabar);
  }
  .fate-toggle-context[data-context="emergency"] {
    background: #4a4a4a;
    animation: pulse-emergency 1.5s ease-in-out infinite;
  }

  /* 🆕 v2.6.2 分享按钮 */
  .fate-share {
    flex: 0 0 auto;
    padding: 2px 8px;
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-sm);
    color: var(--color-ink-light);
    font-family: var(--font-body);
    font-size: 10px;
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .fate-share:hover:not(:disabled) {
    background: var(--color-bronze);
    border-color: var(--color-bronze-dark);
    color: var(--color-paper);
  }

  .fate-share:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @keyframes pulse-emergency {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  .fate-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .fate-group-label {
    font-family: var(--font-body);
    font-size: 10px;
    color: var(--color-ink-light);
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 2px;
  }

  .fate-group-count {
    font-family: var(--font-numeric);
    color: var(--color-ink-faint);
  }

  .fate-rail {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    overflow-y: visible;
    padding: 2px 0;
  }

  .fate-rail::-webkit-scrollbar {
    height: 3px;
  }
  .fate-rail::-webkit-scrollbar-thumb {
    background: var(--color-bronze);
    border-radius: 2px;
  }

  .fate-card {
    flex: 0 0 150px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 8px;
    background: var(--color-paper);
    border: 2px solid var(--card-color, var(--color-bronze));
    border-radius: var(--radius-sm);
    cursor: pointer;
    text-align: center;
    transition: all var(--duration-normal) var(--ease-ink);
    position: relative;
  }

  .fate-card:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(58, 42, 26, 0.15);
  }

  .fate-card:disabled {
    cursor: not-allowed;
  }

  /* 🆕 v2.6 应急卡有阴影 + 边框加粗 */
  .fate-card-emergency {
    border-width: 3px;
    box-shadow: 0 0 8px rgba(165, 40, 40, 0.3);
  }

  /* 🆕 v2.6 回合卡有特殊边框样式 */
  .fate-card-round {
    border-style: dashed;
  }

  /* 🆕 v2.6 禁用状态（条件不满足） */
  .fate-card-disabled {
    opacity: 0.5;
    filter: grayscale(60%);
  }

  .fate-card-used {
    opacity: 0.3;
    background: var(--color-paper-aged);
    filter: grayscale(80%);
  }

  .fate-card-icon {
    font-size: var(--text-xl);
    line-height: 1;
  }

  .fate-card-name {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-ink);
  }

  .fate-card-desc {
    font-family: var(--font-body);
    font-size: 10px;
    color: var(--color-ink-light);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* 🆕 v2.6 use_hint 显示 */
  .fate-card-hint {
    font-family: var(--font-body);
    font-size: 9px;
    color: var(--color-bronze-dark);
    font-style: italic;
    line-height: 1.2;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .fate-card-mark,
  .fate-card-lock {
    position: absolute;
    top: 4px;
    right: 4px;
    font-size: 9px;
    color: var(--color-ink-faint);
    background: var(--color-paper-aged);
    padding: 1px 4px;
    border-radius: 4px;
    line-height: 1.2;
    max-width: 90%;
  }
  .fate-card-lock {
    color: var(--color-cinnabar);
    background: rgba(165, 40, 40, 0.1);
  }
</style>
