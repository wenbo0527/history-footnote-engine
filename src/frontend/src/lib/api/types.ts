/**
 * API 类型定义
 * 跟 Python 后端 /api/* 响应结构对齐
 */

// ============ Era 朝代 ============
export interface Era {
  id: string;
  name: string;
  year_start: number;
  year_end: number;
  description: string;
  icon: string;
}

// ============ Character 角色 ============
export type Identity = 'weaving_male' | 'weaving_female' | 'merchant_male' | 'merchant_female' | 'farmer_male' | 'farmer_female' | 'scholar_male';
export type Gender = 'male' | 'female';

export interface Character {
  name: string;
  age: number;
  occupation: string;
  hometown: string;
  // 🆕 v2.3: 可选扩展字段（人物档案用）
  identity?: string;     // 织工/织女/牙商/佃户（更细）
  portrait?: string;     // 头像 URL
}

export interface FamilyMember {
  relation: string;
  name: string;
  age: number;
  status?: string;
}

export interface Skill {
  name: string;
  level: number;
}

// ============ Timeline 大事记 ============
export interface TimelineEvent {
  year: number;
  event: string;
  highlight?: boolean;
}

// ============ Sidebar 财务/任务/还债日 ============
export interface FinancialStatus {
  cash: number;
  rice: number;
  debt: number;
  monthly_burn: number;
}

export interface Task {
  title: string;
  urgency: 'high' | 'medium' | 'low';
}

export interface Deadline {
  name: string;
  days_estimate?: number;
  amount?: string;
}

export interface SidebarData {
  active_tasks: Task[];
  upcoming_deadlines: Deadline[];
  financial_status: FinancialStatus;
}

// ============ Voice 声音选项 ============
export type ValueDimension =
  | 'tradition_vs_change'      // 守旧 vs 求变
  | 'duty_vs_freedom'          // 责任 vs 自由
  | 'pragmatism_vs_idealism'   // 务实 vs 理想
  | 'independence_vs_network'  // 独立 vs 依附
  | 'acceptance_vs_resistance' // 顺从 vs 抗争
  | null;                      // 无关联维度

export const VALUE_DIMENSION_META: Record<Exclude<ValueDimension, null>, {
  label: string;        // 短标签（"顺从/抗争"）
  icon: string;         // emoji
  color: string;        // 主题色
  shortDesc: string;    // 一句话说明
}> = {
  tradition_vs_change:     { label: '守旧/求变', icon: '🏛', color: '#8b6f47', shortDesc: '守祖宗之法 or 顺应时势' },
  duty_vs_freedom:         { label: '责任/自由', icon: '⚖', color: '#5a7a8b', shortDesc: '为家人活 or 为自己活' },
  pragmatism_vs_idealism:  { label: '务实/理想', icon: '💎', color: '#7a5a8b', shortDesc: '看眼前 or 守本心' },
  independence_vs_network: { label: '独立/依附', icon: '🤝', color: '#6b8b5a', shortDesc: '独自扛 or 抱团取暖' },
  acceptance_vs_resistance: { label: '顺从/抗争', icon: '🔥', color: '#a52828', shortDesc: '认命 or 反抗' }
};

export interface VoiceOption {
  voice_id: string;
  voice_name: string;
  intent_text: string;
  is_freetext?: boolean;
  // 🆕 v2.1: DE 思想内阁 —— 选项关联的价值维度
  // 兼容：后端暂未返回时降级为 null
  value_dimension?: ValueDimension;
  value_level?: number;          // 1-5，影响"声音的响亮度"
  inner_voice?: string;          // 选这个时 DM 内心独白（玩家会看到）
  // v1.9.5 移除 option_preview（破坏沉浸感）
  preview?: {
    intent?: string;
    probability?: number;
  };
  // 🆕 v2.4: 移动选项（来自 location_service.get_move_options）
  is_move?: boolean;
  target_location?: string;
  ap_cost?: number;
  time_mode?: 'abstract_time' | 'now_time' | 'slow_time' | 'sharp_cut';
}

// ============ v2.4 Location 地点 ============
export type LocationTier = 'L1' | 'L2' | 'L3';
export type LocationType = 'family' | 'public' | 'work' | 'neighbor' | 'social' | 'authority' | 'service' | 'education';

export interface LocationInfo {
  id: string;
  name: string;
  tier: LocationTier;
  type?: LocationType;
  description: string;
  tone?: string;
  atmosphere_sound?: string;
  npcs_default?: string[];
  neighbors?: string[] | { id: string; name: string }[];
  events?: Array<{
    id: string;
    title: string;
    ap_cost: number;
    time_mode: string;
    trigger?: string;
  }>;
}

export interface LocationListResponse {
  city_name: string;
  city_intro: string;
  current_location: LocationInfo;
  visited: LocationInfo[];
  heard: LocationInfo[];   // 听过没去过
  unseen: LocationInfo[];  // 玩家完全不知道
  newly_heard: string[];  // 本次请求新解锁的
}

export interface LocationMoveResponse {
  success: boolean;
  from_location: string;
  to_location: string;
  to_location_name: string;
  ap_cost: number;
  time_mode: string;
  new_ap: number;
  new_voice_options: VoiceOption[];  // 新地点的"脑海中的声音"（含移动）
  narrative: string;                 // 简单移动叙事
  newly_heard: string[];
  location: LocationInfo;            // 新地点的完整信息
  // 🆕 v2.4.1: 路遇事件 + 该地 NPC
  encounter?: { npc: string; event: string; probability: number } | null;
  npcs_at?: string[];                // 该地所有 NPC
}

// ============ Narrative 叙事 ============
export interface Narrative {
  round: number;
  content: string;        // markdown 格式
  raw_text?: string;
  type?: 'opening' | 'story' | 'response' | 'system';
  created_at?: string;
}

// ============ Game State 游戏状态 ============
export interface GameState {
  session_id: string;
  account_username: string;
  character: Character;
  family: FamilyMember[];
  skills: Skill[];
  city: string;
  year_current: number;
  year_max: number;
  round_current: number;
  cash: number;
  rice: number;
  looms: number;
  debt: number;
  monthly_burn: number;
  reputation: number;
  // 🆕 行动点（每月 3-4 个）—— 让"过日子"可感知
  // 后端 action_points_current / action_points_max 已在 mapper 透传
  action_points_current: number;
  action_points_max: number;
  timeline: TimelineEvent[];
  sidebar: SidebarData;
  narrative: Narrative | null;
  narrative_history: Narrative[];
  last_voice_options: VoiceOption[];
  // 中文：身份 / 性别（由 wizard 决定）
  identity: Identity;
  gender: Gender;
  era_id: string;
  // 🆕 v1.7.32: 后端 input.py:208 写入的软提示（low_relevance 等）
  // mapper.ts 必须透传，否则前端 toast.warning 永远不会显示 server-side 提示
  soft_warning?: {
    type: string;
    message: string;
    suggestion?: string;
  };
}

// ============ Archive 存档 ============
// 🆕 v1.7.30: 字段对齐后端（后端返回 current_round / current_date / summary / last_saved_at）
export interface Archive {
  // 后端实际字段
  session_id: string;
  era_id: string;
  current_round: number;
  current_date: string;
  summary: string;
  created_at: string;
  last_saved_at: string;
  selected_identity: string;
  player_gender: string;
  // 旧字段保留（兼容）
  archive_id?: string;
  account_username?: string;
  character_name?: string;
  character_occupation?: string;
  year?: number;
  round?: number;
  cash?: number;
  debt?: number;
  updated_at?: string;
  preview?: string;
}

// ============ API Response ============
export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

// ============ Wiki 角色关系 ============
// 🆕 v1.7.30: 字段对齐后端（wiki 是 dict）
export interface WikiCharacter {
  name: string;
  relation: string;
  age?: number;
  description: string;
  portrait?: string;
  // 🆕 v2.3: 补充字段（用于排序和卡片展示）
  first_met_round?: number;   // 第一次相遇的回合数（0=开局）
  affinity?: number;          // 与玩家的关系 -100~+100（-100=仇人，+100=恩人）
  status?: 'alive' | 'dead' | 'missing' | 'unknown';  // 生死状态
}

// 🆕 v2.3: 主角（玩家）卡片数据
export interface PlayerCharacter {
  name: string;
  identity: string;     // 织工/织女/牙商/佃户
  age?: number;
  portrait?: string;
}

export interface WikiResponse {
  markdown: string;        // 渲染后的 markdown
  characters: WikiCharacter[];
  updated_at: string;
  // 兼容后端 {session_id, wiki} 格式
  raw_wiki?: Record<string, any>;
}

// ============ Dilemma 困境 ============
export interface DilemmaResponse {
  situation: string;        // 简洁描述当前困境
  choices: VoiceOption[];
  markdown: string;
}

// ============ Recap 剧情回顾 ============
// 🆕 v1.7.30: 字段对齐后端（后端返回 recent + archive + total_narratives）
export interface RecapNarrativeItem {
  round: number;
  narrative: string;
  summary?: string;
}

export interface RecapResponse {
  round_number?: number;
  current_date?: string;
  total_narratives: number;
  recent: RecapNarrativeItem[];
  archive: RecapNarrativeItem[];
  // 旧字段保留（兼容）
  markdown?: string;
  rounds_covered?: number;
  generated_at?: string;
}

// ============ Glossary 词条 ============
// 🆕 v1.7.30: 字段对齐后端（query, terms[]）
export interface GlossaryTerm {
  key: string;
  category: string;
  definition: string;
  related?: string[];
}

export interface GlossaryResponse {
  query: string;
  count: number;
  terms: GlossaryTerm[];
  total_in_dict: number;
  // 旧字段保留
  term?: string;
  definition?: string;
  related?: string[];
}
