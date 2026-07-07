"""🆕 v1.8.4 真实 LLM 调用测试（不 mock fixture，直接调 /api/generate_character）

前提：服务运行在 8765 端口
环境：.env 配 LLM key（MINIMAX / DEEPSEEK）
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


def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def test_real_llm_5_rounds():
    """真实 LLM 跑 5 轮（缩短版，避免 token 太多）"""
    print("=" * 60)
    print("v1.8.4 真实 LLM 调用测试（5 轮）")
    print("=" * 60)

    # 先看服务在不在
    try:
        v = get("/api/version")
        print(f"  服务运行：{v.get('version', '?')}")
    except Exception as e:
        print(f"  ❌ 服务未运行：{e}")
        return False

    ok = True

    # 准备 prompt（5 轮 + 1601 葛贤抗税）
    rounds = [
        {
            "name": "Round 1（开始游戏）",
            "era_id": "wanli1587",
            "gender": "male",
            "location": "盛泽镇",
            "location_description": "江南丝绸重镇，机户林立",
            "identity_description": "织工，家中贫寒，靠技艺谋生",
            "life_expectation": "愿有一日能开自己的织坊",
        },
        {
            "name": "Round 2（问行情）",
            "era_id": "wanli1587",
            "gender": "male",
            "location": "盛泽镇",
            "location_description": "苏州府属镇，丝绸贸易枢纽",
            "identity_description": "刚入行的织工",
            "life_expectation": "学手艺养家",
        },
        {
            "name": "Round 3（机户遭遇税监）",
            "era_id": "wanli1587",
            "gender": "male",
            "location": "苏州府",
            "location_description": "税关所在地，矿税监设立",
            "identity_description": "织工代表",
            "life_expectation": "想组织同行减税",
        },
        {
            "name": "Round 4（1601 葛贤抗税前夜）",
            "era_id": "wanli1587",
            "gender": "male",
            "location": "苏州府",
            "location_description": "万历二十九年，矿税监孙隆横征暴敛",
            "identity_description": "织工领袖，被推举代表",
            "life_expectation": "领导织工反对加税",
        },
        {
            "name": "Round 5（1601 抗税爆发）",
            "era_id": "wanli1587",
            "gender": "male",
            "location": "苏州府",
            "location_description": "万历二十九年六月，葛贤率众打死税官",
            "identity_description": "葛贤式人物，织工领袖",
            "life_expectation": "为同行争命、不畏强权",
        },
    ]

    results = []
    total_tokens = 0
    for r in rounds:
        name = r.pop("name")
        print(f"\n--- {name} ---")
        t0 = time.time()
        try:
            resp = post("/api/generate_character", r)
            elapsed = time.time() - t0
            if resp.get("error"):
                print(f"  ❌ 错误：{resp.get('error')}")
                ok = _step(f"  {name}", False, resp.get("error"))
            else:
                char = resp.get("character", {})
                raw_len = len(resp.get("raw", ""))
                # 提取关键字段
                name_v = char.get("name", "?")
                occ = char.get("occupation", "?")
                age = char.get("age", "?")
                print(f"  ✓ {elapsed:.1f}s | 姓名={name_v} | 职业={occ} | 年龄={age}")
                print(f"    raw: {raw_len} 字符")
                results.append({"name": name_v, "occupation": occ, "elapsed": elapsed, "raw_len": raw_len})
                ok = _step(f"  {name}", True, f"{elapsed:.1f}s, raw={raw_len}") and ok
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ❌ 异常（{elapsed:.1f}s）：{e}")
            ok = _step(f"  {name}", False, str(e)[:50]) and ok
    return ok and len(results) == 5


def test_admin_audit_after():
    """检查 audit.log 是否有真实 LLM 调用记录"""
    print("\n" + "=" * 60)
    print("audit.log 真实 LLM 调用检查")
    print("=" * 60)
    log_path = ROOT / "saves" / "audit.log"
    if not log_path.exists():
        print("  ⚠️  audit.log 不存在")
        return False
    # 读最近 20 行
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()[-20:]
    print(f"  读取最近 {len(lines)} 条")
    real_llm_count = 0
    for line in lines:
        try:
            r = json.loads(line)
            if r.get("event") == "action" and r.get("route", "").endswith("generate_character"):
                real_llm_count += 1
        except Exception:
            pass
    print(f"  generate_character 记录：{real_llm_count} 条")
    return real_llm_count >= 3


def main():
    ok1 = test_real_llm_5_rounds()
    print()
    ok2 = test_admin_audit_after()
    print("\n" + "=" * 60)
    if ok1 and ok2:
        print("🎉 真实 LLM 5 轮 + 1601 抗税全过")
        return 0
    else:
        print(f"❌ 部分失败：ok1={ok1} ok2={ok2}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
