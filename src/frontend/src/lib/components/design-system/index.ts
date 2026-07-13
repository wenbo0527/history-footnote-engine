// 设计系统组件导出
// 🆕 v2.10.4-patch 修复：v2.10.3 删除 toast export 引入 4 个组件 import 失败
// 原因：Toast.svelte 是 Svelte 5 runes 文件，用 <script module> 导出 toast
// 旧版 `export { default as Toast, toast } from '...'` 在 Vite/Rollup 解析时
// 不会把 <script module> 的 named export 透传 → 4 个组件 build 失败
// 修复：用 @ts-ignore 拿 <script module> 的 toast named export
// @ts-ignore - svelte 模块类型未暴露 <script module> 的 named export
import ToastModule, { toast } from './Toast.svelte';
export { toast };
export const Toast = ToastModule as any;
export { default as Button } from './Button.svelte';
export { default as Card } from './Card.svelte';
export { default as Dialog } from './Dialog.svelte';
export { default as Spinner } from './Spinner.svelte';
export { default as Seal } from './Seal.svelte';
export { default as Chapter } from './Chapter.svelte';
export { default as Divider } from './Divider.svelte';
export { default as FirstLetter } from './FirstLetter.svelte';
export { default as Tabs } from './Tabs.svelte';
export { default as Reveal } from './Reveal.svelte';
export { default as Skeleton } from './Skeleton.svelte';
export { default as SkipLink } from './SkipLink.svelte';
// 🆕 v2.10.1 W82: Icon 组件
export { default as Icon } from './Icon.svelte';
