/**
 * /api/start 调用
 * 调 Python 后端创建新游戏
 *
 * 🆕 v1.7.30:
 * - 成功后把 session_id 存到 localStorage
 * - 调 mapper 把后端字段转成前端 GameState
 * - 接 account_id（v1.7.30 账户隔离）
 */
import { call } from './client';
import { mapBackendState } from './mapper';
import { getCurrentAccountId } from './account';
import type { GameState, Character, Identity, Gender } from './types';

const SESSION_KEY = 'hfe_session_id';

export interface StartRequest {
  era_id: string;
  identity: Identity;
  gender: Gender;
  character: Character;
  /** 🆕 v2.10.33 D2.1: 是否剧本模式（写到后端 state.scripted_intent） */
  scripted?: boolean;
  /** 🆕 v2.10.33 D2.1: 剧本起始章节 */
  scripted_chapter_id?: number;
}

export async function startGame(req: StartRequest): Promise<GameState> {
  // 🆕 v1.7.30: 把 account_id 加到 body
  const accountId = getCurrentAccountId() ?? '';
  const body: Record<string, any> = { ...req, account_id: accountId };
  // 🆕 v2.10.33 D2.1: scripted 字段透传到后端
  if (req.scripted) body.scripted = true;
  if (req.scripted_chapter_id) body.scripted_chapter_id = req.scripted_chapter_id;
  const raw = await call<any>('/start', { body });
  const data = mapBackendState(raw);

  // 存 session_id 供后续 API 使用
  if (typeof window !== 'undefined' && data?.session_id) {
    localStorage.setItem(SESSION_KEY, data.session_id);
  }

  return data;
}

/** 读取本地 session_id */
export function getSessionId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(SESSION_KEY);
}

/** 清除 session_id（登出/重开） */
export function clearSession(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(SESSION_KEY);
}
