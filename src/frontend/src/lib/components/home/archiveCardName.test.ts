/**
 * v2.10.2 W52 followup: ArchiveCard 派生逻辑测试
 *
 * 验证 deriveCharacterName / deriveCharacterOccupation 函数
 * （避开 .svelte 组件 mount 兼容性）
 */
import { describe, it, expect } from 'vitest';
import { IDENTITY_PRESETS } from '$lib/stores/wizard.svelte';
import type { Archive, Identity } from '$lib/api/types';

// 🆕 v2.10.2 派生函数（与 ArchiveCard.svelte 逻辑同步）
function deriveCharacterName(archive: Archive): string {
  if (archive.character_name && archive.character_name.trim()) {
    return archive.character_name;
  }
  const preset = IDENTITY_PRESETS[archive.selected_identity as Identity];
  if (preset) {
    return preset.name;
  }
  return '盛泽织户';
}

function deriveCharacterOccupation(archive: Archive): string {
  if (archive.character_occupation && archive.character_occupation.trim()) {
    return archive.character_occupation;
  }
  const preset = IDENTITY_PRESETS[archive.selected_identity as Identity];
  if (preset) {
    return preset.profile.occupation;
  }
  return '织工';
}

const baseArchive: Archive = {
  session_id: 'sess-1',
  era_id: 'wanli1587',
  current_round: 5,
  current_date: '1587年4月',
  summary: '测试',
  created_at: '2026-01-01T00:00:00Z',
  last_saved_at: '2026-01-01T00:00:00Z',
  selected_identity: 'weaving_male',
  player_gender: 'male',
};

describe('ArchiveCard 派生 name/occupation', () => {
  describe('name', () => {
    it('后端返回的 character_name 优先', () => {
      const archive = { ...baseArchive, character_name: '沈万三' };
      expect(deriveCharacterName(archive)).toBe('沈万三');
    });

    it('无 character_name 时，用 IDENTITY_PRESETS 派生（weaving_male → 织工）', () => {
      const archive = { ...baseArchive };
      delete (archive as any).character_name;
      expect(deriveCharacterName(archive)).toBe('织工');
    });

    it('weaving_female → 织女', () => {
      const archive = { ...baseArchive, selected_identity: 'weaving_female' as Identity };
      expect(deriveCharacterName(archive)).toBe('织女');
    });

    it('merchant_male → 牙商', () => {
      const archive = { ...baseArchive, selected_identity: 'merchant_male' as Identity };
      expect(deriveCharacterName(archive)).toBe('牙商');
    });

    it('farmer_male → 佃户', () => {
      const archive = { ...baseArchive, selected_identity: 'farmer_male' as Identity };
      expect(deriveCharacterName(archive)).toBe('佃户');
    });

    it('未知 selected_identity → generic 兜底（盛泽织户）', () => {
      const archive = { ...baseArchive, selected_identity: 'unknown_identity' as any };
      expect(deriveCharacterName(archive)).toBe('盛泽织户');
    });

    it('空字符串 selected_identity → generic 兜底', () => {
      const archive = { ...baseArchive, selected_identity: '' };
      expect(deriveCharacterName(archive)).toBe('盛泽织户');
    });

    it('全空白 character_name 走 fallback', () => {
      const archive = { ...baseArchive, character_name: '   ' };
      expect(deriveCharacterName(archive)).toBe('织工');
    });
  });

  describe('occupation', () => {
    it('后端返回的 character_occupation 优先', () => {
      const archive = { ...baseArchive, character_occupation: '苏州织户' };
      expect(deriveCharacterOccupation(archive)).toBe('苏州织户');
    });

    it('weaving_male → 织工', () => {
      const archive = { ...baseArchive };
      delete (archive as any).character_occupation;
      expect(deriveCharacterOccupation(archive)).toBe('织工');
    });

    it('merchant_male → 牙商', () => {
      const archive = { ...baseArchive, selected_identity: 'merchant_male' as Identity };
      expect(deriveCharacterOccupation(archive)).toBe('牙商');
    });

    it('farmer_male → 佃户', () => {
      const archive = { ...baseArchive, selected_identity: 'farmer_male' as Identity };
      expect(deriveCharacterOccupation(archive)).toBe('佃户');
    });

    it('未知 selected_identity → generic 兜底（织工）', () => {
      const archive = { ...baseArchive, selected_identity: 'unknown' as any };
      expect(deriveCharacterOccupation(archive)).toBe('织工');
    });
  });
});
