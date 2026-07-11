/**
 * 🆕 v2.9.x W47: 性能监控前端 API
 *
 * 后端 /metrics 返回结构（来自 MetricsCollector.snapshot()）：
 * {
 *   uptime_seconds: number,
 *   endpoints: {
 *     [name]: {
 *       count, avg_ms, p50_ms, p95_ms, p99_ms, errors, error_rate
 *     }
 *   },
 *   llm: {
 *     [provider]: {
 *       count, total_prompt_tokens, total_completion_tokens,
 *       avg_prompt_tokens, avg_completion_tokens,
 *       avg_latency_ms, p50_latency_ms, p95_latency_ms
 *     }
 *   },
 *   tool_cache: { ... },
 *   rate_limiter: { ... },
 *   llm_throttle: { ... }
 * }
 */
import { api } from './client';

export interface EndpointMetrics {
  count: number;
  avg_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  errors: number;
  error_rate: number;
}

export interface LLMMetrics {
  count: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
}

export interface MetricsResponse {
  uptime_seconds: number;
  endpoints: Record<string, EndpointMetrics>;
  llm: Record<string, LLMMetrics>;
  tool_cache?: Record<string, any>;
  rate_limiter?: Record<string, any>;
  llm_throttle?: Record<string, any>;
}

/**
 * GET /metrics — 获取所有性能指标快照
 */
export async function getMetrics(): Promise<MetricsResponse> {
  return api<MetricsResponse>('/metrics');
}

/**
 * 派生：找出最慢端点（按 p95 排序）
 */
export function slowestEndpoints(
  metrics: MetricsResponse,
  limit: number = 5
): Array<{ endpoint: string; p95_ms: number; count: number }> {
  return Object.entries(metrics.endpoints || {})
    .map(([endpoint, m]) => ({ endpoint, p95_ms: m.p95_ms, count: m.count }))
    .sort((a, b) => b.p95_ms - a.p95_ms)
    .slice(0, limit);
}

/**
 * 派生：总 LLM token 用量
 */
export function totalLLMTokens(metrics: MetricsResponse): {
  prompt: number;
  completion: number;
  by_provider: Record<string, { prompt: number; completion: number }>;
} {
  let prompt = 0;
  let completion = 0;
  const by_provider: Record<string, { prompt: number; completion: number }> = {};
  for (const [provider, llm] of Object.entries(metrics.llm || {})) {
    prompt += llm.total_prompt_tokens;
    completion += llm.total_completion_tokens;
    by_provider[provider] = {
      prompt: llm.total_prompt_tokens,
      completion: llm.total_completion_tokens,
    };
  }
  return { prompt, completion, by_provider };
}

/**
 * 派生：Uptime 人类可读格式
 */
export function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}
