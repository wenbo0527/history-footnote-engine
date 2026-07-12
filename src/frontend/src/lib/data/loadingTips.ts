/**
 * loadingTips - DM 思考中的"过场文字" 池
 *
 * 🆕 v1.7.32: 因为 LLM 推理需要 1-2 分钟（节气评估 + DM 思考 + 叙事生成），
 * 玩家点击 voice 后只看 spinner 会焦虑。改成"随机翻动"明清知识，让等待变成阅读。
 *
 * 数据来源：eras/wanli1587/era.json 的 iron_laws（10 条）+ 自洽文案。
 * 通过 Vite 的 ?url/raw import 静态引入，避免运行时再读 /api。
 *
 * 设计：
 *  - category="history"：明史铁律，让等待中读到真实史料
 *  - category="atmosphere"：盛泽镇日常碎片，增加沉浸
 *  - category="system"：技术提示（如"思考中""请求中"）
 */
import eraJson from '../../../../../eras/wanli1587/era.json';

export interface LoadingTip {
  text: string;
  source: string;        // 出处（如"明史·神宗本纪"）
  category: 'history' | 'atmosphere' | 'system';
}

// 从 era.json 抽出 iron_laws.fact + source
// 🆕 v2.10.1 fix: 用 type assertion（era config 类型未声明 iron_laws 字段）
const historyTips: LoadingTip[] = (
  (eraJson.world as any)?.iron_laws ||
  (eraJson as any).iron_laws ||
  []
).map((law: any) => ({
  text: law.fact,
  source: law.source || '明史',
  category: 'history' as const,
}));

// 沉浸式文案（盛泽镇日常，与织工开局叙事呼应）
const atmosphereTips: LoadingTip[] = [
  { text: '盛泽镇的清晨，织机声往往比鸡鸣早一刻。', source: '江南织工谈', category: 'atmosphere' },
  { text: '一张湖丝从投梭到织成要七天七夜。', source: '天工开物', category: 'atmosphere' },
  { text: '盛泽四乡有织机近万台，所产皆称盛湖绸。', source: '盛湖志', category: 'atmosphere' },
  { text: '丝以水漂洗，谓之"缫丝"；练丝之时，用梅水最佳。', source: '天工开物', category: 'atmosphere' },
  { text: '牙行收一方佣金，称"用钱"，三分为常。', source: '客商习惯', category: 'atmosphere' },
  { text: '春税多在正月开征，由里长挨家递"催单"。', source: '里甲则例', category: 'atmosphere' },
  { text: '朝廷开矿税监，所到之处百业萧条。', source: '万历野获', category: 'atmosphere' },
];

// 技术提示
const systemTips: LoadingTip[] = [
  { text: 'DM 正在推演节气影响与人物命运…', source: '系统', category: 'system' },
  { text: 'DM 正在权衡道德与利益的平衡…', source: '系统', category: 'system' },
  { text: 'DM 正在掂量银两的轻重…', source: '系统', category: 'system' },
  { text: 'DM 正在观察你动作背后的人心…', source: '系统', category: 'system' },
  { text: 'DM 正在编织下一步的命数…', source: '系统', category: 'system' },
];

/** 全部 tip（用于随机翻动）*/
export const LOADING_TIPS: LoadingTip[] = [
  ...historyTips,
  ...atmosphereTips,
  ...systemTips,
];

/** 随机选一条 */
export function randomTip(seed?: number): LoadingTip {
  if (LOADING_TIPS.length === 0) {
    return { text: '请稍候…', source: '系统', category: 'system' };
  }
  const idx = seed !== undefined
    ? seed % LOADING_TIPS.length
    : Math.floor(Math.random() * LOADING_TIPS.length);
  return LOADING_TIPS[idx];
}
