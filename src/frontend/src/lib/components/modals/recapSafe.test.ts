/**
 * v2.10.2 W52 followup: RecapModal optional 字段派生函数测试
 */
import { describe, it, expect } from 'vitest';

// 🆕 v2.10.2 派生函数（与 RecapModal.svelte 同步）
function safeDate(d: string | undefined | null): string {
  return d && d.trim() ? d : '—';
}
function safeChoice(voice: string | undefined | null, input: string | undefined | null): { label: string; isVoice: boolean } {
  if (voice && voice.trim()) {
    return { label: voice, isVoice: true };
  }
  if (input && input.trim()) {
    return { label: input, isVoice: false };
  }
  return { label: '（无记录）', isVoice: false };
}
function safeNarrative(n: string | undefined | null): string {
  return n && n.trim() ? n : '（无叙事）';
}

describe('RecapModal safe 派生函数', () => {
  describe('safeDate', () => {
    it('正常日期透传', () => {
      expect(safeDate('万历十五年四月')).toBe('万历十五年四月');
    });
    it('undefined → —', () => {
      expect(safeDate(undefined)).toBe('—');
    });
    it('null → —', () => {
      expect(safeDate(null)).toBe('—');
    });
    it('空字符串 → —', () => {
      expect(safeDate('')).toBe('—');
    });
    it('全空白 → —', () => {
      expect(safeDate('   ')).toBe('—');
    });
  });

  describe('safeChoice', () => {
    it('有 voice 时返回 voice', () => {
      const r = safeChoice('起身上路', '我去苏州');
      expect(r).toEqual({ label: '起身上路', isVoice: true });
    });
    it('无 voice 有 input 时返回 input', () => {
      const r = safeChoice(undefined, '我去苏州');
      expect(r).toEqual({ label: '我去苏州', isVoice: false });
    });
    it('全无时返回"（无记录）"', () => {
      const r = safeChoice(undefined, undefined);
      expect(r).toEqual({ label: '（无记录）', isVoice: false });
    });
    it('空字符串 voice → 用 input', () => {
      const r = safeChoice('', '我去苏州');
      expect(r).toEqual({ label: '我去苏州', isVoice: false });
    });
  });

  describe('safeNarrative', () => {
    it('正常 narrative 透传', () => {
      expect(safeNarrative('你摸了摸他的头。')).toBe('你摸了摸他的头。');
    });
    it('undefined → （无叙事）', () => {
      expect(safeNarrative(undefined)).toBe('（无叙事）');
    });
    it('null → （无叙事）', () => {
      expect(safeNarrative(null)).toBe('（无叙事）');
    });
    it('空字符串 → （无叙事）', () => {
      expect(safeNarrative('')).toBe('（无叙事）');
    });
  });
});

/**
 * BUG 9 fix: ShareCardButton gameRoleName 派生
 */
function deriveGameRoleName(game: any): string {
  const id = game?.character?.identity || game?.identity;
  const name = game?.character?.name || '织工';
  if (id === 'weaving_male') return `织工·${name}`;
  if (id === 'weaving_female') return `织女·${name}`;
  if (id === 'merchant_male') return `牙商·${name}`;
  if (id === 'merchant_female') return `牙商·${name}`;
  if (id === 'farmer_male') return `佃户·${name}`;
  if (id === 'farmer_female') return `佃妇·${name}`;
  return `织户·${name}`;
}

describe('ShareCardButton gameRoleName', () => {
  it('weaving_male → 织工', () => {
    expect(deriveGameRoleName({ character: { identity: 'weaving_male', name: '老沈' } })).toBe('织工·老沈');
  });
  it('weaving_female → 织女', () => {
    expect(deriveGameRoleName({ character: { identity: 'weaving_female', name: '沈氏' } })).toBe('织女·沈氏');
  });
  it('merchant_male → 牙商', () => {
    expect(deriveGameRoleName({ character: { identity: 'merchant_male', name: '王老板' } })).toBe('牙商·王老板');
  });
  it('farmer_male → 佃户', () => {
    expect(deriveGameRoleName({ character: { identity: 'farmer_male', name: '张二' } })).toBe('佃户·张二');
  });
  it('character 缺失 → 兜底 "织户·织工"', () => {
    expect(deriveGameRoleName(null)).toBe('织户·织工');
    expect(deriveGameRoleName({})).toBe('织户·织工');
  });
  it('character.identity 缺失但有 identity 字段（fallback）', () => {
    expect(deriveGameRoleName({ identity: 'merchant_male', character: { name: '王老板' } })).toBe('牙商·王老板');
  });
  it('character.name 缺失 → 兜底 "织工"', () => {
    expect(deriveGameRoleName({ character: { identity: 'weaving_male' } })).toBe('织工·织工');
  });
  it('未知 identity → 兜底 "织户"', () => {
    expect(deriveGameRoleName({ character: { identity: 'unknown_xyz', name: '某' } })).toBe('织户·某');
  });
});

/**
 * BUG 7 fix: CharacterCard relation 兜底
 */
function deriveRelation(character: any): string {
  return character?.relation || '陌生人';
}

describe('CharacterCard relation 兜底', () => {
  it('正常 relation 透传', () => {
    expect(deriveRelation({ relation: '妻子' })).toBe('妻子');
  });
  it('undefined → 陌生人', () => {
    expect(deriveRelation({})).toBe('陌生人');
    expect(deriveRelation(null)).toBe('陌生人');
  });
  it('空字符串 → 陌生人', () => {
    expect(deriveRelation({ relation: '' })).toBe('陌生人');
  });
});
