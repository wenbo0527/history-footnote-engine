"""🆕 v1.9.3 token 优化（A Prompt Caching + C Era Cache + E Narrative Cache）"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MISC = ROOT / "src/history_footnote/web_server/routers/misc.py"
LLM_CACHE = ROOT / "src/history_footnote/llm_cache.py"
RESOURCE_CACHE = ROOT / "src/history_footnote/resource_cache.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_prompt_caching():
    print("[1/4] A. Prompt Caching 静态 prefix")
    src = MISC.read_text(encoding="utf-8")
    ok = True
    ok = _step("  STATIC_SYSTEM_PROMPT 常量", "STATIC_SYSTEM_PROMPT = " in src) and ok
    ok = _step("  注释：Prompt Caching", "🆕 v1.9.3 Prompt Caching" in src) and ok
    ok = _step("  SystemMessage 用 STATIC_SYSTEM_PROMPT", "SystemMessage(content=STATIC_SYSTEM_PROMPT)" in src) and ok
    return ok


def test_era_cache():
    print("\n[2/4] C. Era Config Cache")
    src = RESOURCE_CACHE.read_text(encoding="utf-8")
    ok = True
    ok = _step("  _ERA_CONFIGS_CACHE 字典", "_ERA_CONFIGS_CACHE" in src) and ok
    ok = _step("  _ERA_CONFIGS_LOCK 锁", "_ERA_CONFIGS_LOCK" in src) and ok
    ok = _step("  load_era_config 缓存", "if era_id in _ERA_CONFIGS_CACHE" in src) and ok
    ok = _step("  warm_era_configs 预热", "warm_era_configs" in src) and ok
    return ok


def test_narrative_cache():
    print("\n[3/4] E. Narrative Cache 3 级")
    src = LLM_CACHE.read_text(encoding="utf-8")
    ok = True
    ok = _step("  get_narrative 函数", "def get_narrative(action_key: str)" in src) and ok
    ok = _step("  put_narrative 函数", "def put_narrative(action_key: str, narrative: str)" in src) and ok
    ok = _step("  make_narrative_key 函数", "def make_narrative_key(state_dict: dict, player_input: str)" in src) and ok
    ok = _step("  缓存键 prefix narr:", 'f"narr:' in src) and ok
    ok = _step("  缓存限制 500 条", "if len(cache) > 500" in src) and ok
    return ok


def test_module_import():
    print("\n[4/4] 模块导入 + 缓存功能")
    sys.path.insert(0, str(ROOT / "src"))
    ok = True
    try:
        from history_footnote.llm_cache import (
            get_narrative, put_narrative, make_narrative_key,
            get as cache_get, put as cache_put,
            find_similar, find_latest, stats,
        )
        ok = _step("  llm_cache 函数可导入", True) and ok
        # 测 narrative 缓存
        state = {"current_round": 5, "current_city": "苏州府", "character": {"occupation": "织工"}}
        key = make_narrative_key(state, "问行情")
        put_narrative(key, "机户王掌柜说：'今年行情不好，绸缎滞销...'")
        cached = get_narrative(key)
        ok = _step("  narrative 写入+读取", cached is not None and "王掌柜" in cached["narrative"]) and ok
        # 测 character 缓存
        cache_put("wanli1587", "male", "盛泽镇", "织工", "学手艺", {"name": "沈三"}, "raw")
        c = cache_get("wanli1587", "male", "盛泽镇", "织工", "学手艺")
        ok = _step("  character 缓存仍工作", c is not None and c["character"]["name"] == "沈三") and ok
        s = stats()
        ok = _step(f"  stats size={s['size']} ≥ 2", s["size"] >= 2) and ok
    except Exception as e:
        ok = _step(f"  模块导入失败", False, str(e)[:80]) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.9.3 token 优化（A+C+E）静态测试 ===\n")
    ok1 = test_prompt_caching()
    ok2 = test_era_cache()
    ok3 = test_narrative_cache()
    ok4 = test_module_import()
    if all([ok1, ok2, ok3, ok4]):
        print("\n🎉 4 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=}")
        sys.exit(1)
