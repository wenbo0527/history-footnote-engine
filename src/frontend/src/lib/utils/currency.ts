/**
 * 🆕 v2.10.2 W52 followup: 银钱单位格式化（前端版）
 *
 * 与后端 src/history_footnote/currency.py 保持一致：
 * - 1 两 = 10 钱 = 100 分 = 1000 厘/文
 * - 后端以"两"为 float 内部精度单位
 * - 前端展示时按需格式化
 */

/** 单位换算表（以"两"为基准） */
const UNIT_TO_LIANG: Record<string, number> = {
  两: 1.0,
  钱: 0.1,
  分: 0.01,
  厘: 0.001,
  文: 0.001,
};

/**
 * 紧凑显示（2 位有效单位）
 *
 * 示例：
 *   toCompactLiang(5.7) === "5 两 7 钱"
 *   toCompactLiang(0.5) === "5 钱"
 *   toCompactLiang(0.05) === "5 分"
 *   toCompactLiang(0.005) === "5 厘"
 *   toCompactLiang(0) === "0 两"
 *   toCompactLiang(-5) === "-5 两"
 */
export function toCompactLiang(liang: number): string {
  if (liang === 0) return "0 两";
  const abs = Math.abs(liang);
  const sign = liang < 0 ? "-" : "";

  if (abs >= 1) {
    const intPart = Math.floor(abs);
    const remainder = Math.round((abs - intPart) * 10); // 0-9 钱
    if (remainder === 0) {
      return `${sign}${intPart} 两`;
    }
    return `${sign}${intPart} 两 ${remainder} 钱`;
  } else if (abs >= 0.1) {
    const qians = Math.round(abs * 10);
    return `${sign}${qians} 钱`;
  } else if (abs >= 0.01) {
    const fens = Math.round(abs * 100);
    return `${sign}${fens} 分`;
  } else {
    const centis = Math.round(abs * 1000);
    if (centis === 0) {
      return `${sign}0 两`;
    }
    return `${sign}${centis} 厘`;
  }
}

/**
 * 详细显示（所有层级）
 *
 * 示例：
 *   toLiang(5.789) === "5 两 7 钱 8 分 9 厘"
 *   toLiang(0.5) === "5 钱"
 *   toLiang(0.05) === "5 分"
 */
export function toLiang(liang: number): string {
  if (liang === 0) return "0 两";
  const liangInt = Math.floor(liang);
  const remainder = liang - liangInt;

  if (remainder === 0) {
    return `${liangInt} 两`;
  }

  const centis = Math.round(remainder * 1000);

  if (centis < 10) {
    if (liangInt === 0) return `${centis} 厘`;
    return `${liangInt} 两 ${centis} 厘`;
  }

  const fens = Math.floor(centis / 10);
  const centisLeft = centis % 10;
  if (fens < 10) {
    if (liangInt === 0) {
      if (centisLeft === 0) return `${fens} 分`;
      return `${fens} 分 ${centisLeft} 厘`;
    }
    if (centisLeft === 0) return `${liangInt} 两 ${fens} 分`;
    return `${liangInt} 两 ${fens} 分 ${centisLeft} 厘`;
  }

  const qians = Math.floor(fens / 10);
  const fensLeft = fens % 10;
  if (liangInt === 0) {
    if (fensLeft === 0 && centisLeft === 0) return `${qians} 钱`;
    if (centisLeft === 0) return `${qians} 钱 ${fensLeft} 分`;
    return `${qians} 钱 ${fensLeft} 分 ${centisLeft} 厘`;
  }
  if (fensLeft === 0 && centisLeft === 0) {
    return `${liangInt} 两 ${qians} 钱`;
  }
  if (centisLeft === 0) {
    return `${liangInt} 两 ${qians} 钱 ${fensLeft} 分`;
  }
  return `${liangInt} 两 ${qians} 钱 ${fensLeft} 分 ${centisLeft} 厘`;
}

/**
 * 显示为 "X.XX 两"（保留 2 位小数，机器展示）
 *
 * 示例：
 *   toLiangOrYuan(5) === "5.00 两"
 *   toLiangOrYuan(5.7) === "5.70 两"
 */
export function toLiangOrYuan(liang: number): string {
  return `${liang.toFixed(2)} 两`;
}
