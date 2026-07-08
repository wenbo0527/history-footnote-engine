/**
 * /api/recap - 剧情回顾
 */
import { call } from './client';
import type { RecapResponse } from './types';

export async function getRecap(sessionId: string): Promise<RecapResponse> {
  return call<RecapResponse>('/recap', {
    body: { session_id: sessionId }
  });
}
