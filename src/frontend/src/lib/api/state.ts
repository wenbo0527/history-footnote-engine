/**
 * /api/state 调用 - GET 方式
 *
 * 🆕 v1.7.30: 调 mapper 把后端字段转成前端 GameState
 * 🆕 v2.10.1 W77: 加 confirmCityChange / rejectCityChange
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

/**
 * 🆕 W77: 玩家确认城市变更（应用 pending_city_change）
 */
export async function confirmCityChange(sessionId: string): Promise<GameState> {
  const raw = await call<any>('/confirm_city_change', {
    method: 'POST',
    body: { session_id: sessionId }
  });
  return mapBackendState(raw);
}

/**
 * 🆕 W77: 玩家拒绝城市变更（保持原 city）
 */
export async function rejectCityChange(sessionId: string): Promise<GameState> {
  const raw = await call<any>('/reject_city_change', {
    method: 'POST',
    body: { session_id: sessionId }
  });
  return mapBackendState(raw);
}
