"""🆕 v1.7.37 Wiki Tools（LLM 可调用）

将 WikiRetriever 包装为 LangChain Tool，DM Agent 可在 narrative 生成时
主动调用 search_wiki() 检索片段。

工具设计（LangChain @tool 风格）：
- search_wiki(query, intent, city, top_k)
- search_wiki_by_action(action_verb, target, city)

依据用户洞察：
> Wiki 内容是按需注入的，由 LLM 处理
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from history_footnote.wiki_retriever import (
    WikiRetriever,
    WikiFragment,
    get_wiki_retriever,
)


# ============= Tool 函数 =============

def search_wiki(
    query: str,
    intent: str = "",
    city: str = "",
    top_k: int = 3,
) -> dict:
    """检索 Wiki 片段

    Args:
        query: 检索词（玩家输入 / 关键词）
        intent: 意图分类（city/route/gossip/branch/auto）
        city: 城市过滤（suzhou/hangzhou/...）
        top_k: 返回几个片段

    Returns:
        {
          "query": str,
          "fragments": [
            {"title": str, "content": str, "city": str, "category": str, "score": float},
            ...
          ],
          "total": int
        }

    Example:
        >>> search_wiki("搭船去苏州", intent="route", city="suzhou")
        {
          "query": "搭船去苏州",
          "fragments": [
            {"title": "4 城市概览（vs 盛泽）", "content": "...", "city": "suzhou", "score": 1.0},
            ...
          ]
        }
    """
    retriever = get_wiki_retriever()
    # 自动检测 intent（如果未指定）
    if not intent or intent == "auto":
        intent = _auto_detect_intent(query)
    frags = retriever.search(query=query, intent=intent, city=city, top_k=top_k)
    return {
        "query": query,
        "intent": intent,
        "city": city,
        "fragments": [
            {
                "title": f.title,
                "content": f.content,
                "city": f.city,
                "category": f.category,
                "section": f.section,
                "score": round(f.score, 2),
            }
            for f in frags
        ],
        "total": len(frags),
    }


def search_wiki_by_action(
    action_verb: str,
    target: str = "",
    city: str = "",
    top_k: int = 3,
) -> dict:
    """按玩家动作检索 Wiki

    Args:
        action_verb: 动作（TRAVEL/MEET/SELL/BUY/CRAFT/IDLE）
        target: 目标（人物/地点）
        city: 当前城市
        top_k: 返回几个片段

    Returns:
        与 search_wiki 相同结构

    Example:
        >>> search_wiki_by_action("TRAVEL", "suzhou")
    """
    retriever = get_wiki_retriever()
    frags = retriever.search_by_action(action_verb, target=target, city=city, top_k=top_k)
    return {
        "action": action_verb,
        "target": target,
        "city": city,
        "fragments": [
            {
                "title": f.title,
                "content": f.content,
                "city": f.city,
                "category": f.category,
                "section": f.section,
                "score": round(f.score, 2),
            }
            for f in frags
        ],
        "total": len(frags),
    }


def _auto_detect_intent(query: str) -> str:
    """自动检测意图（基于关键词）"""
    query_lower = query.lower()
    # route
    if any(kw in query_lower for kw in ["去", "到", "航", "船", "路", "码头"]):
        return "route"
    # city
    if any(kw in query_lower for kw in ["街", "景象", "感觉", "听", "看", "阊门", "西湖"]):
        return "city"
    # gossip
    if any(kw in query_lower for kw in ["故事", "听说", "传闻", "闲", "聊天", "施润泽", "金瓶梅"]):
        return "gossip"
    return ""


# ============= LangChain 工具注册 =============

def get_wiki_tools():
    """获取 LangChain 工具列表

    Returns:
        list of LangChain tool objects
    """
    try:
        from langchain_core.tools import tool
        @tool
        def wiki_search(query: str, intent: str = "auto", city: str = "", top_k: int = 3) -> dict:
            """搜索万历十五年 Wiki 知识库

            玩家行动时，调用此工具获取相关历史背景、感官描写、闲谈素材。

            Args:
                query: 检索词，如"搭船去苏州"、"盛泽丝市"、"施润泽故事"
                intent: 意图分类（auto/city/route/gossip/branch）
                city: 城市过滤，如"苏州"、"杭州"、"盛泽"
                top_k: 返回几个片段（1-5）

            Returns:
                {
                  "fragments": [{"title": str, "content": str, "city": str, "score": float}],
                  "total": int
                }
            """
            return search_wiki(query=query, intent=intent, city=city, top_k=top_k)

        @tool
        def wiki_search_by_action(action_verb: str, target: str = "", city: str = "", top_k: int = 3) -> dict:
            """按玩家动作搜索 Wiki

            当玩家执行动作（去某地/见某人/买东西/闲聊）时，调用此工具获取相关历史背景。

            Args:
                action_verb: 动作类型（TRAVEL/MEET/SELL/BUY/CRAFT/IDLE）
                target: 目标（城市/人物/物品）
                city: 当前所在城市
                top_k: 返回几个片段

            Returns:
                {
                  "fragments": [{"title": str, "content": str, "city": str, "score": float}],
                  "total": int
                }
            """
            return search_wiki_by_action(action_verb=action_verb, target=target, city=city, top_k=top_k)

        return [wiki_search, wiki_search_by_action]
    except ImportError:
        return []


# ============= 工具描述（给 LLM 的工具说明）============

WIKI_TOOL_DESCRIPTION = """
你有以下 Wiki 检索工具可用：

1. **wiki_search(query, intent, city, top_k)**
   - 用于在玩家执行动作前，搜索相关历史背景
   - 何时调用：玩家"去某地"、"听到/看到某事"、"想了解历史"时
   - 不要每次都调用：除非需要细节，否则保留 LLM 自由发挥

2. **wiki_search_by_action(action_verb, target, city, top_k)**
   - 按玩家动作类型自动选择检索策略
   - 何时调用：玩家输入动作后，DM 需要丰富叙事细节时

调用示例：
- 玩家"搭船去苏州" → wiki_search_by_action("TRAVEL", "suzhou", "shengze")
- 玩家"我听张婶说最近织工闹事" → wiki_search("织工闹事", intent="gossip", city="shengze")
- 玩家"我想知道阊门码头什么样" → wiki_search("阊门码头", intent="city", city="suzhou")

**重要**：Wiki 是按需注入，不是全量。LLM 自由发挥时不要机械调用。
"""


# ============= 烟雾测试 =============

if __name__ == "__main__":
    print("=== search_wiki 烟雾测试 ===\n")
    # 1. 苏州离乡
    print("--- search_wiki('搭船去苏州', intent='route', city='suzhou') ---")
    result = search_wiki("搭船去苏州", intent="route", city="suzhou", top_k=2)
    print(f"  query={result['query']}, intent={result['intent']}, total={result['total']}")
    for f in result["fragments"]:
        print(f"  [{f['score']}] {f['title']} ({f['city']}/{f['category']})")
        print(f"    {f['content'][:150]}...")

    # 2. 卖绸
    print("\n--- search_wiki_by_action('SELL', city='shengze') ---")
    result = search_wiki_by_action("SELL", city="shengze")
    for f in result["fragments"]:
        print(f"  [{f['score']}] {f['title']} ({f['city']}/{f['category']})")
        print(f"    {f['content'][:150]}...")

    # 3. 自动意图
    print("\n--- search_wiki('听说施润泽的故事') (auto intent) ---")
    result = search_wiki("听说施润泽的故事", intent="auto", top_k=2)
    print(f"  intent={result['intent']}, total={result['total']}")
    for f in result["fragments"]:
        print(f"  [{f['score']}] {f['title']} ({f['city']}/{f['category']})")

    # 4. LangChain 工具
    print("\n--- get_wiki_tools() ---")
    tools = get_wiki_tools()
    print(f"  获取 {len(tools)} 个 LangChain 工具")
    for t in tools:
        print(f"    - {t.name}: {t.description[:80]}...")
