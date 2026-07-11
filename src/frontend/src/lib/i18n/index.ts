/**
 * 🆕 v2.10.x W52: 最小 i18n 框架
 *
 * - locale store (zh-CN / en-US)
 * - t(key) 翻译函数
 * - 嵌套字典（nav.main.game）
 * - localStorage 持久化
 * - 不引入重型库（轻量 ~100 行）
 *
 * 用法：
 *   import { t, locale, setLocale } from '$lib/i18n';
 *   <p>{t('nav.main.game')}</p>  // zh: "游戏" / en: "Game"
 *   <button onclick={() => setLocale('en-US')}>English</button>
 */
import { writable, type Writable, get } from 'svelte/store';

import { zh_CN } from './locales/zh-CN';
import { en_US } from './locales/en-US';

export type Locale = 'zh-CN' | 'en-US';

export const SUPPORTED_LOCALES: Locale[] = ['zh-CN', 'en-US'];

export const LOCALE_LABELS: Record<Locale, string> = {
  'zh-CN': '中文',
  'en-US': 'English',
};

export const LOCALE_FLAGS: Record<Locale, string> = {
  'zh-CN': '🇨🇳',
  'en-US': '🇺🇸',
};

const DICTS: Record<Locale, Record<string, string>> = {
  'zh-CN': zh_CN,
  'en-US': en_US,
};

const STORAGE_KEY = 'hfe_locale';

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function loadInitial(): Locale {
  if (!isBrowser()) return 'zh-CN';
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'zh-CN' || raw === 'en-US') return raw;
  } catch { /* ignore */ }
  // fallback: 浏览器语言
  if (isBrowser() && navigator.language?.startsWith('en')) return 'en-US';
  return 'zh-CN';
}

export const locale: Writable<Locale> = writable(loadInitial());

// 持久化
if (isBrowser()) {
  locale.subscribe((l) => {
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch { /* ignore */ }
  });
}

export function setLocale(l: Locale): void {
  locale.set(l);
}

/**
 * 翻译函数：t('nav.main.game') → "游戏" or "Game"
 * - 找不到 key 返原 key（不抛错）
 * - 支持 {var} 占位符插值
 */
export function t(key: string, vars?: Record<string, string | number>): string {
  const current = get(locale); // 同步取当前值
  const dict = DICTS[current] || {};
  let text = dict[key] || key;

  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
  }
  return text;
}

/**
 * 同步 t 函数（接收 locale 参数）
 * 用于组件外（不能在 $effect 中调 t()）
 */
export function tSync(key: string, current: Locale, vars?: Record<string, string | number>): string {
  const dict = DICTS[current] || {};
  let text = dict[key] || key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
  }
  return text;
}
