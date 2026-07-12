/**
 * 🆕 v2.10.x W56: MetricsPanel 告警系统
 *
 * 阈值检测：
 * - p95_latency > threshold
 * - error_rate > threshold
 * - LLM token 用量异常
 *
 * 用法：
 *   const alerts = checkAlerts(metrics, { p95_threshold: 3000, error_threshold: 0.05 });
 *   alerts.forEach(a => console.log(a.severity, a.message));
 */
import type { MetricsResponse } from '$lib/api/metrics';

export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface Alert {
  type: 'endpoint_p95' | 'endpoint_error' | 'llm_latency' | 'uptime';
  severity: AlertSeverity;
  endpoint?: string;
  provider?: string;
  message: string;
  value: number;
  threshold: number;
  timestamp: number;
}

export interface AlertThresholds {
  p95_ms?: number;       // 默认 3000ms
  error_rate?: number;   // 默认 0.05 (5%)
  llm_p95_ms?: number;   // 默认 5000ms
  uptime_min_seconds?: number; // 默认 0
}

const DEFAULTS: Required<AlertThresholds> = {
  p95_ms: 3000,
  error_rate: 0.05,
  llm_p95_ms: 5000,
  uptime_min_seconds: 0,
};

export function checkAlerts(
  metrics: MetricsResponse,
  thresholds: AlertThresholds = {}
): Alert[] {
  const t = { ...DEFAULTS, ...thresholds };
  const alerts: Alert[] = [];
  const now = Date.now();

  // 端点 p95
  for (const [endpoint, m] of Object.entries(metrics.endpoints || {})) {
    if (m.p95_ms > t.p95_ms) {
      alerts.push({
        type: 'endpoint_p95',
        severity: m.p95_ms > t.p95_ms * 2 ? 'critical' : 'warning',
        endpoint,
        message: `${endpoint} p95 ${m.p95_ms.toFixed(0)}ms > ${t.p95_ms}ms`,
        value: m.p95_ms,
        threshold: t.p95_ms,
        timestamp: now,
      });
    }
    if (m.error_rate > t.error_rate) {
      alerts.push({
        type: 'endpoint_error',
        severity: m.error_rate > 0.2 ? 'critical' : 'warning',
        endpoint,
        message: `${endpoint} 错误率 ${(m.error_rate * 100).toFixed(1)}% > ${(t.error_rate * 100).toFixed(1)}%`,
        value: m.error_rate,
        threshold: t.error_rate,
        timestamp: now,
      });
    }
  }

  // LLM p95
  for (const [provider, llm] of Object.entries(metrics.llm || {})) {
    if (llm.p95_latency_ms > t.llm_p95_ms) {
      alerts.push({
        type: 'llm_latency',
        severity: llm.p95_latency_ms > t.llm_p95_ms * 2 ? 'critical' : 'warning',
        provider,
        message: `${provider} LLM p95 ${llm.p95_latency_ms.toFixed(0)}ms > ${t.llm_p95_ms}ms`,
        value: llm.p95_latency_ms,
        threshold: t.llm_p95_ms,
        timestamp: now,
      });
    }
  }

  return alerts;
}

export function alertSeverity(alert: Alert): number {
  return { info: 0, warning: 1, critical: 2 }[alert.severity] ?? 0;
}

export function sortAlerts(alerts: Alert[]): Alert[] {
  return [...alerts].sort((a, b) => alertSeverity(b) - alertSeverity(a));
}
