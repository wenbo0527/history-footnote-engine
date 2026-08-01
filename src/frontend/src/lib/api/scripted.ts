/**
 * 🆕 v2.10.22 — 故事模式 API
 *
 * 跟主游戏融合后的统一入口
 */
import { call } from './client';
import { game, gameActions } from '$lib/stores';
import { get } from 'svelte/store';

export interface ScriptedStartResponse {
  narrative: string;
  voice_options: any[];
  scripted_mode: boolean;
  scripted_chapter_id: number;
  scripted_node_id: string;
  llm_calls: number;
}

/**
 * 启动剧本模式 (从主游戏切换)
 * @param sessionId 主游戏的 session_id
 * @param chapterId 1=家贫, 2=织染, 3=丝绢案
 */
export async function startScriptedMode(sessionId: string, chapterId: number = 1): Promise<ScriptedStartResponse> {
  const data = await call<ScriptedStartResponse>('/api/scripted/start', {
    session_id: sessionId,
    chapter_id: chapterId,
  });

  // 更新本地 game state
  const cur = get(game);
  if (cur) {
    const updated = {
      ...cur,
      scripted_mode: data.scripted_mode,
      scripted_chapter_id: data.scripted_chapter_id,
      scripted_node_id: data.scripted_node_id,
      scripted_flags: [],
      scripted_visits: [data.scripted_node_id],
      scripted_chapter_complete: false,
      narrative: cur.narrative ? {
        ...cur.narrative,
        content: data.narrative,
      } : { round: 0, content: data.narrative, type: 'opening' as const, created_at: new Date().toISOString() },
      last_voice_options: data.voice_options,
    };
    gameActions.set(updated);
  }

  return data;
}

/**
 * 退出剧本模式
 */
export async function exitScriptedMode(sessionId: string): Promise<void> {
  await call('/api/scripted/exit', { session_id: sessionId });
  const cur = get(game);
  if (cur) {
    gameActions.set({
      ...cur,
      scripted_mode: false,
      scripted_chapter_complete: false,
    });
  }
}