<script lang="ts">
  /**
   * EndingModal - 🆕 v2.10.33 P0-3 结局结算弹窗
   *
   * 当玩家触发任一 8 种结局时（破产/小康/抗税/出海...）自动弹出
   * - 大标题 + 图标 + 叙事模板
   * - 触发时的财务快照（cash/debt/rice/city/round）
   * - 玩家关闭后回到首页，可开新档或回看往事
   *
   * 触发逻辑在 GameView：当 game.ending 非空时显示
   */
  import { goto } from '$app/navigation';
  import { Chapter, Button, Seal, Icon } from '$lib/components/design-system';
  import ModalShell from './ModalShell.svelte';
  import type { Ending } from '$lib/api/types';

  interface Props {
    open: boolean;
    ending: Ending | null | undefined;
    onclose: () => void;
  }

  let { open, ending, onclose }: Props = $props();

  /**
   * 8 种结局的中文副标题（icon + 一句话点睛）
   * 用于弹窗头部的"小标题"
   */
  const ENDING_TAGLINE: Record<string, string> = {
    merchant_empire: '江南丝绸王，三十年织机人生',
    scholar_success: '弃织从文，三十岁中举人',
    overseas_pioneer: '从盛泽到月港，跨海丝路',
    loyal_resist: '万历二十九年，葛贤抗税的同年',
    peaceful_family: '守住一方小院，子孙绕膝',
    comfortable: '三十两家底，踏实过活',
    struggling: '小冰河期咬牙撑住的普通人',
    bankrupt_beggar: '织机被收，加入流民群',
  };

  const tagline = $derived(
    ending ? (ENDING_TAGLINE[ending.type] ?? ending.name) : ''
  );

  function handleClose() {
    onclose?.();
  }

  function handleGoHome() {
    handleClose();
    setTimeout(() => goto('/'), 200);
  }

  function handleBackToStart() {
    handleClose();
    setTimeout(() => goto('/'), 200);
  }
</script>

<ModalShell {open} {onclose} title="往 事 已 矣" size="lg">
  {#if ending}
    <div class="ending-content">
      <!-- 头部：图标 + 结局名 -->
      <header class="ending-header">
        <div class="ending-icon" aria-hidden="true">{ending.icon}</div>
        <div class="ending-title-wrap">
          <Chapter title={ending.name} level={1} />
          <p class="ending-tagline">{tagline}</p>
        </div>
      </header>

      <!-- 触发回合 -->
      <div class="ending-round">
        <Icon name="calendar" size={14} />
        <span>触发于 <strong>第 {ending.triggered_round} 回合</strong></span>
        {#if ending.snapshot?.current_date}
          <span class="ending-date">· {ending.snapshot.current_date}</span>
        {/if}
      </div>

      <!-- 主体：叙事模板 -->
      <article class="ending-narrative">
        <p>{ending.narrative}</p>
      </article>

      <!-- 财务快照（如果有） -->
      {#if ending.snapshot}
        <section class="ending-snapshot">
          <h3 class="ending-snapshot-title">终局账本</h3>
          <div class="ending-snapshot-grid">
            <div class="snapshot-item">
              <span class="snapshot-label">现银</span>
              <span class="snapshot-value" class:negative={(ending.snapshot.cash ?? 0) < 0}>
                {(ending.snapshot.cash ?? 0).toFixed(2)} 两
              </span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">欠债</span>
              <span class="snapshot-value" class:warning={(ending.snapshot.debt ?? 0) > 0}>
                {(ending.snapshot.debt ?? 0).toFixed(2)} 两
              </span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">存粮</span>
              <span class="snapshot-value">
                {(ending.snapshot.rice ?? 0).toFixed(1)} 石
              </span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">所在</span>
              <span class="snapshot-value">
                {ending.snapshot.city === 'shengze' ? '盛泽镇'
                  : ending.snapshot.city === 'suzhou' ? '苏州府'
                  : ending.snapshot.city === 'yuegang' ? '福建月港'
                  : ending.snapshot.city || '—'}
              </span>
            </div>
          </div>
        </section>
      {/if}

      <!-- 提示：再玩 -->
      <footer class="ending-footer">
        <p class="ending-hint">
          每一条路、每一个数字都来自你的选择。可以重新开局，看看另一种活法。
        </p>
        <div class="ending-actions">
          <Button variant="ghost" size="md" onclick={handleClose}>关 闭</Button>
          <Seal text="回 首 页" size="md" onclick={handleGoHome} />
        </div>
      </footer>
    </div>
  {:else}
    <p class="ending-empty">（暂无结局数据）</p>
  {/if}
</ModalShell>

<style>
  .ending-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  .ending-header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-3) 0;
    border-bottom: 2px solid var(--color-bronze);
  }

  .ending-icon {
    font-size: 64px;
    line-height: 1;
    flex-shrink: 0;
    filter: drop-shadow(0 2px 8px rgba(143, 75, 40, 0.3));
  }

  .ending-title-wrap {
    flex: 1;
    min-width: 0;
  }

  .ending-tagline {
    margin: var(--space-2) 0 0;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    font-style: italic;
  }

  .ending-round {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-family: var(--font-numeric);
    font-size: var(--text-sm);
    color: var(--color-bronze-dark);
    margin: 0;
  }

  .ending-round strong {
    color: var(--color-cinnabar);
    font-weight: 700;
  }

  .ending-date {
    margin-left: var(--space-2);
    color: var(--color-ink-light);
  }

  .ending-narrative {
    padding: var(--space-4) var(--space-5);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-bronze);
    border-left: 4px solid var(--color-cinnabar);
    border-radius: var(--radius-sm);
  }

  .ending-narrative p {
    margin: 0;
    font-family: var(--font-body);
    font-size: var(--text-md);
    line-height: var(--leading-relaxed);
    color: var(--color-ink);
    text-indent: 2em;
    letter-spacing: 0.02em;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .ending-snapshot {
    padding: var(--space-3) 0;
  }

  .ending-snapshot-title {
    margin: 0 0 var(--space-3);
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 600;
    color: var(--color-cinnabar);
    letter-spacing: 0.1em;
  }

  .ending-snapshot-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-3);
  }

  .snapshot-item {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-3);
    background: var(--color-paper);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-sm);
  }

  .snapshot-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }

  .snapshot-value {
    font-family: var(--font-numeric);
    font-size: var(--text-lg);
    color: var(--color-ink);
    font-weight: 600;
  }

  .snapshot-value.negative {
    color: var(--color-cinnabar);
  }

  .snapshot-value.warning {
    color: var(--color-bronze-dark);
  }

  .ending-footer {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding-top: var(--space-3);
    border-top: 1px solid var(--color-ink-faint);
  }

  .ending-hint {
    margin: 0;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--color-ink-light);
    font-style: italic;
    text-align: center;
  }

  .ending-actions {
    display: flex;
    gap: var(--space-3);
    justify-content: center;
  }

  .ending-empty {
    text-align: center;
    color: var(--color-ink-faint);
    padding: var(--space-5);
  }
</style>