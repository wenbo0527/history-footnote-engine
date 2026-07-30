/**
 * 🆕 v2.10.x — CityData 共享类型
 *
 * 多个组件需要 CityData (CityMarker, TravelLine, WorldMap)
 * 提取为独立 .ts 文件，避免 Svelte <script> 中不支持 export type 的问题
 */

export interface CityData {
  id: string;
  name: string;
  tier: 'fu' | 'xian';
  x: number;
  y: number;
  days: number;
  desc: string;
  meta: string;
}

export interface TravelSegment {
  from: string;
  to: string;
  days: number;
  round?: number;
}
