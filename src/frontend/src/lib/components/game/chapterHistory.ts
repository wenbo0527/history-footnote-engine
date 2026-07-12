/**
 * 🆕 v2.9.x W45: 章节历史 timeline 辅助函数
 *
 * 章节历史数据结构（来自 chapter.settlement.settle()）：
 * {
 *   chapter: int,
 *   summary: str,
 *   core_event: str,
 *   key_choice: str,
 *   build_summary: str,
 *   path_summary: str,
 *   rounds_in_chapter: int,
 *   ended_at_round: int,
 *   ended_at: str (ISO),
 *   transition: str,
 *   closure_status: str,  // "SOFT_READY" / "HARD_FORCED"
 * }
 *
 * timeline 节点：在原记录上添加：
 * - isFirst / isLast: 第一/最后
 * - durationLabel: "8 轮 (round 5-12)"
 * - closureLabel: "软收束" / "强制收尾"
 * - status: "current" / "past" / "future"（基于 currentChapter）
 *
 * 🆕 v2.10.1 fix: history 中元素字段变为 optional（与 $lib/api/chapter 兼容）
 */

export interface ChapterRecord {
  chapter: number;
  summary: string;
  core_event?: string;
  key_choice?: string;
  build_summary?: string;
  path_summary?: string;
  rounds_in_chapter?: number;
  ended_at_round?: number;
  ended_at?: string;
  transition?: string;
  closure_status?: string;
}

export interface TimelineNode extends ChapterRecord {
  isFirst: boolean;
  isLast: boolean;
  durationLabel: string;
  closureLabel: string;
  status: 'current' | 'past' | 'future';
}

export interface ChapterHistoryResponse {
  count: number;
  history: ChapterRecord[];
}

/**
 * 转化章节历史为 timeline 节点列表
 */
export function toTimeline(
  response: ChapterHistoryResponse,
  currentChapter: number = 0,
  totalChapters: number = 10
): TimelineNode[] {
  const history = response.history || [];
  const maxChapter = Math.max(
    totalChapters,
    currentChapter,
    history.length > 0 ? history[history.length - 1].chapter : 0,
  );

  // 1. 转 record
  const nodes: TimelineNode[] = history.map((rec) => ({
    ...rec,
    isFirst: rec.chapter === 1,
    isLast: rec.chapter >= totalChapters,
    durationLabel: buildDurationLabel(rec),
    closureLabel: buildClosureLabel(rec.closure_status ?? ''),
    status: rec.chapter < currentChapter
      ? 'past'
      : rec.chapter === currentChapter
        ? 'current'
        : 'future',
  }));

  // 2. 填充未来章节占位（虚线）
  for (let ch = 1; ch <= maxChapter; ch++) {
    if (!nodes.find((n) => n.chapter === ch)) {
      nodes.push({
        chapter: ch,
        summary: '',
        core_event: '',
        key_choice: '',
        build_summary: '',
        path_summary: '',
        rounds_in_chapter: 0,
        ended_at_round: 0,
        ended_at: '',
        transition: '',
        closure_status: '',
        isFirst: ch === 1,
        isLast: ch === totalChapters,
        durationLabel: '未开始',
        closureLabel: '',
        status: ch < currentChapter ? 'past' : ch === currentChapter ? 'current' : 'future',
      });
    }
  }

  // 3. 按章节号排序
  nodes.sort((a, b) => a.chapter - b.chapter);

  // 4. 修正 isLast
  const lastIdx = nodes.length - 1;
  nodes.forEach((n, i) => {
    n.isLast = i === lastIdx;
  });

  return nodes;
}

/**
 * 持续时长标签：例如 "8 轮 (round 5-12)"
 */
export function buildDurationLabel(rec: ChapterRecord): string {
  if (rec.rounds_in_chapter === 0 || rec.rounds_in_chapter === undefined) return '未开始';
  const startRound = Math.max(1, (rec.ended_at_round ?? 0) - rec.rounds_in_chapter + 1);
  return `${rec.rounds_in_chapter} 轮 (round ${startRound}-${rec.ended_at_round ?? 0})`;
}

/**
 * 收尾状态标签
 */
export function buildClosureLabel(closureStatus: string): string {
  const map: Record<string, string> = {
    SOFT_READY: '软收束',
    HARD_FORCED: '强制收尾',
  };
  return map[closureStatus] ?? closureStatus;
}

/**
 * 进度百分比
 */
export function progressPercent(currentChapter: number, totalChapters: number): number {
  if (totalChapters <= 0) return 0;
  return Math.min(100, Math.max(0, (currentChapter / totalChapters) * 100));
}

/**
 * 章节进度（圆点定位）
 */
export function chapterDotX(chapter: number, totalChapters: number, width: number = 100): number {
  if (totalChapters <= 1) return 0;
  return ((chapter - 1) / (totalChapters - 1)) * width;
}
