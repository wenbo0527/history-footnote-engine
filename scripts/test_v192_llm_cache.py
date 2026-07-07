"""🆕 v1.9.2 LLM 缓存 + 降级 端到端测试

测试 3 场景：
1. 精确缓存命中（同 body 重复请求，cache_hit=exact）
2. 模糊缓存命中（关键词 60% 相似，cache_hit=similar:X.XX）
3. 兜底（同 era 最新一条）
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8765"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def post(path, body, timeout=180):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8")), time.time() - t0
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8")), time.time() - t0
        except Exception:
            return e.code, {"error": e.reason}, time.time() - t0


def test_module_functions():
    """测试 1: 缓存模块函数"""
    print("\n[1/3] 缓存模块函数")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.llm_cache import make_key, get, put, find_similar, find_latest, stats
    ok = True
    # 1. 写
    test_char = {"name": "测试沈三", "age": 30, "occupation": "织工"}
    put("wanli1587", "male", "盛泽镇", "织工", "学手艺", test_char, "raw content")
    ok = _step("  put() 成功", True) and ok
    # 2. 精确读
    cached = get("wanli1587", "male", "盛泽镇", "织工", "学手艺")
    ok = _step("  精确命中 get()", cached is not None and cached["character"]["name"] == "测试沈三") and ok
    # 3. 模糊（同关键词更多）
    similar = find_similar("wanli1587", "male", "盛泽镇", "织工学徒想学手艺", "学手艺养家")
    ok = _step(f"  模糊命中 find_similar() {similar.get('cache_hit', 'miss') if similar else 'None'}", similar is not None and "similar" in similar.get("cache_hit", "")) and ok
    # 4. 兜底
    latest = find_latest("wanli1587")
    ok = _step("  兜底 find_latest()", latest is not None and latest["character"]["name"] == "测试沈三") and ok
    # 5. stats
    s = stats()
    ok = _step(f"  stats() size={s['size']}", s["size"] >= 1) and ok
    return ok


def test_api_first_call_miss():
    """测试 2: 首次调用 LLM（miss 写缓存）"""
    print("\n[2/3] 首次调用 LLM（写缓存）")
    body = {
        "era_id": "wanli1587",
        "gender": "male",
        "location": "盛泽镇",
        "location_description": "测试缓存",
        "identity_description": "织工学徒",
        "life_expectation": "学手艺",
    }
    status, resp, elapsed = post("/api/generate_character", body)
    if status == 200 and resp.get("character"):
        return _step(f"  HTTP 200 {elapsed:.1f}s cache_hit={resp.get('cache_hit')}", resp.get("cache_hit") == "miss")
    else:
        return _step(f"  HTTP {status} 错误", False, str(resp.get("error", "?"))[:60])


def test_api_second_call_hit():
    """测试 3: 重复调用（精确命中）"""
    print("\n[3/3] 重复调用（精确命中）")
    body = {
        "era_id": "wanli1587",
        "gender": "male",
        "location": "盛泽镇",
        "location_description": "测试缓存",
        "identity_description": "织工学徒",
        "life_expectation": "学手艺",
    }
    status, resp, elapsed = post("/api/generate_character", body)
    if status == 200 and resp.get("character"):
        return _step(f"  HTTP 200 {elapsed:.1f}s cache_hit={resp.get('cache_hit')}", resp.get("cache_hit") == "exact")
    else:
        return _step(f"  HTTP {status} 错误", False, str(resp.get("error", "?"))[:60])


def main():
    print("=" * 60)
    print("v1.9.2 LLM 缓存 + 降级 端到端测试")
    print("=" * 60)
    ok1 = test_module_functions()
    ok2 = test_api_first_call_miss()
    ok3 = test_api_second_call_hit()
    print("\n" + "=" * 60)
    if all([ok1, ok2, ok3]):
        print("🎉 v1.9.2 3 场景全过：模块 / miss / exact 命中")
        return 0
    else:
        print(f"❌ 部分失败：ok1={ok1} ok2={ok2} ok3={ok3}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
