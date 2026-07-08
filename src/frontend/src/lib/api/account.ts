/**
 * /api/account/* 账号系统
 *
 * 🆕 v1.7.30: 接入 scrypt 密码 + 邀请码注册
 */
import { call } from './client';

export interface Account {
  account_id: string;
  username: string;
  email?: string;
  role?: string;
  last_login_at?: string;
  created_at?: string;
}

const SESSION_KEY = 'hfe_account_id';
const USERNAME_KEY = 'hfe_account_username';
const INVITE_KEY = 'hfe_invite_code';   // 🆕 v1.7.30: 邀请码暂存

/** 🆕 v1.7.30: 注册（用户名 + 邀请码 + 密码）*/
export async function register(username: string, inviteCode: string, password: string, email?: string): Promise<Account> {
  const trimmed = username.trim();
  if (!trimmed) throw new Error('用户名不能为空');
  if (!inviteCode.trim()) throw new Error('邀请码不能为空');
  if (!password || password.length < 6) throw new Error('密码至少 6 字符');
  const data = await call<Account>('/account/register', {
    body: {
      username: trimmed,
      invite_code: inviteCode.trim(),
      password,
      email
    }
  });
  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, data.account_id);
    localStorage.setItem(USERNAME_KEY, data.username);
    localStorage.setItem(INVITE_KEY, inviteCode.trim());
  }
  return data;
}

/** 🆕 v1.7.30: 登录（用户名 + 密码）*/
export async function login(username: string, password: string): Promise<Account> {
  const trimmed = username.trim();
  if (!trimmed) throw new Error('用户名不能为空');
  if (!password) throw new Error('密码不能为空');
  const data = await call<Account>('/account/login', {
    body: { username: trimmed, password }
  });
  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, data.account_id);
    localStorage.setItem(USERNAME_KEY, data.username);
  }
  return data;
}

/** 获取当前账号信息 */
export async function getAccountInfo(accountId: string): Promise<Account | null> {
  try {
    return await call<Account>('/account/info', {
      method: 'GET',
      query: { account_id: accountId }
    });
  } catch (e) {
    return null;
  }
}

/** 读取本地 account_id */
export function getCurrentAccountId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(SESSION_KEY);
}

/** 读取本地 username */
export function getCurrentUsername(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(USERNAME_KEY);
}

/** 🆕 v1.7.30: 邀请码 */
export function getInviteCode(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(INVITE_KEY);
}
export function setInviteCode(code: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(INVITE_KEY, code);
}

/** 登出 */
export function logout(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(GUEST_KEY);
}

/** 是否已登录 */
export function isLoggedIn(): boolean {
  return !!getCurrentAccountId();
}

/** 访客模式 */
const GUEST_KEY = 'hfe_is_guest';
export function isGuest(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(GUEST_KEY) === '1';
}
export function setGuest(): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(GUEST_KEY, '1');
}
export function clearGuest(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(GUEST_KEY);
}
