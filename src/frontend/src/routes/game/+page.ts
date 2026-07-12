/**
 * Game 页: 纯客户端渲染
 *
 * 🆕 v2.10.2 W52 followup: 强制 ssr=false
 * 原因:
 * - Game 页面挂载 5 个 Modal + PlateMap + CharCard,所有依赖 $game store
 * - $game 由 onMount 调 /api/state 填充,SSR 时 $game 为 null
 * - 之前强制 SSR 会渲染空 Modal,某些 template 引用 undefined 字段 → 500
 * - 改为 client-only 后,SSR 直接跳过,避免任何 SSR 渲染错误
 */
export const ssr = false;
export const prerender = false;
