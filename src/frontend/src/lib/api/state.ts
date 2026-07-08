/**
 * /api/state 调用 - GET 方式
 *
 * 🆕 v1.7.30: 调 mapper 把后端字段转成前端 GameState
 */
import { call } from './client';
import { mapBackendState } from './mapper';
import type { GameState } from './types';

export async function getState(sessionId: string): Promise<GameState> {
  const raw = await call<any>('/state', {
    method: 'GET',
    query: { session_id: sessionId }
  });
  return mapBackendState(raw);
}
