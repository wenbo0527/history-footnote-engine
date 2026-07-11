/**
 * 🆕 v2.10.x W52: i18n 框架测试
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';

import {
  locale,
  setLocale,
  t,
  tSync,
  SUPPORTED_LOCALES,
  LOCALE_LABELS,
  LOCALE_FLAGS,
} from './index';

describe('W52: i18n 框架', () => {
  beforeEach(() => {
    setLocale('zh-CN');
  });

  it('locale store 默认 zh-CN', () => {
    expect(get(locale)).toBe('zh-CN');
  });

  it('setLocale 切换 locale', () => {
    setLocale('en-US');
    expect(get(locale)).toBe('en-US');
  });

  it('SUPPORTED_LOCALES 含 2 个 locale', () => {
    expect(SUPPORTED_LOCALES).toContain('zh-CN');
    expect(SUPPORTED_LOCALES).toContain('en-US');
  });

  it('LOCALE_LABELS 字典正确', () => {
    expect(LOCALE_LABELS['zh-CN']).toBe('中文');
    expect(LOCALE_LABELS['en-US']).toBe('English');
  });

  it('LOCALE_FLAGS 字典正确', () => {
    expect(LOCALE_FLAGS['zh-CN']).toBe('🇨🇳');
    expect(LOCALE_FLAGS['en-US']).toBe('🇺🇸');
  });
});

describe('t() 翻译函数', () => {
  beforeEach(() => {
    setLocale('zh-CN');
  });

  it('zh-CN 翻译存在 key', () => {
    expect(t('nav.main.game')).toBe('游戏');
  });

  it('en-US 翻译存在 key', () => {
    setLocale('en-US');
    expect(t('nav.main.game')).toBe('Game');
  });

  it('zh-CN 嵌套 key', () => {
    expect(t('plate.title')).toBe('板块格局');
  });

  it('en-US 嵌套 key', () => {
    setLocale('en-US');
    expect(t('plate.title')).toBe('Plate Map');
  });

  it('找不到 key 返原 key', () => {
    expect(t('non.existent.key')).toBe('non.existent.key');
  });

  it('占位符插值', () => {
    setLocale('zh-CN');
    expect(t('chapter.label', { n: 5 })).toBe('第 5 章');
  });

  it('英文占位符插值', () => {
    setLocale('en-US');
    expect(t('chapter.label', { n: 3 })).toBe('Chapter 3');
  });

  it('多个占位符', () => {
    setLocale('zh-CN');
    expect(t('chapter.duration', { n: 8 })).toBe('8 轮');
  });

  it('switch locale 动态更新', () => {
    setLocale('zh-CN');
    expect(t('common.save')).toBe('保存');
    setLocale('en-US');
    expect(t('common.save')).toBe('Save');
  });
});

describe('tSync() 同步翻译', () => {
  it('明确 locale 翻译', () => {
    expect(tSync('nav.main.game', 'zh-CN')).toBe('游戏');
    expect(tSync('nav.main.game', 'en-US')).toBe('Game');
  });

  it('tSync 占位符', () => {
    expect(tSync('chapter.label', 'en-US', { n: 7 })).toBe('Chapter 7');
  });

  it('tSync 找不到 key 返原 key', () => {
    expect(tSync('non.existent', 'zh-CN')).toBe('non.existent');
  });
});

describe('4 状态色翻译', () => {
  beforeEach(() => setLocale('zh-CN'));

  it('plate 4 状态 zh', () => {
    expect(t('plate.status.stable')).toBe('稳定');
    expect(t('plate.status.tense')).toBe('紧张');
    expect(t('plate.status.shifting')).toBe('变化');
    expect(t('plate.status.collapsed')).toBe('崩溃');
  });

  it('plate 4 状态 en', () => {
    setLocale('en-US');
    expect(t('plate.status.stable')).toBe('Stable');
    expect(t('plate.status.tense')).toBe('Tense');
    expect(t('plate.status.shifting')).toBe('Shifting');
    expect(t('plate.status.collapsed')).toBe('Collapsed');
  });
});
