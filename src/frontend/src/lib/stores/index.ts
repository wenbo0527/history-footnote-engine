// Stores 统一导出
export { session, sessionActions } from './session';
export {
  game, isLoading, lastError,
  narrativeHistory, currentNarrative, voiceOptions,
  gameActions
} from './game';
export {
  wizard,
  IDENTITIES, IDENTITY_PRESETS, inferGenderFromIdentity,
  type WizardState, type PresetProfile
} from './wizard.svelte';
// 🆕 v2.7 命运卡事件总线（CharCard → FateHandPanel 通信）
export { fateEvents } from './fate-events';
