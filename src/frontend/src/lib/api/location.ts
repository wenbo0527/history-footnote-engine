/**
 * /api/location/* - 地点系统 API 客户端（v2.4 文字地图）
 */
import { call } from './client';
import type { LocationListResponse, LocationMoveResponse } from './types';

export async function locationList(sessionId: string): Promise<LocationListResponse> {
  return call<LocationListResponse>('/location/list', { body: { session_id: sessionId } });
}

export async function locationMove(sessionId: string, target: string): Promise<LocationMoveResponse> {
  return call<LocationMoveResponse>('/location/move', { body: { session_id: sessionId, target } });
}

export async function locationDetail(sessionId: string, locationId: string) {
  return call('/location/detail', { body: { session_id: sessionId, location_id: locationId } });
}
