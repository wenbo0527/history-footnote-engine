"""🆕 v1.9.4 双层缓存（公共层 + 玩家层）静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LLM_CACHE = ROOT / "src/history_footnote/llm_cache.py"
MISC = ROOT / "src/history_footnote/web_server/routers/misc.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_cache_module():
    """缓存模块双层设计"""
    print("[1/4] 缓存模块双层设计")
    src = LLM_CACHE.read_text(encoding="utf-8")
    ok = True
    ok = _step("  make_player_key 玩家层键", "def make_player_key" in src and "account_id" in src) and ok
    ok = _step("  get() 接收 account_id", "account_id: str = \"\"" in src) and ok
    ok = _step("  玩家层优先（先 player:）", "先玩家层" in src or "account_id" in src) and ok
    ok = _step("  公共层 fallback", "公共层" in src) and ok
    ok = _step("  find_similar 双层", "similar_player:" in src and "similar_public:" in src) and ok
    ok = _step("  find_latest 双层", "latest_player" in src and "latest_public" in src) and ok
    ok = _step("  put() 玩家层 + 公共层", '"type": "public"' in src and '"type": "player"' in src) and ok
    ok = _step("  player: prefix 区分", "player:" in src) and ok
    return ok


def test_player_isolation():
    """玩家隔离：不同玩家不命中对方缓存"""
    print("\n[2/4] 玩家隔离（不同玩家不命中）")
    sys.path.insert(0, str(ROOT / "src"))
    # 清空
    cache_path = ROOT / "saves/llm_cache.json"
    if cache_path.exists():
        cache_path.unlink()
    from history_footnote import llm_cache
    ok = True
    # 玩家 A 写
    llm_cache.put("wanli1587", "male", "盛泽镇", "织工", "学手艺",
                  {"name": "沈织户A"}, "raw A", account_id="player_A")
    # 玩家 A 查（应精确命中玩家层）
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工", "学手艺", account_id="player_A")
    ok = _step("  玩家 A 查自己", c is not None and c["character"]["name"] == "沈织户A" and c.get("cache_hit") == "exact_player") and ok
    # 玩家 B 查（应命中公共层，不是玩家 A 的）
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工", "学手艺", account_id="player_B")
    ok = _step(f"  玩家 B 查同样 prompt，命中公共层（cache_hit={c.get('cache_hit', '?') if c else 'None'}）", c is not None and c["character"]["name"] == "沈织户A" and c.get("cache_hit") == "exact_public") and ok
    # 玩家 B 写
    llm_cache.put("wanli1587", "male", "盛泽镇", "织工", "学手艺",
                  {"name": "沈织户B"}, "raw B", account_id="player_B")
    # 玩家 A 查（仍应是自己）
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工", "学手艺", account_id="player_A")
    ok = _step("  玩家 A 仍是自己（不被 B 污染）", c is not None and c["character"]["name"] == "沈织户A") and ok
    # 玩家 B 查（应是自己）
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工", "学手艺", account_id="player_B")
    ok = _step("  玩家 B 现在是自己", c is not None and c["character"]["name"] == "沈织户B") and ok
    return ok


def test_misc_integration():
    """misc.py 集成 account_id"""
    print("\n[3/4] misc.py 集成 account_id")
    src = MISC.read_text(encoding="utf-8")
    ok = True
    ok = _step("  account_id 从 query 取", 'qs.get("account_id"' in src and "parse_qs" in src) and ok
    ok = _step("  account_id 从 body 取", 'body.get("account_id"' in src) and ok
    ok = _step("  cache_get 传 account_id", "cache_get(era_id, gender, location, identity_desc, life_exp, account_id=account_id)" in src) and ok
    ok = _step("  cache_put 传 account_id", "cache_put(era_id, gender, location, identity_desc, life_exp, parsed, resp.content, account_id=account_id)" in src) and ok
    ok = _step("  find_similar 传 account_id", "find_similar(era_id, gender, location, identity_desc, life_exp, account_id=account_id)" in src) and ok
    ok = _step("  find_latest 传 account_id", "find_latest(era_id, account_id=account_id)" in src) and ok
    return ok


def test_scenarios():
    """3 场景：玩家 A 重复/玩家 B 命中公共层/同玩家模糊"""
    print("\n[4/4] 场景验证")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote import llm_cache
    cache_path = ROOT / "saves/llm_cache.json"
    if cache_path.exists():
        cache_path.unlink()
    ok = True
    # 场景 1: 玩家 A 第一次
    llm_cache.put("wanli1587", "male", "盛泽镇", "织工学徒", "学手艺",
                  {"name": "沈三A"}, "raw", account_id="player_A")
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工学徒", "学手艺", account_id="player_A")
    ok = _step("  场景1: 玩家A 精确命中", c is not None and c["character"]["name"] == "沈三A") and ok
    # 场景 2: 玩家 B 第一次（应命中公共层）
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工学徒", "学手艺", account_id="player_B")
    ok = _step(f"  场景2: 玩家B 首次，命中公共层 cache_hit={c.get('cache_hit', '?') if c else 'None'}", c is not None and c["character"]["name"] == "沈三A" and "public" in c.get("cache_hit", "")) and ok
    # 场景 3: 玩家 B 写自己的
    llm_cache.put("wanli1587", "male", "盛泽镇", "织工学徒", "学手艺",
                  {"name": "沈三B"}, "raw", account_id="player_B")
    c = llm_cache.get("wanli1587", "male", "盛泽镇", "织工学徒", "学手艺", account_id="player_B")
    ok = _step("  场景3: 玩家B 写后再查，是自己", c is not None and c["character"]["name"] == "沈三B") and ok
    return ok


if __name__ == "__main__":
    print("=== v1.9.4 双层缓存 静态测试 ===\n")
    ok1 = test_cache_module()
    ok2 = test_player_isolation()
    ok3 = test_misc_integration()
    ok4 = test_scenarios()
    if all([ok1, ok2, ok3, ok4]):
        print("\n🎉 4 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=}")
        sys.exit(1)
