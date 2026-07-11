/**
 * 🆕 v2.10.x W51: 多会话/存档 API 客户端
 *
 * 后端 /api/archives 返回存档列表（含 session_id / era_id / current_round / summary）
 */
import { api } from './client';

export interface ArchiveSession {
  session_id: string;
  era_id: string;
  current_round: number;
  current_date: string;
  summary: string;
  created_at: string;
  updated_at?: string;
  archived?: boolean;
  [key: string]: any;
}

export interface ArchivesResponse {
  count: number;
  sessions: ArchiveSession[];
}

/**
 * GET /api/archives — 获取存档列表
 * @param account 账户 ID（可选）
 * @param includeArchived 是否含冷存档（默认 false）
 */
export async function listArchives(
  account?: string,
  includeArchived: boolean = false
): Promise<ArchivesResponse> {
  return api<ArchivesResponse>('/archives', {
    params: {
      ...(account ? { account } : {}),
      ...(includeArchived ? { include_archived: 1 } : {}),
    },
  });
}

/**
 * 派生：按 updated_at 倒序排序（最近玩的在前）
 */
export function sortByRecent(sessions: ArchiveSession[]): ArchiveSession[] {
  return [...sessions].sort((a, b) => {
    const aTime = a.updated_at || a.created_at || '';
    const bTime = b.updated_at || b.created_at || '';
    return bTime.localeCompare(aTime);
  });
}

/**
 * 派生：按 era 分组
 */
export function groupByEra(
  sessions: ArchiveSession[]
): Record<string, ArchiveSession[]> {
  const out: Record<string, ArchiveSession[]> = {};
  for (const s of sessions) {
    const era = s.era_id || 'unknown';
    if (!out[era]) out[era] = [];
    out[era].push(s);
  }
  return out;
}
