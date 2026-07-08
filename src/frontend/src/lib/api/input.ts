/**
 * /api/input 调用 - 玩家提交行动
 * 调 LLM 生成新 narrative
 *
 * 🆕 v1.7.30: 调 mapper 把后端字段转成前端 GameState
 */
import { call } from './client';
import { mapBackendState } from './mapper';
import type { GameState, VoiceOption } from './types';

export interface InputRequest {
  session_id: string;
  text?: string;
  voice_id?: string;
  voice_name?: string;
  /**
   * 🆕 v1.7.32 voice option 的语义化玩家行动（"再盘算盘算..."）。
   * 后端 /api/input 期望 body.input 字段；voice 点击时必须传 intent_text 作为 input，
   * 否则后端返回 400 "missing session_id or input"。
   */
  intent_text?: string;
}

export async function submitInput(req: InputRequest): Promise<GameState> {
  // 🆕 v1.7.32: 后端 /api/input 期望 body.input 字段。
  // voice 点击时只传 voice_id+voice_name 会导致后端 400 "missing session_id or input"；
  // 我们必须把 intent_text（语义化玩家行动）映射到 input。
  const body: Record<string, any> = {
    session_id: req.session_id,
    voice_id: req.voice_id,
    voice_name: req.voice_name,
    // intent_text 优先；没有就 fallback 到 free text；二者都没有传空串则后端会 400
    input: req.intent_text ?? req.text ?? '',
  };
  const raw = await call<any>('/input', { body });
  return mapBackendState(raw);
}

/**
 * /api/voice_options/suggest - 玩家主动求 LLM 重新生成选项（v2.3 新增 UI 入口）
 *
 * 后端（v1.7.30）已有该端点，但之前没有前端入口。
 * v2.3 改造：ActionPanel 加 "🔄 换一批" 按钮 → 调此端点
 * 注意：返回的是 voice_options[]（不是 GameState），需要前端手动合并
 */
export interface VoiceSuggestRequest {
  session_id: string;
}

export interface VoiceSuggestResponse {
  voice_options: VoiceOption[];
  from_suggestion?: boolean;
  fallback_used?: boolean;
  round_number?: number;
}

export async function suggestVoices(req: VoiceSuggestRequest): Promise<VoiceOption[]> {
  const res = await call<any>('/voice_options/suggest', { body: req });
  // 后端返 { voice_options: [...], from_suggestion: true, ... }
  if (Array.isArray(res)) return res;
  if (res?.voice_options && Array.isArray(res.voice_options)) return res.voice_options;
  if (res?.voices) return res.voices;
  return [];
}
