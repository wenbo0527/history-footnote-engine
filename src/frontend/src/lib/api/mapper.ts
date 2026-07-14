/**
 * 后端 → 前端 字段映射
 *
 * 后端（Python web_server.format_state）返回的字段名跟前端
 * lib/api/types.ts 期望的不完全一致。这个文件做转换。
 *
 * 🆕 v1.7.30 联调发现
 */
import type { GameState, FamilyMember, Skill, Character, SidebarData, TimelineEvent, Narrative, FinancialStatus, Task, Deadline, Identity, Gender } from './types';

// v2.10.3 类型守卫：后端返回 string，需 narrow 到有限 union
const VALID_IDENTITIES: readonly Identity[] = [
  'weaving_male', 'weaving_female', 'merchant_male', 'merchant_female',
  'farmer_male', 'farmer_female', 'scholar_male',
];
const VALID_GENDERS: readonly Gender[] = ['male', 'female'];

function narrowIdentity(s: string | undefined): Identity {
  return s && (VALID_IDENTITIES as readonly string[]).includes(s) ? s as Identity : 'weaving_male';
}
function narrowGender(s: string | undefined): Gender {
  return s && (VALID_GENDERS as readonly string[]).includes(s) ? s as Gender : 'male';
}

// 后端 family_members 字段
interface BackendFamilyMember {
  id: string;
  name: string;
  relation: string;       // wife / son / daughter / ...
  age: number;
  alive: boolean;
  notes?: string;
  status?: string;
  location?: string;
}

interface BackendTask {
  title: string;
  description?: string;
  urgency: string;
  status?: string;
  due_date?: string;
  reward?: any;
}

interface BackendDeadline {
  name: string;
  date?: string;
  days_estimate?: number;
  amount?: string;
  urgency?: string;
}

interface BackendFinancialStatus {
  cash: number;
  rice: number;
  debt: number;
  monthly_burn: number;
  [key: string]: any;
}

interface BackendSidebar {
  active_tasks: BackendTask[];
  upcoming_deadlines: BackendDeadline[];
  financial_status: BackendFinancialStatus;
}

interface BackendRecentNarrative {
  round: number;
  summary: string;
  narrative: string;
  type?: string;
  created_at?: string;
}

interface BackendState {
  // 基础
  session_id: string;
  era_id: string;
  era_name: string;
  round_number: number;
  current_date: string;      // "1587年1月"
  action_points_current: number;
  action_points_max: number;

  // 身份
  selected_identity: string;
  player_gender: string;
  current_city: string;

  // 列表
  unlocked_insights: any[];
  triggered_events: string[];
  variables: Record<string, any>;
  value_shifts: Record<string, number>;

  // 叙事
  recent_narratives: BackendRecentNarrative[];

  // 角色
  custom_character: Character;
  character?: Character;
  family_members: BackendFamilyMember[];
  genealogy: any[];

  // 财务
  cash: number;
  rice: number;
  debt: number;
  monthly_burn: number;
  financial_log: any[];

  // 声音/时间线
  last_voice_options: any[];

  // 侧栏
  sidebar_data: BackendSidebar;

  // 其他
  city_properties: any;
  inventory: any;
  discoveries: any;
  completed_tasks_count: number;
  skills?: Skill[];
  timeline?: any[];
  // 🆕 v2.5: 命运卡 + seed + 关系 + buff（让 CharCard 直接显示）
  seed?: number;
  fate_hand?: any[];
  fate_used?: string[];
  fate_event_flags?: string[];
  npc_relations?: Record<string, number>;
  active_buffs?: any[];
  // 🆕 v2.10.3: 补充字段声明（消除 .svelte 里 ($game as any) 兜底）
  soft_warning?: { type: string; message: string; suggestion?: string };
  pending_city_change?: {
    from_city: string;
    to_city: string;
    narrative?: string;
  };
  current_chapter?: number;
  total_chapters?: number;
}

/**
 * 把后端状态转成前端 GameState
 */
export function mapBackendState(b: BackendState): GameState {
  // 1. character
  const character: Character = b.custom_character ?? b.character ?? {
    name: '???',
    age: 30,
    occupation: '???',
    hometown: '???'
  };

  // 2. family_members → family
  const family: FamilyMember[] = (b.family_members ?? []).map(fm => ({
    name: fm.name,
    relation: translateRelation(fm.relation),
    age: fm.age,
    status: fm.alive ? '在世' : (fm.status ?? '已故')
  }));

  // 3. recent_narratives → narrative（最新一条真 narrative）
  // 🆕 v1.7.32 Bug 修复：取末项而不是首项（后端 [-3:] 最新在尾）。
  // 🆕 v1.7.32 又一次修复：narrative_history 数组里混入了面板型 entry（type=monthly_settlement），
  // 比如游戏循环的最后会追加一个「📅 **月末结算** 📉 -0.42 两 ...」短文。
  // 取末项会拿到这条面板而不是真实叙事。需过滤掉面板型 entry，从后往前找第一个真 narrative。
  const _recentList = b.recent_narratives ?? [];
  const isPanelEntry = (n: any) => n && (n.type === 'monthly_settlement' || n.type === 'event_log');
  let latest: any = undefined;
  for (let i = _recentList.length - 1; i >= 0; i--) {
    if (!isPanelEntry(_recentList[i])) { latest = _recentList[i]; break; }
  }
  // v2.10.3 类型安全：Narrative.type 是有限 union，运行时做 narrow
  const VALID_NARRATIVE_TYPES = ['opening', 'story', 'response', 'system'] as const;
  const narrativeType = (latest && VALID_NARRATIVE_TYPES.includes(latest.type as any))
    ? latest.type as 'opening' | 'story' | 'response' | 'system'
    : 'opening';
  const narrative: Narrative | null = latest ? {
    round: latest.round,
    content: latest.narrative,
    type: narrativeType,
    created_at: latest.created_at ?? new Date().toISOString()
  } : null;

  // 4. timeline
  const timeline: TimelineEvent[] = (b.timeline ?? buildTimelineFromEvents(b)).map(t => ({
    year: typeof t.year === 'number' ? t.year : parseYearFromDate(t.year ?? t.date ?? ''),
    event: t.event ?? t.summary ?? t.description ?? '',
    highlight: t.highlight ?? t.is_highlight ?? false
  }));

  // 5. sidebar
  const VALID_URGENCY = ['low', 'medium', 'high'] as const;
  const sidebar: SidebarData = {
    active_tasks: (b.sidebar_data?.active_tasks ?? []).map((t: BackendTask): Task => ({
      title: t.title,
      urgency: (VALID_URGENCY.includes(t.urgency as any)
        ? t.urgency
        : 'low') as 'low' | 'medium' | 'high',
    })),
    upcoming_deadlines: (b.sidebar_data?.upcoming_deadlines ?? []).map((d: BackendDeadline): Deadline => ({
      name: d.name,
      days_estimate: d.days_estimate,
      amount: d.amount
    })),
    financial_status: {
      cash: b.sidebar_data?.financial_status?.cash ?? b.cash,
      rice: b.sidebar_data?.financial_status?.rice ?? b.rice,
      debt: b.sidebar_data?.financial_status?.debt ?? b.debt,
      monthly_burn: b.sidebar_data?.financial_status?.monthly_burn ?? b.monthly_burn
    } as FinancialStatus
  };

  // 6. 年份从 current_date 提取
  const yearCurrent = parseYearFromDate(b.current_date);
  const yearMax = yearCurrent >= 1601 ? yearCurrent : 1601;  // era 默认到 1601

  // 7. 声音
  // 🆕 v2.10.7: 兜底 voice_id 防止 duplicate key
  // 后端 LLM 偶尔返的 dict 缺 voice_id → mapper 不处理会让 Svelte 报 each_key_duplicate
  const last_voice_options = (b.last_voice_options ?? []).map((v: any, i: number) => ({
    voice_id: v.voice_id || v.id || `voice_${i}`,
    voice_name: v.voice_name || v.name || '未命名选项',
    intent_text: v.intent_text || v.text || '',
  }));

  // 8. account_username（后端没返，用 session_id 前缀）
  const account_username = b.session_id?.split('_')[0] ?? 'demo';

  return {
    session_id: b.session_id,
    account_username,
    character,
    family,
    skills: b.skills ?? [],
    city: translateCity(b.current_city),
    year_current: yearCurrent,
    year_max: yearMax,
    round_current: b.round_number,
    cash: b.cash,
    rice: b.rice,
    looms: b.inventory?.looms ?? 1,
    debt: b.debt,
    monthly_burn: b.monthly_burn,
    reputation: b.variables?.reputation ?? 0,
    // 🆕 行动点（v2.0 设计补充）—— 让"过日子"循环可感知
    action_points_current: b.action_points_current ?? 3,
    action_points_max: b.action_points_max ?? 3,
    identity: narrowIdentity(b.selected_identity),
    gender: narrowGender(b.player_gender),
    era_id: b.era_id,
    timeline,
    sidebar,
    narrative,
    // 🆕 v2.5: 透传命运卡 + seed + 关系 + buff（让 CharCard 直接显示）
    fate_hand: b.fate_hand ?? [],
    fate_used: b.fate_used ?? [],
    fate_event_flags: b.fate_event_flags ?? [],
    npc_relations: b.npc_relations ?? {},
    active_buffs: b.active_buffs ?? [],
    seed: b.seed ?? 0,
    narrative_history: (b.recent_narratives ?? []).slice(0, -1).map(n => ({
      round: n.round,
      content: n.narrative,
      // v2.10.3 类型安全：narrow 到 Narrative.type 有限 union
      type: (VALID_NARRATIVE_TYPES.includes(n.type as any)
        ? n.type as 'opening' | 'story' | 'response' | 'system'
        : 'response') as 'opening' | 'story' | 'response' | 'system',
      created_at: n.created_at ?? new Date().toISOString()
    })),
    last_voice_options,
    // 🆕 v1.7.32 透传 soft_warning：让前端 GameView 能 toast.warning(message)
    // 否则 server-side 给玩家的软提示（low_relevance/meta_query 等）会静默丢失
    soft_warning: b.soft_warning ?? undefined,
    // 🆕 v2.10.3 补全字段：消除 Svelte 里 ($game as any) 兜底
    // 后端 format_state.py 已有这些字段，mapper 之前没透传
    round_number: b.round_number,
    current_date: b.current_date,
    value_shifts: b.value_shifts ?? {},
    pending_city_change: b.pending_city_change ?? undefined,
    // 🆕 v2.10.3 章节制字段（format_state chapter 块）
    current_chapter: b.current_chapter ?? 0,
    total_chapters: b.total_chapters ?? 10,
    // 🆕 v2.10.3 recent_narratives 完整列表（之前只取最新）
    recent_narratives: b.recent_narratives ?? [],
    // 🆕 v2.10.3 性格 / 自定义字段
    selected_identity: b.selected_identity,
    player_gender: b.player_gender,
  } as GameState;
}


// 关系翻译
function translateRelation(r: string): string {
  const map: Record<string, string> = {
    wife: '妻', husband: '夫',
    son: '子', daughter: '女',
    father: '父', mother: '母',
    brother: '兄', sister: '姐',
    grandfather: '祖父', grandmother: '祖母',
  };
  return map[r] ?? r;
}

// 城市翻译
function translateCity(c: string): string {
  const map: Record<string, string> = {
    shengze: '盛泽镇',
    fengqiao: '枫桥',
    zhouzhuang: '周庄',
    tongli: '同里',
    suzhou: '苏州',
    nanjing: '南京',
  };
  return map[c] ?? c;
}

// 从 "1587年1月" 提取年份
function parseYearFromDate(s: string): number {
  if (!s) return 1587;
  const m = String(s).match(/(\d{3,4})/);
  return m ? parseInt(m[1], 10) : 1587;
}

// 从 triggered_events 派生 timeline
function buildTimelineFromEvents(b: BackendState) {
  // 万历十五年的真实大事
  const known = [
    { year: 1587, event: '海瑞罢官', highlight: true },
    { year: 1589, event: '戚继光去世', highlight: false },
    { year: 1596, event: '矿税监设立', highlight: false },
    { year: 1601, event: '葛贤抗税', highlight: true },
  ];
  return known.filter(k => k.year >= 1587);
}
