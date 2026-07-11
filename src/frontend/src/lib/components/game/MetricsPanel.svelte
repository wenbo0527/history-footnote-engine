<!--
  🆕 v2.9.x W48: MetricsPanel — 性能监控前端面板
  
  30s 轮询 /metrics，显示：
  - Uptime + 总 token
  - 端点表（按 p95 排序）
  - LLM provider 分布
  - 错误率 top 5
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    getMetrics,
    slowestEndpoints,
    totalLLMTokens,
    formatUptime,
    type MetricsResponse,
  } from '$lib/api/metrics';

  let metrics = $state<MetricsResponse | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let lastUpdated = $state<Date | null>(null);
  let pollInterval: ReturnType<typeof setInterval> | null = null;
  const POLL_MS = 30_000;

  async function refresh() {
    try {
      const data = await getMetrics();
      metrics = data;
      lastUpdated = new Date();
      error = null;
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    refresh();
    pollInterval = setInterval(refresh, POLL_MS);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  // 派生
  let slowest = $derived(
    metrics ? slowestEndpoints(metrics, 5) : []
  );
  let tokens = $derived(
    metrics ? totalLLMTokens(metrics) : { prompt: 0, completion: 0, by_provider: {} }
  );

  // 错误率最高的 5 个端点
  let errorHotspots = $derived.by(() => {
    if (!metrics) return [];
    return Object.entries(metrics.endpoints || {})
      .filter(([, m]) => m.error_rate > 0)
      .sort((a, b) => b[1].error_rate - a[1].error_rate)
      .slice(0, 5)
      .map(([endpoint, m]) => ({ endpoint, error_rate: m.error_rate, errors: m.errors }));
  });
</script>

<section class="metrics-panel" aria-label="性能监控">
  <header class="metrics-panel-header">
    <span class="metrics-panel-icon" aria-hidden="true">📊</span>
    <h3 class="metrics-panel-title">性能监控</h3>
    {#if lastUpdated}
      <span class="metrics-panel-updated">
        更新于 {lastUpdated.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </span>
    {/if}
  </header>

  {#if loading}
    <p class="metrics-panel-loading">加载中...</p>
  {:else if error}
    <p class="metrics-panel-error">❌ {error}</p>
  {:else if metrics}
    <!-- 概览卡片 -->
    <div class="metrics-panel-summary">
      <div class="metrics-panel-stat">
        <span class="metrics-panel-stat-label">Uptime</span>
        <span class="metrics-panel-stat-value">{formatUptime(metrics.uptime_seconds)}</span>
      </div>
      <div class="metrics-panel-stat">
        <span class="metrics-panel-stat-label">总端点</span>
        <span class="metrics-panel-stat-value">{Object.keys(metrics.endpoints).length}</span>
      </div>
      <div class="metrics-panel-stat">
        <span class="metrics-panel-stat-label">总 Token</span>
        <span class="metrics-panel-stat-value">{(tokens.prompt + tokens.completion).toLocaleString()}</span>
      </div>
      <div class="metrics-panel-stat">
        <span class="metrics-panel-stat-label">LLM Provider</span>
        <span class="metrics-panel-stat-value">{Object.keys(metrics.llm).length}</span>
      </div>
    </div>

    <!-- 最慢端点 -->
    {#if slowest.length > 0}
      <details class="metrics-panel-section" open>
        <summary>🐢 最慢端点（p95）</summary>
        <table class="metrics-panel-table">
          <thead>
            <tr>
              <th>端点</th>
              <th>次数</th>
              <th>p95 (ms)</th>
            </tr>
          </thead>
          <tbody>
            {#each slowest as s (s.endpoint)}
              <tr>
                <td class="metrics-panel-endpoint">{s.endpoint}</td>
                <td>{s.count}</td>
                <td class="metrics-panel-p95">{s.p95_ms.toFixed(0)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </details>
    {/if}

    <!-- LLM 分布 -->
    {#if Object.keys(metrics.llm).length > 0}
      <details class="metrics-panel-section">
        <summary>🤖 LLM Provider</summary>
        <table class="metrics-panel-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>调用</th>
              <th>平均延迟 (ms)</th>
              <th>总 Token</th>
            </tr>
          </thead>
          <tbody>
            {#each Object.entries(metrics.llm) as [provider, llm] (provider)}
              <tr>
                <td class="metrics-panel-endpoint">{provider}</td>
                <td>{llm.count}</td>
                <td>{llm.avg_latency_ms.toFixed(0)}</td>
                <td>{(llm.total_prompt_tokens + llm.total_completion_tokens).toLocaleString()}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </details>
    {/if}

    <!-- 错误率热点 -->
    {#if errorHotspots.length > 0}
      <details class="metrics-panel-section">
        <summary>⚠️ 错误率热点</summary>
        <table class="metrics-panel-table">
          <thead>
            <tr>
              <th>端点</th>
              <th>错误数</th>
              <th>错误率</th>
            </tr>
          </thead>
          <tbody>
            {#each errorHotspots as e (e.endpoint)}
              <tr class="metrics-panel-error-row">
                <td class="metrics-panel-endpoint">{e.endpoint}</td>
                <td>{e.errors}</td>
                <td class="metrics-panel-error-rate">{(e.error_rate * 100).toFixed(1)}%</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </details>
    {/if}
  {/if}
</section>

<style>
  .metrics-panel {
    padding: var(--space-3, 12px);
    background: var(--color-paper, rgba(255, 245, 220, 0.5));
    border: 1px solid rgba(143, 75, 40, 0.2);
    border-radius: var(--radius-sm, 4px);
    font-size: var(--text-xs, 11px);
  }

  .metrics-panel-header {
    display: flex;
    align-items: center;
    gap: var(--space-2, 8px);
    margin-bottom: var(--space-2, 8px);
  }
  .metrics-panel-icon { font-size: 1.2em; }
  .metrics-panel-title {
    margin: 0;
    font-size: var(--text-base, 14px);
    font-weight: 600;
    color: var(--color-ink, #2a1a0a);
  }
  .metrics-panel-updated {
    margin-left: auto;
    color: var(--color-ink-light, #6a5a4a);
  }

  .metrics-panel-loading,
  .metrics-panel-error {
    color: var(--color-ink-light, #6a5a4a);
    font-style: italic;
  }
  .metrics-panel-error { color: var(--color-crimson-dark, #8a2a1a); }

  .metrics-panel-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-2, 8px);
    margin-bottom: var(--space-3, 12px);
  }
  .metrics-panel-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-2, 8px);
    background: rgba(255, 255, 255, 0.6);
    border-radius: var(--radius-sm, 4px);
  }
  .metrics-panel-stat-label {
    font-size: 10px;
    color: var(--color-ink-light, #6a5a4a);
  }
  .metrics-panel-stat-value {
    font-size: var(--text-base, 14px);
    font-weight: 700;
    color: var(--color-bronze-dark, #6a3a1a);
  }

  .metrics-panel-section {
    margin: var(--space-2, 8px) 0;
  }
  .metrics-panel-section summary {
    cursor: pointer;
    font-weight: 600;
    color: var(--color-ink, #2a1a0a);
    margin-bottom: 4px;
  }
  .metrics-panel-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 10px;
  }
  .metrics-panel-table th,
  .metrics-panel-table td {
    text-align: left;
    padding: 3px 6px;
    border-bottom: 1px solid rgba(143, 75, 40, 0.1);
  }
  .metrics-panel-table th {
    color: var(--color-ink-light, #6a5a4a);
    font-weight: 500;
  }
  .metrics-panel-endpoint {
    font-family: monospace;
    color: var(--color-bronze-dark, #6a3a1a);
  }
  .metrics-panel-p95 {
    color: var(--color-crimson-dark, #8a2a1a);
    font-weight: 600;
  }
  .metrics-panel-error-rate {
    color: var(--color-crimson-dark, #8a2a1a);
    font-weight: 600;
  }
  .metrics-panel-error-row {
    background: rgba(180, 50, 50, 0.05);
  }
</style>
