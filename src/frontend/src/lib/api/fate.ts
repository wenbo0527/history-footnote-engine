/**
 * /api/fate/* - 命运卡 API 客户端（v2.5）
 */
import { call } from './client';
import type { FateHandResponse, FateUseResponse } from './types';

export async function fateHand(sessionId: string): Promise<FateHandResponse> {
  return call<FateHandResponse>('/fate/hand', { body: { session_id: sessionId } });
}

export async function fateUse(sessionId: string, cardId: string): Promise<FateUseResponse> {
  return call<FateUseResponse>('/fate/use', { body: { session_id: sessionId, card_id: cardId } });
}
