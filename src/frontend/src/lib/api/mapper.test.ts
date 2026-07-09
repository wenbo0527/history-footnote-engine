/**
 * mapper.test.ts - 前端 mapper 端到端测试（v2.5+）
 *
 * 🆕 v2.5 教训：
 * - 之前 commit 584dfa6 漏了前端 mapper 字段映射
 * - 后端有数据 + 类型有字段 = 没用（mapper 没 put）
 * - 这个测试确保字段真正流到前端
 */
import { describe, it, expect } from 'vitest';
import { mapBackendState } from './mapper';

describe('mapBackendState', () => {
  it('T1: 透传命运卡（fate_hand）', () => {
    const raw = {
      session_id: 'test_123',
      era_id: 'wanli1587',
      era_name: '万历十五年',
      round_number: 1,
      current_date: '1587年1月',
      action_points_current: 3,
      action_points_max: 3,
      selected_identity: 'weaving_male',
      player_gender: 'male',
      current_city: 'shengze',
      unlocked_insights: [],
      triggered_events: [],
      variables: {},
      value_shifts: {},
      recent_narratives: [],
      custom_character: { name: '李三', age: 30, occupation: '织工', hometown: '盛泽镇' },
      family_members: [],
      genealogy: [],
      cash: 5.0,
      rice: 10,
      debt: 0,
      monthly_burn: 0.42,
      financial_log: [],
      last_voice_options: [],
      sidebar_data: { active_tasks: [], upcoming_deadlines: [], financial_status: {} },
      city_properties: {},
      inventory: {},
      discoveries: {},
      completed_tasks_count: 0,
      // 🆕 v2.5 字段
      seed: 12345,
      fate_hand: [
        { id: 'windfall', name: '天降横财', icon: '💰', color: '#6b8b5a',
          description: '获得 3 两', effect_type: 'modify_state', effect_params: {},
          used: false, use_type: 'immediate', use_constraints: {}, use_hint: '现金不够时用' },
        { id: 'shield', name: '护身符', icon: '🛡️', color: '#5a7a8b',
          description: '本回合所有失败减半', effect_type: 'apply_shield', effect_params: {},
          used: false, use_type: 'emergency', use_constraints: { min_cash: 2 }, use_hint: '危机时' },
      ],
      fate_used: [],
      fate_event_flags: [],
      npc_relations: { '沈氏': 30 },
      active_buffs: [{ name: 'lucky', rounds_left: 2, params: {} }],
    } as any;

    const state = mapBackendState(raw);
    expect(state.fate_hand).toHaveLength(2);
    expect(state.fate_hand![0].id).toBe('windfall');
    expect(state.fate_hand![0].use_type).toBe('immediate');
    expect(state.fate_hand![1].use_constraints).toEqual({ min_cash: 2 });
  });

  it('T2: 透传 seed', () => {
    const raw = {
      session_id: 't', era_id: 'wanli1587', era_name: '', round_number: 0,
      current_date: '', action_points_current: 0, action_points_max: 0,
      selected_identity: '', player_gender: '', current_city: '',
      unlocked_insights: [], triggered_events: [], variables: {}, value_shifts: {},
      recent_narratives: [], custom_character: null as any, family_members: [],
      genealogy: [], cash: 0, rice: 0, debt: 0, monthly_burn: 0, financial_log: [],
      last_voice_options: [], sidebar_data: { active_tasks: [], upcoming_deadlines: [], financial_status: {} },
      city_properties: {}, inventory: {}, discoveries: {}, completed_tasks_count: 0,
      seed: 999999,
      fate_hand: [], fate_used: [], fate_event_flags: [],
      npc_relations: {}, active_buffs: [],
    } as any;
    const state = mapBackendState(raw);
    expect(state.seed).toBe(999999);
  });

  it('T3: 透传 npc_relations', () => {
    const raw = {
      session_id: 't', era_id: 'wanli1587', era_name: '', round_number: 0,
      current_date: '', action_points_current: 0, action_points_max: 0,
      selected_identity: '', player_gender: '', current_city: '',
      unlocked_insights: [], triggered_events: [], variables: {}, value_shifts: {},
      recent_narratives: [], custom_character: null as any, family_members: [],
      genealogy: [], cash: 0, rice: 0, debt: 0, monthly_burn: 0, financial_log: [],
      last_voice_options: [], sidebar_data: { active_tasks: [], upcoming_deadlines: [], financial_status: {} },
      city_properties: {}, inventory: {}, discoveries: {}, completed_tasks_count: 0,
      seed: 0,
      fate_hand: [], fate_used: [], fate_event_flags: [],
      npc_relations: { '沈氏': 30, '王牙人': -20 },
      active_buffs: [],
    } as any;
    const state = mapBackendState(raw);
    expect(state.npc_relations).toEqual({ '沈氏': 30, '王牙人': -20 });
  });

  it('T4: 透传 active_buffs', () => {
    const raw = {
      session_id: 't', era_id: 'wanli1587', era_name: '', round_number: 0,
      current_date: '', action_points_current: 0, action_points_max: 0,
      selected_identity: '', player_gender: '', current_city: '',
      unlocked_insights: [], triggered_events: [], variables: {}, value_shifts: {},
      recent_narratives: [], custom_character: null as any, family_members: [],
      genealogy: [], cash: 0, rice: 0, debt: 0, monthly_burn: 0, financial_log: [],
      last_voice_options: [], sidebar_data: { active_tasks: [], upcoming_deadlines: [], financial_status: {} },
      city_properties: {}, inventory: {}, discoveries: {}, completed_tasks_count: 0,
      seed: 0,
      fate_hand: [], fate_used: [], fate_event_flags: [],
      npc_relations: {},
      active_buffs: [
        { name: 'lucky', rounds_left: 2, params: {} },
        { name: 'shield', rounds_left: 1, params: { failure_reduction: 0.5 } },
      ],
    } as any;
    const state = mapBackendState(raw);
    expect(state.active_buffs).toHaveLength(2);
    expect(state.active_buffs![0].name).toBe('lucky');
  });

  it('T5: 缺字段时用默认值（不崩）', () => {
    // 后端不返新字段时（如老 session）
    const raw = {
      session_id: 't', era_id: 'wanli1587', era_name: '', round_number: 0,
      current_date: '', action_points_current: 0, action_points_max: 0,
      selected_identity: '', player_gender: '', current_city: '',
      unlocked_insights: [], triggered_events: [], variables: {}, value_shifts: {},
      recent_narratives: [], custom_character: null as any, family_members: [],
      genealogy: [], cash: 0, rice: 0, debt: 0, monthly_burn: 0, financial_log: [],
      last_voice_options: [], sidebar_data: { active_tasks: [], upcoming_deadlines: [], financial_status: {} },
      city_properties: {}, inventory: {}, discoveries: {}, completed_tasks_count: 0,
      // 没有 seed/fate_hand/npc_relations/active_buffs
    } as any;
    const state = mapBackendState(raw);
    expect(state.fate_hand).toEqual([]);
    expect(state.fate_used).toEqual([]);
    expect(state.npc_relations).toEqual({});
    expect(state.active_buffs).toEqual([]);
    expect(state.seed).toBe(0);
  });

  it('T6: 全部 v2.5 字段全链路端到端（start → mapper → game）', () => {
    // 模拟 /api/start 的完整响应
    const startResponse = {
      session_id: 'wanli1587_20260709_155543',
      seed: 12345,
      fate_hand: [
        { id: 'windfall', name: '天降横财', icon: '💰', color: '#6b8b5a',
          description: '获得 3 两', effect_type: 'modify_state', effect_params: {},
          used: false, use_type: 'immediate', use_constraints: {}, use_hint: '现金不够时用' },
        { id: 'lucky_star', name: '吉星高照', icon: '✨', color: '#b8860b',
          description: '+10% 检定', effect_type: 'apply_buff', effect_params: {},
          used: false, use_type: 'emergency', use_constraints: {}, use_hint: '硬闯前用' },
      ],
      // ... 其他字段
      era_id: 'wanli1587', era_name: '万历十五年', round_number: 0,
      current_date: '1587年1月', action_points_current: 3, action_points_max: 3,
      selected_identity: 'weaving_male', player_gender: 'male', current_city: 'shengze',
      unlocked_insights: [], triggered_events: [], variables: {}, value_shifts: {},
      recent_narratives: [],
      custom_character: { name: '李三', age: 30, occupation: '织工', hometown: '盛泽镇' },
      family_members: [], genealogy: [],
      cash: 5.0, rice: 10, debt: 0, monthly_burn: 0.42, financial_log: [],
      last_voice_options: [],
      sidebar_data: { active_tasks: [], upcoming_deadlines: [], financial_status: {} },
      city_properties: {}, inventory: {}, discoveries: {}, completed_tasks_count: 0,
    } as any;

    const state = mapBackendState(startResponse);
    // 玩家应能看到 2 张命运卡
    expect(state.fate_hand).toHaveLength(2);
    expect(state.fate_hand![0].name).toBe('天降横财');
    expect(state.fate_hand![1].use_type).toBe('emergency');
    expect(state.seed).toBe(12345);
  });
});
