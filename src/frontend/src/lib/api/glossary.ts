/**
 * /api/glossary - 词条查询
 *
 * 🆕 v1.7.30: 对齐后端（query 字符串 → 搜索结果 / term 单字 → 详情）
 */
import { call } from './client';
import type { GlossaryResponse, GlossaryTerm } from './types';

export async function queryGlossary(query: string, sessionId?: string): Promise<GlossaryResponse> {
  return call<GlossaryResponse>('/glossary', {
    body: { query: query.trim(), session_id: sessionId }
  });
}

/** 单个词条详情（key, category, definition, example, related, html）*/
export interface TermDetail {
  key: string;
  category: string;
  definition: string;
  example: string;
  related: string[];
  html: string;
}

export async function getTerm(termKey: string): Promise<TermDetail | null> {
  try {
    return await call<TermDetail>('/glossary', {
      body: { term: termKey }
    });
  } catch (e) {
    return null;
  }
}
