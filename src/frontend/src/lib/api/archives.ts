/**
 * /api/archives - 存档管理
 *
 * 🆕 v1.7.30: 对齐后端
 * - GET /api/archives?account=xxx → 列表
 * - DELETE /api/archives?session_id=xxx → 删除
 * - POST /api/archives/clear → 清空
 *
 * 加载存档用 loadArchivedSession(archiveId) 调 /api/state
 */
import { call } from './client';
import type { Archive } from './types';

export async function listArchives(account = 'default'): Promise<Archive[]> {
  const res = await call<{ archives: Archive[] }>('/archives', {
    method: 'GET',
    query: { account }
  });
  return res.archives ?? [];
}

export async function deleteArchive(sessionId: string): Promise<{ deleted: boolean }> {
  return call<{ deleted: boolean }>('/archives', {
    method: 'DELETE',
    body: { session_id: sessionId }
  });
}

export async function clearArchives(): Promise<{ cleared: number }> {
  return call<{ cleared: number }>('/archives/clear', { body: {} });
}
