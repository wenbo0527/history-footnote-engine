/**
 * v2.10.2 W52 followup: 关系详注派生逻辑测试
 *
 * 验证 relationshipNotes 派生函数
 * - 后端无 wiki.markdown 字段
 * - 用 wiki.relationships 派生
 */
import { describe, it, expect } from 'vitest';

// 🆕 v2.10.2 派生函数（与 CharacterWikiModal.svelte 同步）
function deriveRelationshipNotes(wiki: any): Array<{ key: string; name: string; value: string }> {
  if (!wiki) return [];
  const notes: Array<{ key: string; name: string; value: string }> = [];
  const rels = (wiki as any).relationships || {};
  for (const [name, info] of Object.entries(rels)) {
    if (typeof info === 'string') {
      notes.push({ key: name, name, value: info });
    } else if (info && typeof info === 'object') {
      const value = (info as any).note
        || (info as any).relation
        || (info as any).level
        || JSON.stringify(info);
      notes.push({ key: name, name, value: String(value) });
    }
  }
  return notes;
}

describe('relationshipNotes 派生', () => {
  it('无 wiki 返回空数组', () => {
    expect(deriveRelationshipNotes(null)).toEqual([]);
    expect(deriveRelationshipNotes(undefined)).toEqual([]);
  });

  it('无 relationships 返回空数组', () => {
    expect(deriveRelationshipNotes({})).toEqual([]);
    expect(deriveRelationshipNotes({ characters: [], events: [] })).toEqual([]);
  });

  it('字符串 value 直接显示', () => {
    const wiki = {
      relationships: {
        '沈氏': '妻子',
        '阿宝': '儿子',
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes).toHaveLength(2);
    expect(notes[0]).toEqual({ key: '沈氏', name: '沈氏', value: '妻子' });
    expect(notes[1]).toEqual({ key: '阿宝', name: '阿宝', value: '儿子' });
  });

  it('对象 value 用 note 字段', () => {
    const wiki = {
      relationships: {
        '李秀才': { relation: '朋友', note: '同窗', level: 5 },
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes[0].name).toBe('李秀才');
    expect(notes[0].value).toBe('同窗');  // 优先用 note
  });

  it('对象 value 无 note 用 relation 字段', () => {
    const wiki = {
      relationships: {
        '王二嫂': { relation: '邻人' },
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes[0].value).toBe('邻人');
  });

  it('对象 value 无 note/relation 用 level', () => {
    const wiki = {
      relationships: {
        '赵里长': { level: 3 },
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes[0].value).toBe('3');
  });

  it('对象 value 完全空 → JSON.stringify', () => {
    const wiki = {
      relationships: {
        '神秘人': {},
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes[0].value).toBe('{}');
  });

  it('混合字符串 + 对象', () => {
    const wiki = {
      relationships: {
        'A': '朋友',
        'B': { note: '家人' },
        'C': { relation: '敌人' },
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes).toHaveLength(3);
    expect(notes[0].value).toBe('朋友');
    expect(notes[1].value).toBe('家人');
    expect(notes[2].value).toBe('敌人');
  });

  it('key 唯一（用 name 作 key）', () => {
    const wiki = {
      relationships: {
        'A': '敌人',  // 后者会覆盖前者
      },
    };
    const notes = deriveRelationshipNotes(wiki);
    expect(notes).toHaveLength(1);
    expect(notes[0].value).toBe('敌人');
  });
});
