/**
 * Session 状态 - 登录态、用户信息
 */
import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';

export interface Session {
  username: string;
  sessionId: string | null;
  isLoggedIn: boolean;
}

const STORAGE_KEY = 'hfe_session';

function loadInitial(): Session {
  if (!browser) return { username: '', sessionId: null, isLoggedIn: false };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return { username: '', sessionId: null, isLoggedIn: false };
}

export const session: Writable<Session> = writable(loadInitial());

// 自动持久化
if (browser) {
  session.subscribe((s) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch { /* ignore */ }
  });
}

export const sessionActions = {
  login(username: string, sessionId: string | null = null) {
    session.set({ username, sessionId, isLoggedIn: true });
  },
  logout() {
    session.set({ username: '', sessionId: null, isLoggedIn: false });
  }
};
