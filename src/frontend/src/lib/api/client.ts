/**
 * API 客户端
 * 包装 ofetch，提供类型安全的 API 调用
 *
 * 开发期：通过 Vite proxy 转发 /api/* 到 localhost:8765
 * 生产期：直接调用同域 /api/*
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
 */
export async function call<T>(
  endpoint: string,
  options?: { method?: string; body?: unknown; query?: Record<string, string> }
): Promise<T> {
  try {
    const data = await api<unknown>(endpoint, {
      method: options?.method ?? 'POST',
      body: options?.body as Record<string, unknown> | undefined,
      query: options?.query
    });
    // 后端可能直接返回数据（无 ok 包装）
    return data as T;
  } catch (e) {
    const err = e as { data?: { error?: { message?: string } } };
    throw new Error(err.data?.error?.message ?? 'API 调用失败');
  }
}
