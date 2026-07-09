/**
 * /api/fate/* - 命运卡 API 客户端（v2.6 主动使用）
 */
import { call } from './client';
import type {
  FateHandResponse,
  FateUseResponse,
  FateAvailableResponse,
  FateEmergencyResponse
} from './types';

export async function fateHand(sessionId: string): Promise<FateHandResponse> {
  return call<FateHandResponse>('/fate/hand', { body: { session_id: sessionId } });
}

export async function fateUse(
  sessionId: string,
  cardId: string,
  context: 'immediate' | 'round_start' | 'emergency' = 'immediate',
): Promise<FateUseResponse> {
  return call<FateUseResponse>('/fate/use', {
    body: { session_id: sessionId, card_id: cardId, context },
  });
}

export async function fateAvailable(
  sessionId: string,
  context: 'immediate' | 'round_start' | 'emergency' = 'immediate',
): Promise<FateAvailableResponse> {
  return call<FateAvailableResponse>('/fate/available', {
    body: { session_id: sessionId, context },
  });
}

export async function fateEmergencyCheck(sessionId: string): Promise<FateEmergencyResponse> {
  return call<FateEmergencyResponse>('/fate/emergency_check', {
    body: { session_id: sessionId },
  });
}
