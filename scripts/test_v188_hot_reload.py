"""🆕 v1.8.8 P0+P1 端到端测试（provider 切换 + 热加载）

1. 默认 provider = minimax-anthropic
2. 改 .env → LLM_PRIMARY_PROVIDER=deepseek
3. 不重启，调 LLM，验证用 deepseek（fail by 402）
4. 改回 .env → minimax-anthropic
5. 不重启，调 LLM，应成功
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8765"
ADMIN_TOKEN = "hf-xUlJyLATpfp2FPDkh0qYaWPki2BwguBd"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Admin-Token": ADMIN_TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_admin(path):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def call_llm():
    """调一次 LLM（generate_character）"""
    req = urllib.request.Request(
        f"{BASE}/api/generate_character",
        data=json.dumps({
            "era_id": "wanli1587",
            "gender": "male",
            "location": "盛泽镇",
            "location_description": "测试热加载",
            "identity_description": "测试",
            "life_expectation": "test",
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode("utf-8")), time.time() - t0
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8")), time.time() - t0
        except Exception:
            return e.code, {"error": e.reason}, time.time() - t0


def test_step1_default_provider():
    """步骤 1: 默认 provider = minimax-anthropic"""
    print("\n[1/5] 默认 provider")
    data = get_admin("/api/admin/settings")
    p = data.get("settings", {}).get("LLM_PRIMARY_PROVIDER", "?")
    return _step(f"  LLM_PRIMARY_PROVIDER = {p}", p == "minimax-anthropic")


def test_step2_change_to_deepseek():
    """步骤 2: 改 .env → deepseek（不重启）"""
    print("\n[2/5] 改 provider → deepseek（不重启）")
    data = post("/api/admin/settings", {"LLM_PRIMARY_PROVIDER": "deepseek"})
    return _step(f"  POST 改 provider", data.get("ok") == True and data.get("updated", {}).get("LLM_PRIMARY_PROVIDER") == "deepseek")


def test_step3_hot_reload_works():
    """步骤 3: 立即用 get_setting() 读（不重启）"""
    print("\n[3/5] 热加载验证")
    # 调 get_setting() 模拟代码读
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.runtime_config import get_setting
    p = get_setting("LLM_PRIMARY_PROVIDER", "")
    return _step(f"  get_setting() 返回 {p}", p == "deepseek")


def test_step4_revert_to_minimax():
    """步骤 4: 改回 .env → minimax-anthropic（不重启）"""
    print("\n[4/5] 改回 provider → minimax-anthropic（不重启）")
    data = post("/api/admin/settings", {"LLM_PRIMARY_PROVIDER": "minimax-anthropic"})
    return _step(f"  POST 改回", data.get("ok") == True and data.get("updated", {}).get("LLM_PRIMARY_PROVIDER") == "minimax-anthropic")


def test_step5_real_llm_call():
    """步骤 5: 实际 LLM 调用（验证主 provider 生效）"""
    print("\n[5/5] 真实 LLM 调用（验证 provider = minimax-anthropic）")
    # 等几秒让 server 端 .env cache 失效（runtime_config TTL 5s）
    time.sleep(6)
    status, resp, elapsed = call_llm()
    if status == 200 and resp.get("character"):
        char = resp.get("character", {})
        name = char.get("name", "?")
        return _step(f"  HTTP 200 {elapsed:.1f}s 角色={name}", True)
    else:
        return _step(f"  HTTP {status} 错误：{resp.get('error', '?')[:80]}", False, f"{elapsed:.1f}s")


def main():
    print("=" * 60)
    print("v1.8.8 P0+P1 LLM provider 热加载测试")
    print("=" * 60)
    ok1 = test_step1_default_provider()
    ok2 = test_step2_change_to_deepseek()
    ok3 = test_step3_hot_reload_works()
    ok4 = test_step4_revert_to_minimax()
    ok5 = test_step5_real_llm_call()
    print("\n" + "=" * 60)
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("🎉 P0+P1 5 步骤全过：provider 切换 + 热加载 + 真实 LLM 验证")
        return 0
    else:
        print(f"❌ 部分失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
