/**
 * 🆕 v2.9.x W47: Metrics API + 派生函数测试
 */
import { describe, it, expect, vi } from 'vitest';
import {
  getMetrics,
  slowestEndpoints,
  totalLLMTokens,
  formatUptime,
  type MetricsResponse,
} from './metrics';
import { api } from './client';

vi.mock('$lib/api/client', () => ({
  api: vi.fn(),
}));
const mockedApi = vi.mocked(api);

const sampleMetrics: MetricsResponse = {
  uptime_seconds: 3725,
  endpoints: {
    '/api/input': {
      count: 100, avg_ms: 1100, p50_ms: 950, p95_ms: 2500, p99_ms: 4500,
      errors: 2, error_rate: 0.02,
    },
    '/api/chapter/state': {
      count: 50, avg_ms: 50, p50_ms: 40, p95_ms: 120, p99_ms: 200,
      errors: 0, error_rate: 0,
    },
    '/api/chapter/blueprint': {
      count: 20, avg_ms: 80, p50_ms: 70, p95_ms: 180, p99_ms: 250,
      errors: 0, error_rate: 0,
    },
  },
  llm: {
    'minimax-anthropic': {
      count: 100, total_prompt_tokens: 100000, total_completion_tokens: 20000,
      avg_prompt_tokens: 1000, avg_completion_tokens: 200,
      avg_latency_ms: 1500, p50_latency_ms: 1400, p95_latency_ms: 3500,
    },
    'openai': {
      count: 10, total_prompt_tokens: 5000, total_completion_tokens: 1000,
      avg_prompt_tokens: 500, avg_completion_tokens: 100,
      avg_latency_ms: 800, p50_latency_ms: 750, p95_latency_ms: 1200,
    },
  },
};

describe('W47: Metrics API', () => {
  it('getMetrics calls /metrics endpoint', async () => {
    mockedApi.mockResolvedValueOnce(sampleMetrics);
    const result = await getMetrics();
    expect(mockedApi).toHaveBeenCalledWith('/metrics');
    expect(result.uptime_seconds).toBe(3725);
    expect(Object.keys(result.endpoints)).toHaveLength(3);
    expect(Object.keys(result.llm)).toHaveLength(2);
  });

  it('handles network error', async () => {
    mockedApi.mockRejectedValueOnce(new Error('Network error'));
    await expect(getMetrics()).rejects.toThrow('Network error');
  });
});

describe('slowestEndpoints', () => {
  it('returns top N by p95_ms', () => {
    const slowest = slowestEndpoints(sampleMetrics, 2);
    expect(slowest).toHaveLength(2);
    expect(slowest[0].endpoint).toBe('/api/input');
    expect(slowest[0].p95_ms).toBe(2500);
    expect(slowest[1].endpoint).toBe('/api/chapter/blueprint');
    expect(slowest[1].p95_ms).toBe(180);
  });

  it('returns all when limit > count', () => {
    const slowest = slowestEndpoints(sampleMetrics, 10);
    expect(slowest).toHaveLength(3);
  });

  it('handles empty endpoints', () => {
    const slowest = slowestEndpoints({ ...sampleMetrics, endpoints: {} }, 5);
    expect(slowest).toHaveLength(0);
  });
});

describe('totalLLMTokens', () => {
  it('sums tokens across providers', () => {
    const total = totalLLMTokens(sampleMetrics);
    expect(total.prompt).toBe(105000);
    expect(total.completion).toBe(21000);
  });

  it('groups by provider', () => {
    const total = totalLLMTokens(sampleMetrics);
    expect(total.by_provider['minimax-anthropic'].prompt).toBe(100000);
    expect(total.by_provider['openai'].completion).toBe(1000);
  });

  it('handles empty llm', () => {
    const total = totalLLMTokens({ ...sampleMetrics, llm: {} });
    expect(total.prompt).toBe(0);
    expect(total.completion).toBe(0);
    expect(total.by_provider).toEqual({});
  });
});

describe('formatUptime', () => {
  it('formats seconds', () => {
    expect(formatUptime(45)).toBe('45s');
  });

  it('formats minutes', () => {
    expect(formatUptime(125)).toBe('2.1m');
  });

  it('formats hours', () => {
    expect(formatUptime(3725)).toBe('1.0h');
  });

  it('formats days', () => {
    expect(formatUptime(86400 * 2)).toBe('2.0d');
  });
});
