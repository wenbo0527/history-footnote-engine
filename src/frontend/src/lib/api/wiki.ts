/**
 * /api/character_wiki - 角色关系 Wiki (GET)
 *
 * 🆕 v1.7.30: 后端返回 {session_id, wiki}, 转换为前端 {markdown, characters, updated_at}
 */
import { call } from './client';
import type { WikiResponse, WikiCharacter } from './types';

export async function getCharacterWiki(sessionId: string): Promise<WikiResponse> {
  const raw = await call<{ session_id: string; wiki: Record<string, any> }>('/character_wiki', {
    method: 'GET',
    query: { session_id: sessionId }
  });

  // 转换 wiki dict → 前端期望格式
  const wiki = raw.wiki ?? {};
  const characters: WikiCharacter[] = Object.entries(wiki).map(([name, info]: [string, any]) => ({
    name,
    relation: info?.relation ?? '未知',
    age: info?.age,
    description: info?.description ?? info?.note ?? '',
    portrait: info?.portrait
  }));

  // 渲染 markdown（简单格式化）
  const markdown = characters.length === 0
    ? '暂无人物档案。\n\n游戏开始后遇到的人物会在这里出现。'
    : characters.map(c => `## ${c.name}\n\n- **身份**: ${c.relation}\n${c.age ? `- **年龄**: ${c.age}岁\n` : ''}- **介绍**: ${c.description}`).join('\n\n');

  return {
    markdown,
    characters,
    updated_at: new Date().toISOString(),
    raw_wiki: wiki
  };
}
