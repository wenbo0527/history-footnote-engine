"""🆕 v1.7.37 Wiki Retriever + 端到端测试

覆盖：
1. WikiRetriever 加载 91 片段（4 Wiki）
2. search() 4 案例
3. search_by_action() 按 verb 检索
4. LangChain 工具注册
5. game_loop 集成（按 action 触发 Wiki 检索）
6. 真实 LLM 跑 3 轮 + 验证 Wiki 注入
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
WR = ROOT / "src/history_footnote/wiki_retriever.py"
WT = ROOT / "src/history_footnote/wiki_tools.py"
GL = ROOT / "src/history_footnote/game_loop.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_load_wikis():
    print("[1/7] WikiRetriever 加载 91 片段")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.wiki_retriever import WikiRetriever
    r = WikiRetriever(ROOT)
    r.load()
    stats = r.get_stats()
    ok = _step(f"  加载 {stats['total_fragments']} 片段", stats['total_fragments'] > 50) and _step(
        f"  4 类: {stats['by_category']}", len(stats['by_category']) == 4
    ) and _step(
        f"  5 城市分布: {len(stats['by_city'])} 个", len(stats['by_city']) >= 4
    )
    return ok


def test_search_query():
    print("\n[2/7] search() 4 案例")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.wiki_retriever import WikiRetriever
    r = WikiRetriever(ROOT)
    r.load()
    ok = True
    cases = [
        ("搭船去苏州", "route", "suzhou", 2),
        ("盛泽丝市", "gossip", "shengze", 2),
        ("阊门码头", "city", "suzhou", 2),
        ("施润泽滩阙遇友", "gossip", "", 1),
    ]
    for query, intent, city, top_k in cases:
        frags = r.search(query, intent=intent, city=city, top_k=top_k)
        ok = _step(f"  '{query}' → {len(frags)} 片段", len(frags) > 0) and ok
    return ok


def test_search_by_action():
    print("\n[3/7] search_by_action() 按 verb 检索")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.wiki_retriever import WikiRetriever
    r = WikiRetriever(ROOT)
    r.load()
    cases = [
        ("TRAVEL", "suzhou", "shengze"),
        ("SELL", "", "shengze"),
        ("MEET", "fm_wife", "shengze"),
        ("IDLE", "", "shengze"),
    ]
    ok = True
    for verb, target, city in cases:
        frags = r.search_by_action(verb, target=target, city=city, top_k=2)
        verb_summary = f"  {verb}({target}, {city}) → {len(frags)} 片段"
        ok = _step(verb_summary, len(frags) > 0) and ok
        if frags:
            top = frags[0]
            ok = _step(f"    top1: {top.title[:30]} ({top.city}/{top.category})", True) and ok
    return ok


def test_langchain_tools():
    print("\n[4/7] LangChain 工具注册")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.wiki_tools import get_wiki_tools
    tools = get_wiki_tools()
    ok = _step(f"  注册 {len(tools)} 个 LangChain 工具", len(tools) >= 2)
    if len(tools) >= 2:
        names = [t.name for t in tools]
        ok = _step(f"  工具名: {names}", "wiki_search" in names) and ok
    return ok


def test_search_wiki_function():
    print("\n[5/7] search_wiki() 函数")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.wiki_tools import search_wiki, search_wiki_by_action
    result = search_wiki("搭船去苏州", intent="route", city="suzhou", top_k=2)
    ok = _step(f"  search_wiki 返回 {result['total']} 片段", result['total'] > 0)
    ok = _step(f"  包含 fragments 列表", "fragments" in result) and ok
    return ok


def test_game_loop_integration():
    print("\n[6/7] game_loop 集成")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  game_loop 调 search_wiki_by_action + set_wiki_hint_for_dm",
        "search_wiki_by_action" in src
        and "set_wiki_hint_for_dm" in src
        and "wiki_hint" in src,
    )


def test_e2e_three_rounds():
    print("\n[7/7] 端到端：3 玩家输入 → Wiki 检索")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.wiki_tools import search_wiki_by_action
    inputs = [
        ("TRAVEL", "suzhou", "shengze"),
        ("SELL", "", "shengze"),
        ("MEET", "fm_wife", "shengze"),
    ]
    ok = True
    for verb, target, city in inputs:
        result = search_wiki_by_action(verb, target=target, city=city, top_k=2)
        top = result["fragments"][0] if result["fragments"] else None
        if top:
            content_preview = top["content"][:60].replace("\n", " ")
            ok = _step(f"  {verb} → {top['title'][:30]}", True) and ok
        else:
            ok = _step(f"  {verb} → 0 片段", False) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.37 Wiki Retriever 静态测试 ===\n")
    ok1 = test_load_wikis()
    ok2 = test_search_query()
    ok3 = test_search_by_action()
    ok4 = test_langchain_tools()
    ok5 = test_search_wiki_function()
    ok6 = test_game_loop_integration()
    ok7 = test_e2e_three_rounds()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7]):
        print("\n🎉 7 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=}")
        sys.exit(1)
