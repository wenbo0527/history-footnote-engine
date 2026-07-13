/**
 * 🆕 v2.10.3 unwrap 工具 + mapper 类型守卫单元测试
 */
import { describe, it, expect } from 'vitest';
import { unwrap, unwrapAs, pick } from './unwrap';

describe('unwrap', () => {
  it('透传 non-null 值', () => {
    const obj = { a: 1 };
    expect(unwrap(obj)).toBe(obj);
  });

  it('透传 null/undefined（运行时 noop）', () => {
    expect(unwrap(null)).toBe(null);
    expect(unwrap(undefined)).toBe(undefined);
  });
});

describe('unwrapAs', () => {
  it('强制类型断言', () => {
    const v = unwrapAs<{ x: number }>({ x: 42 });
    expect(v.x).toBe(42);
  });

  it('运行时仍是 noop（不会抛）', () => {
    expect(() => unwrapAs<unknown>(null)).not.toThrow();
  });
});

describe('pick', () => {
  const obj = {
    a: { b: { c: 'deep value' } },
    list: [{ name: 'first' }, { name: 'second' }],
  };

  it('读嵌套字段', () => {
    expect(pick(obj, 'a.b.c')).toBe('deep value');
  });

  it('读数组下标（不支持，会变 undefined）', () => {
    // pick 用 '.' split，数组下标需要 'list.0.name'
    expect(pick(obj, 'list.0.name')).toBe('first');
  });

  it('fallback 缺失字段', () => {
    expect(pick(obj, 'a.b.missing', 'fallback')).toBe('fallback');
  });

  it('null 输入返回 fallback', () => {
    expect(pick(null, 'a.b', 'fb')).toBe('fb');
  });

  it('undefined 输入返回 fallback', () => {
    expect(pick(undefined, 'a.b', 'fb')).toBe('fb');
  });

  it('中间路径断裂返回 fallback', () => {
    expect(pick(obj, 'a.x.y.z', 'fb')).toBe('fb');
  });

  it('空字符串路径返回 fallback', () => {
    expect(pick(obj, '', 'fb')).toBe('fb');
  });
});