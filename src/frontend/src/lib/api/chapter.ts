/**
 * 🆕 v2.8.0 章节制 API 客户端
 *
 * 3 个端点：
 * - GET  /api/chapter/state       — 章节状态（进度条用）
 * - GET  /api/chapter/blueprint   — 当前章节蓝图（节点 scene + options）
 * - POST /api/chapter/record_choice — 记录玩家选项（写入 recent_path_choices）
 * - GET  /api/chapter/history     — 章节历史
 */
import { api } from './client';

export interface ChapterStateResponse {
  active: boolean;
  current_chapter: number;
  current_node: number;
  node_count: number;
  chapter_start_round: number;
  round_number: number;
  rounds_elapsed: number;
  last_closure_status: string;
  progress_pct: number;
  player_build: string;
  main_path_focus: string;
  active_plate: string;
}

export interface ChapterBlueprintResponse {
  active: boolean;
  chapter_id?: number;
  chapter_title?: string;
  chapter_subtitle?: string;
  transition_hint?: string;
  current_node?: number;
  nodes: Array<{
    index: number;
    role: string;
    scene: string;
    npc_ids: string[];
    option_directions: Array<{ text: string; path?: string; path_hint?: string }>;
    knowledge_ids?: string[];
    completion_condition?: string;
  }>;
  meta?: Record<string, any>;
}

export interface ChapterHistoryResponse {
  count: number;
  history: Array<{
    chapter: number;
    summary: string;
    core_event?: string;
    key_choice?: string;
    build_summary?: string;
    path_summary?: string;
    rounds_in_chapter?: number;
    ended_at_round?: number;
    transition?: string;
    closure_status?: string;
  }>;
}

export interface PlateDefinition {
  id: string;
  name: string;
  type: 'core' | 'peripheral' | 'corridor' | string;
  neighbors: string[];
  base_tension: number;
  description: string;
}

export interface PlateCorridor {
  id: string;
  from_plate: string;
  to_plate: string;
  description: string;
}

export interface PlateMapResponse {
  active: boolean;
  plate_count: number;
  definitions: PlateDefinition[];
  corridors: PlateCorridor[];
  /** 各板块当前张力 0-1 */
  tensions: Record<string, number>;
  /** 各板块当前状态 stable/tense/shifting/collapsed */
  statuses: Record<string, string>;
  /** 当前激活的 shifting 板块 */
  active_plate: string;
}

/**
 * GET 章节状态（进度条 + 节点定位）
 * @throws ApiError if session 不存在
 */
export async function getChapterState(sessionId: string): Promise<ChapterStateResponse> {
  return api<ChapterStateResponse>('/chapter/state', { params: { session_id: sessionId } });
}

/**
 * GET 章节蓝图（节点 scene + options）
 */
export async function getChapterBlueprint(sessionId: string): Promise<ChapterBlueprintResponse> {
  return api<ChapterBlueprintResponse>('/chapter/blueprint', { params: { session_id: sessionId } });
}

/**
 * POST 记录玩家选项（写入 recent_path_choices）
 */
export async function recordChapterChoice(
  sessionId: string,
  path: string
): Promise<{ recorded: boolean; path: string; recent_path_choices: string[] }> {
  return api('/chapter/record_choice', {
    method: 'POST',
    body: { session_id: sessionId, path },
  });
}

/**
 * GET 章节历史（已结算章节摘要）
 */
export async function getChapterHistory(sessionId: string): Promise<ChapterHistoryResponse> {
  return api<ChapterHistoryResponse>('/chapter/history', { params: { session_id: sessionId } });
}

/**
 * 🆕 v2.8.x W28: GET 板块格局地图
 * 返回所有板块定义 + 走廊 + 实时张力 + 状态
 */
export async function getPlateMap(sessionId: string): Promise<PlateMapResponse> {
  return api<PlateMapResponse>('/chapter/plate', { params: { session_id: sessionId } });
}
