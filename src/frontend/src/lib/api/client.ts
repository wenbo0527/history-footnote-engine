/**
 * API 客户端
 * 包装 ofetch，提供类型安全的 API 调用
 *
 * 开发期：通过 Vite proxy 转发 /api/* 到 localhost:8765
 * 生产期：直接调用同域 /api/*
 *
 * 🆕 v2.7+ 错误友好化：
 * - 默认 timeout 90s（适配 DM agent 多步 LLM 冷启动 30-60s）
 * - 错误信息分类：401/429/500/超时/网络，给玩家可读提示
 */
import { ofetch, type $Fetch } from 'ofetch';
import type { ApiResponse } from './types';

export const api: $Fetch = ofetch.create({
  baseURL: '/api',
  // 自动带 cookie
  credentials: 'include',
  // 错误处理
  onResponseError({ response }) {
    if (response.status === 401) {
      // 未登录：跳首页
      if (typeof window !== 'undefined' && window.location.pathname !== '/') {
        window.location.href = '/';
      }
    }
  }
});

/**
 * 统一响应处理：把后端响应标准化为 ApiResponse
 *
 * 🆕 v2.7+ 优化：
 * - 显式 timeout（默认 90s，input/suggest 流程可传 120s）
 * - 错误信息分类：把 HTTP status / 异常类型映射成中文友好提示
 *   避免出现 "API 调用失败" 这种干巴文案
 */
export interface CallOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string>;
  /** 超时 ms，默认 90s；input 这类长流程可设 120-180s */
  timeout?: number;
}

export async function call<T>(
  endpoint: string,
  options?: CallOptions
): Promise<T> {
  const timeout = options?.timeout ?? 90000;
  try {
    const data = await api<unknown>(endpoint, {
      method: options?.method ?? 'POST',
      body: options?.body as Record<string, unknown> | undefined,
      query: options?.query,
      timeout,
    });
    // 后端可能直接返回数据（无 ok 包装）
    return data as T;
  } catch (e) {
    throw normalizeError(e, endpoint, timeout);
  }
}

/**
 * 🆕 v2.7+ 错误标准化
 * 把 ofetch / fetch / 各种异常映射成有 status + friendly message 的 Error
 */
function normalizeError(e: unknown, endpoint: string, timeoutMs: number): Error {
  const err = e as {
    name?: string;
    message?: string;
    status?: number;
    statusCode?: number;
    response?: { status?: number; _data?: any };
    data?: { error?: string; message?: string; suggestion?: string };
  };

  const status = err.status ?? err.statusCode ?? err.response?.status;
  const backendMsg = err.data?.message || err.data?.error;
  const backendSuggestion = err.data?.suggestion;

  // 优先用后端的 suggestion（已有友好文案）
  if (backendSuggestion) {
    const e2 = new Error(backendSuggestion) as Error & {
      status?: number;
      friendly?: boolean;
      data?: { error?: string; message?: string; suggestion?: string; retryable?: boolean };
    };
    e2.status = status;
    e2.friendly = true;
    // 🆕 v2.10.1 W71: 把后端 data 复制到 Error，让前端能 err.data?.error 判断重试性
    e2.data = err.data;
    return e2;
  }

  // 客户端主动 abort（用户关页面 / 切路由）
  if (err.name === 'AbortError' || /abort/i.test(err.message || '')) {
    return new Error('已取消请求');
  }

  // 分类映射
  let friendly: string;
  if (status === 401) {
    friendly = '请先登录';
  } else if (status === 403) {
    friendly = '没有权限';
  } else if (status === 404) {
    friendly = '资源不存在';
  } else if (status === 408 || err.name === 'TimeoutError' || /timeout/i.test(err.message || '')) {
    friendly = `⏰ 请求超时（${Math.round(timeoutMs / 1000)}s），可能是 LLM 推理较慢，请稍后重试`;
  } else if (status === 429) {
    friendly = '🚦 请求限流，请稍后再试';
  } else if (status === 503) {
    friendly = '🔧 服务暂不可用，请稍后';
  } else if (status && status >= 500) {
    friendly = backendMsg || '⚙️ 服务异常，请稍后重试';
  } else if (status && status >= 400) {
    friendly = backendMsg || '❌ 请求错误，请检查输入';
  } else if (!status && err.message?.includes('fetch')) {
    friendly = '📡 网络异常，请检查连接';
  } else {
    friendly = backendMsg || err.message || '请求失败';
  }

  const e2 = new Error(friendly) as Error & { status?: number; endpoint?: string; friendly?: boolean };
  e2.status = status;
  e2.endpoint = endpoint;
  e2.friendly = true;
  return e2;
}
