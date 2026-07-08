/**
 * Wizard 状态 - 角色创建流程（v2.0 简化版）
 *
 * 流程（3 步）：
 *   1. 身份（4 选 1）→ 自动绑定性别 + 年龄 + 职业 + 家乡
 *   2. 姓名
 *   3. 确认 → "入 局"
 *
 * 设计原则：
 *   - 玩家只选核心：身份 + 名字
 *   - 其余信息由身份预设（不可改）
 *   - 减少步骤 = 减少劝退
 */
import type { Identity, Gender } from '$lib/api/types';

export interface PresetProfile {
  age: number;
  occupation: string;
  hometown: string;
}

export interface WizardState {
  currentStep: number;
  totalSteps: number;

  // 步骤 1：身份（自动绑定性别/年龄/职业/家乡）
  identity: Identity | null;

  // 步骤 2：姓名
  name: string;
}

// 🆕 v2.0：身份预设表
export const IDENTITY_PRESETS: Record<Identity, {
  name: string;
  gender: Gender;
  icon: string;
  desc: string;
  profile: PresetProfile;
}> = {
  weaving_male: {
    name: '织工',
    gender: 'male',
    icon: '🧵',
    desc: '苏州盛泽，挽丝织绸',
    profile: { age: 30, occupation: '织工', hometown: '盛泽镇' }
  },
  weaving_female: {
    name: '织女',
    gender: 'female',
    icon: '🧵',
    desc: '盛泽镇东栅巷',
    profile: { age: 28, occupation: '织工', hometown: '盛泽镇' }
  },
  merchant_male: {
    name: '牙商',
    gender: 'male',
    icon: '💰',
    desc: '往来于市肆之间',
    profile: { age: 35, occupation: '牙商', hometown: '盛泽镇' }
  },
  farmer_male: {
    name: '佃户',
    gender: 'male',
    icon: '🌾',
    desc: '日出而作，日落而息',
    profile: { age: 40, occupation: '佃户', hometown: '盛泽镇' }
  }
};

// 初始状态
const initial: WizardState = {
  currentStep: 0,
  totalSteps: 3,
  identity: null,
  name: ''
};

// 🆕 v2.0：Svelte 5 runes-based store
class WizardStore {
  state = $state<WizardState>({ ...initial });

  // 派生：当前是否可以进入下一步
  canProceed = $derived.by(() => {
    const s = this.state;
    switch (s.currentStep) {
      case 0: return !!s.identity;
      case 1: return s.name.trim().length > 0 && s.name.trim().length <= 12;
      case 2: return true;  // 确认页总可以提交
      default: return false;
    }
  });

  // 派生：是否最后一步
  isLastStep = $derived(this.state.currentStep === this.state.totalSteps - 1);

  // 派生：身份对应的性别
  inferredGender = $derived(
    this.state.identity ? IDENTITY_PRESETS[this.state.identity].gender : null
  );

  // 派生：身份对应的预设信息
  inferredProfile = $derived(
    this.state.identity ? IDENTITY_PRESETS[this.state.identity].profile : null
  );

  // 派生：身份显示名
  identityName = $derived(
    this.state.identity ? IDENTITY_PRESETS[this.state.identity].name : '?'
  );

  next() {
    if (this.canProceed && this.state.currentStep < this.state.totalSteps - 1) {
      this.state.currentStep++;
    }
  }

  prev() {
    if (this.state.currentStep > 0) {
      this.state.currentStep--;
    }
  }

  goTo(step: number) {
    if (step >= 0 && step < this.state.totalSteps) {
      this.state.currentStep = step;
    }
  }

  reset() {
    this.state = { ...initial };
  }

  setIdentity(identity: Identity) {
    this.state.identity = identity;
  }

  setName(name: string) {
    this.state.name = name;
  }
}

export const wizard = new WizardStore();

// 身份列表（4 个）
export const IDENTITIES = (Object.entries(IDENTITY_PRESETS) as [Identity, typeof IDENTITY_PRESETS[Identity]][])
  .map(([id, data]) => ({
    id,
    name: data.name,
    icon: data.icon,
    desc: data.desc,
    gender: data.gender
  }));

// 保留（兼容）
export function inferGenderFromIdentity(identity: Identity): Gender | null {
  return IDENTITY_PRESETS[identity]?.gender ?? null;
}
