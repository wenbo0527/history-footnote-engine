/**
 * 🆕 v2.10.x W56: alerts 测试
 */
import { describe, it, expect } from 'vitest';
import { checkAlerts, sortAlerts, alertSeverity, type Alert } from './alerts';
import type { MetricsResponse } from './metrics';

const makeMetrics = (overrides: Partial<MetricsResponse> = {}): MetricsResponse => ({
  uptime_seconds: 100,
  endpoints: {},
  llm: {},
  ...overrides,
});

describe('W56: checkAlerts', () => {
  it('空 metrics → 无告警', () => {
    expect(checkAlerts(makeMetrics())).toEqual([]);
  });

  it('端点 p95 超阈值', () => {
    const m = makeMetrics({
      endpoints: {
        '/api/test': {
          count: 10, avg_ms: 1000, p50_ms: 1000, p95_ms: 5000, p99_ms: 8000,
          errors: 0, error_rate: 0,
        },
      },
    });
    const alerts = checkAlerts(m, { p95_ms: 3000 });
    expect(alerts).toHaveLength(1);
    expect(alerts[0].type).toBe('endpoint_p95');
    expect(alerts[0].severity).toBe('warning');
  });

  it('p95 超 2 倍 → critical', () => {
    const m = makeMetrics({
      endpoints: {
        '/api/test': {
          count: 10, avg_ms: 1000, p50_ms: 1000, p95_ms: 7000, p99_ms: 10000,
          errors: 0, error_rate: 0,
        },
      },
    });
    const alerts = checkAlerts(m, { p95_ms: 3000 });
    expect(alerts[0].severity).toBe('critical');
  });

  it('端点错误率超阈值', () => {
    const m = makeMetrics({
      endpoints: {
        '/api/test': {
          count: 100, avg_ms: 100, p50_ms: 100, p95_ms: 200, p99_ms: 300,
          errors: 10, error_rate: 0.10,
        },
      },
    });
    const alerts = checkAlerts(m, { error_rate: 0.05 });
    expect(alerts).toHaveLength(1);
    expect(alerts[0].type).toBe('endpoint_error');
  });

  it('LLM p95 超阈值', () => {
    const m = makeMetrics({
      llm: {
        openai: {
          count: 10, total_prompt_tokens: 100, total_completion_tokens: 50,
          avg_prompt_tokens: 10, avg_completion_tokens: 5,
          avg_latency_ms: 2000, p50_latency_ms: 2000, p95_latency_ms: 8000,
        },
      },
    });
    const alerts = checkAlerts(m, { llm_p95_ms: 5000 });
    expect(alerts).toHaveLength(1);
    expect(alerts[0].type).toBe('llm_latency');
  });

  it('多个告警同时触发', () => {
    const m = makeMetrics({
      endpoints: {
        '/api/a': {
          count: 10, avg_ms: 100, p50_ms: 100, p95_ms: 5000, p99_ms: 5000,
          errors: 0, error_rate: 0,
        },
        '/api/b': {
          count: 10, avg_ms: 100, p50_ms: 100, p95_ms: 100, p99_ms: 100,
          errors: 5, error_rate: 0.50,
        },
      },
    });
    const alerts = checkAlerts(m, { p95_ms: 3000, error_rate: 0.05 });
    expect(alerts).toHaveLength(2);
  });
});

describe('W56: sortAlerts + alertSeverity', () => {
  const make = (severity: 'info' | 'warning' | 'critical'): Alert => ({
    type: 'endpoint_p95',
    severity,
    message: 'x',
    value: 1,
    threshold: 1,
    timestamp: 0,
  });

  it('alertSeverity 排序', () => {
    expect(alertSeverity(make('info'))).toBe(0);
    expect(alertSeverity(make('warning'))).toBe(1);
    expect(alertSeverity(make('critical'))).toBe(2);
  });

  it('sortAlerts critical 优先', () => {
    const sorted = sortAlerts([make('info'), make('critical'), make('warning')]);
    expect(sorted[0].severity).toBe('critical');
    expect(sorted[2].severity).toBe('info');
  });

  it('sortAlerts 不修改原数组', () => {
    const orig = [make('info'), make('critical')];
    sortAlerts(orig);
    expect(orig[0].severity).toBe('info');
  });
});
