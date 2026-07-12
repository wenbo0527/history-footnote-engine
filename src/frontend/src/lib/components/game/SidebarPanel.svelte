<script lang="ts">
  /**
   * SidebarPanel - 左栏底部（v2.2 新增）
   *
   * 合并显示：
   *   - 财务状态（💰 银两 / 🌾 米 / 💳 债 / 月支出）
   *   - 进行中任务
   *   - 即将到期
   *   - 时间线（大事记）
   *
   * 参考豆包左侧的"对话列表"——所有次要信息聚合在侧栏
   */
  import type { GameState } from '$lib/api/types';
  import { Chapter } from '$lib/components/design-system';
  import { locationList } from '$lib/api/location';
  // 🆕 v2.10.2: 银钱单位统一（两/钱/分/厘）
  import { toCompactLiang, toLiangOrYuan } from '$lib/utils/currency';
  import { fateHand } from '$lib/api/fate';
  import type { LocationListResponse, FateCard } from '$lib/api/types';
  import LocationPanel from './LocationPanel.svelte';
  import FateHandPanel from './FateHandPanel.svelte';

  interface Props {
    game: GameState;
  }

  let { game }: Props = $props();

  // 🆕 v2.4: location data（侧栏顶部显示）
  let locationData = $state<LocationListResponse | null>(null);
  // 🆕 v2.5: 命运卡手牌
  let fateHandData = $state<FateCard[]>([]);
  $effect(() => {
    if (game?.session_id) {
      locationList(game.session_id).then(d => locationData = d).catch(() => {});
      fateHand(game.session_id).then(d => fateHandData = d.hand).catch(() => {});
    }
  });

  // 财务告警
  const cashWarning = $derived(game.cash < 1);
  const debtWarning = $derived(game.debt > 5);
</script>

<div class="sidebar-panel">
  <!-- 🆕 v2.4: 当前位置 + 移动选项 -->
  {#if locationData}
    <LocationPanel data={locationData} />
  {/if}

  <!-- 🆕 v2.5: 命运卡手牌 -->
  {#if fateHandData && fateHandData.length > 0}
    <FateHandPanel hand={fateHandData} />
  {/if}

  <!-- 财务 -->
  <section class="sidebar-section">
    <Chapter title="💰 银钱往来" level={4} />
    <div class="fin-grid">
      <div class="fin-item" class:fin-item-warn={cashWarning}>
        <span class="fin-label">银两</span>
        <!-- 🆕 v2.10.2: 紧凑显示 (5.7 → "5 两 7 钱") -->
        <span class="fin-value" title={toLiangOrYuan(game.cash)}>{toCompactLiang(game.cash)}</span>
      </div>
      <div class="fin-item">
        <span class="fin-label">米</span>
        <span class="fin-value">{game.rice}</span>
      </div>
      <div class="fin-item" class:fin-item-warn={debtWarning}>
        <span class="fin-label">欠债</span>
        <!-- 🆕 v2.10.2: 紧凑显示 -->
        <span class="fin-value" title={toLiangOrYuan(game.debt)}>{toCompactLiang(game.debt)}</span>
      </div>
      <div class="fin-item">
        <span class="fin-label">月支出</span>
        <!-- 🆕 v2.10.2: 紧凑显示 -->
        <span class="fin-value" title={toLiangOrYuan(game.monthly_burn)}>{toCompactLiang(game.monthly_burn)}</span>
      </div>
    </div>
  </section>

  <!-- 进行中任务 -->
  {#if game.sidebar?.active_tasks?.length}
    <section class="sidebar-section">
      <Chapter title="📌 手头的事" level={4} />
      <ul class="task-list">
        {#each game.sidebar.active_tasks as t, i (i)}
          <li class="task-item task-urgency-{t.urgency}">
            <span class="task-marker" aria-hidden="true">
              {t.urgency === 'high' ? '●' : t.urgency === 'medium' ? '◐' : '○'}
            </span>
            <span class="task-title">{t.title}</span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- 即将到期 -->
  {#if game.sidebar?.upcoming_deadlines?.length}
    <section class="sidebar-section">
      <Chapter title="⏰ 近日要紧" level={4} />
      <ul class="deadline-list">
        {#each game.sidebar.upcoming_deadlines as d, i (i)}
          <li class="deadline-item">
            <span class="deadline-name">{d.name}</span>
            {#if d.days_estimate !== undefined}
              <span class="deadline-days">{d.days_estimate} 日</span>
            {/if}
            {#if d.amount}
              <span class="deadline-amount">{d.amount}</span>
            {/if}
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- 时间线 -->
  {#if game.timeline?.length}
    <section class="sidebar-section">
      <Chapter title="📜 大事记" level={4} />
      <ol class="timeline-list">
        {#each game.timeline as ev, i (i)}
          <li class="timeline-item" class:timeline-item-highlight={ev.highlight}>
            <span class="timeline-year">{ev.year}</span>
            <span class="timeline-event">{ev.event}</span>
          </li>
        {/each}
      </ol>
    </section>
  {/if}
</div>

<style>
  .sidebar-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-bronze);
    border-radius: var(--radius-md);
  }

  .sidebar-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  /* 财务 */
  .fin-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-2);
  }

  .fin-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: var(--space-2);
    background: var(--color-paper-aged);
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
  }

  .fin-item-warn {
    background: rgba(165, 40, 40, 0.08);
    border-color: var(--color-cinnabar);
  }

  .fin-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }

  .fin-value {
    font-family: var(--font-numeric);
    font-size: var(--text-md);
    color: var(--color-ink);
    font-weight: 600;
  }

  .fin-item-warn .fin-value {
    color: var(--color-cinnabar);
  }

  /* 任务 */
  .task-list, .deadline-list, .timeline-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .task-item {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    padding: 4px 0;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
    line-height: var(--leading-snug);
  }

  .task-marker {
    flex: 0 0 auto;
    font-size: var(--text-xs);
    line-height: 1.4;
  }

  .task-urgency-high .task-marker { color: var(--color-cinnabar); }
  .task-urgency-medium .task-marker { color: var(--color-bronze-dark); }
  .task-urgency-low .task-marker { color: var(--color-ink-faint); }

  .task-title {
    flex: 1 1 auto;
  }

  /* 截止日 */
  .deadline-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink);
  }

  .deadline-name {
    flex: 1 1 auto;
  }

  .deadline-days {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-cinnabar);
    font-weight: 600;
  }

  .deadline-amount {
    font-family: var(--font-numeric);
    font-size: var(--text-xs);
    color: var(--color-bronze-dark);
  }

  /* 时间线 */
  .timeline-item {
    display: flex;
    gap: 6px;
    padding: 4px 0;
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
    line-height: var(--leading-snug);
  }

  .timeline-item-highlight {
    color: var(--color-ink);
  }

  .timeline-year {
    flex: 0 0 auto;
    font-family: var(--font-numeric);
    font-weight: 600;
    color: var(--color-bronze-dark);
  }

  .timeline-item-highlight .timeline-year {
    color: var(--color-cinnabar);
  }

  .timeline-event {
    flex: 1 1 auto;
  }
</style>
