"""🆕 v1.8.5 真实 LLM 30 轮完整测试（不 mock fixture）

📋 设计：
- 30 轮，跨万历 15 年（1587）到万历 29 年（1601，葛贤抗税）
- 间隔 35s/轮（避免 60s 单次 timeout + 30s 退避 = 65s/轮）
- 总时长：~30 轮 × 35s = 17.5 min
- 自动 retry：遇 429/500/timeout 自动等待 60s 重试
- 进度日志：每 5 轮报告 + 全 30 轮收尾

🎬 剧本：
- Round 1-10: 1587 沈青崖在盛泽镇（织工学徒、入行、问行情）
- Round 11-20: 1590 沈青崖出师、织工代表（机户、税监）
- Round 21-30: 1601 葛贤抗税（万历二十九年，织工暴动）
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8765"

# 30 轮完整剧本：跨 1587-1601
ROUNDS = [
    # Round 1-10: 万历十五年（1587）盛泽镇织工学徒期
    ("R01-盛泽织工学徒", "wanli1587", "male", "盛泽镇", "江南丝绸重镇", "织工学徒，15 岁入行", "学手艺养家"),
    ("R02-问机房行情", "wanli1587", "male", "盛泽镇", "镇上机房林立", "学徒第三年", "学挽丝"),
    ("R03-入行第一年", "wanli1587", "male", "盛泽镇", "苏州府属镇", "满师", "自己能开机"),
    ("R04-上工第一日", "wanli1587", "male", "盛泽镇", "机房多如牛毛", "独立织工", "能养活自己"),
    ("R05-月入几何", "wanli1587", "male", "盛泽镇", "织工月入", "独立织工", "养家"),
    ("R06-问绸缎庄", "wanli1587", "male", "盛泽镇", "绸缎庄收布", "织工带布去卖", "卖得好价"),
    ("R07-税关初闻", "wanli1587", "male", "盛泽镇", "苏州税关", "听说税关", "了解税"),
    ("R08-工友闲谈", "wanli1587", "male", "盛泽镇", "工友间聊天", "工友", "团结"),
    ("R09-第一个冬天", "wanli1587", "male", "盛泽镇", "万历十五年冬", "过冬", "温饱"),
    ("R10-过年回家", "wanli1587", "male", "盛泽镇", "回乡", "回乡", "团圆"),
    # Round 11-20: 万历十八年（1590）出师+税监
    ("R11-出师三年", "wanli1587", "male", "盛泽镇", "出师三年", "熟练织工", "攒钱"),
    ("R12-想开织坊", "wanli1587", "male", "盛泽镇", "积累资金", "想创业", "开坊"),
    ("R13-苏州看行情", "wanli1587", "male", "苏州府", "苏州城", "看大行情", "了解市场"),
    ("R14-遇到税监", "wanli1587", "male", "苏州府", "税关所在", "被征税", "应付税"),
    ("R15-税监加征", "wanli1587", "male", "苏州府", "矿税监设立", "被多收", "抗税"),
    ("R16-和工友商量", "wanli1587", "male", "苏州府", "工人秘密会议", "工人代表", "组织"),
    ("R17-向掌柜说理", "wanli1587", "male", "苏州府", "绸缎庄", "代表工人", "求减税"),
    ("R18-听说葛贤", "wanli1587", "male", "苏州府", "传闻葛贤抗税", "听说有人领头", "找葛贤"),
    ("R19-入帮织工", "wanli1587", "male", "苏州府", "织工帮", "加入帮派", "学抗税"),
    ("R20-被推举代表", "wanli1587", "male", "苏州府", "工人推举", "被推为领袖", "领导抗税"),
    # Round 21-30: 万历二十九年（1601）葛贤抗税
    ("R21-万历二十九", "wanli1587", "male", "苏州府", "1601 年", "领袖织工", "组织行动"),
    ("R22-孙隆加税", "wanli1587", "male", "苏州府", "矿税监孙隆", "面对加税", "决心抗"),
    ("R23-密谋抗税", "wanli1587", "male", "苏州府", "织工密会", "组织骨干", "定计划"),
    ("R24-六月初一", "wanli1587", "male", "苏州府", "1601 年六月", "准备行动", "决死"),
    ("R25-打死税官", "wanli1587", "male", "苏州府", "打死税棍", "率众行动", "为民除害"),
    ("R26-抗税扩大", "wanli1587", "male", "苏州府", "事态扩大", "群众加入", "声援"),
    ("R27-官府震怒", "wanli1587", "male", "苏州府", "官府反应", "被追捕", "逃跑"),
    ("R28-葛贤被捕", "wanli1587", "male", "苏州府", "葛贤被抓", "藏匿中", "继续抗争"),
    ("R29-织工罢工", "wanli1587", "male", "苏州府", "全市罢工", "继续罢工", "逼退"),
    ("R30-事后余波", "wanli1587", "male", "苏州府", "万历三十年", "幸存", "继续生活"),
]


def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def call_with_retry(name, body, max_attempts=3, base_backoff=90):
    """真实 LLM 调用 + 退避重试"""
    for attempt in range(1, max_attempts + 1):
        t0 = time.time()
        try:
            status, resp = post("/api/generate_character", body)
            elapsed = time.time() - t0
            if status == 200 and not resp.get("error"):
                return True, elapsed, resp
            elif status == 500 and "timeout" in str(resp.get("error", "")).lower():
                # LLM 60s 超时
                if attempt < max_attempts:
                    wait = base_backoff
                    print(f"    ⏳ LLM timeout（{elapsed:.1f}s），等待 {wait}s 后重试 {attempt + 1}/{max_attempts}")
                    time.sleep(wait)
                    continue
            elif status == 429:
                # 限流
                if attempt < max_attempts:
                    wait = base_backoff * 2
                    print(f"    🚦 限流（429），等待 {wait}s 后重试 {attempt + 1}/{max_attempts}")
                    time.sleep(wait)
                    continue
            return False, elapsed, resp
        except urllib.error.HTTPError as e:
            elapsed = time.time() - t0
            if e.code == 500 and attempt < max_attempts:
                wait = base_backoff
                print(f"    ⏳ HTTP 500（{elapsed:.1f}s），等待 {wait}s 后重试 {attempt + 1}/{max_attempts}")
                time.sleep(wait)
                continue
            return False, elapsed, {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            elapsed = time.time() - t0
            return False, elapsed, {"error": str(e)[:100]}
    return False, 0, {"error": "max attempts exceeded"}


def test_real_llm_30_rounds():
    """真实 LLM 跑 30 轮"""
    print("=" * 60)
    print("v1.8.5 真实 LLM 30 轮完整测试（不 mock fixture）")
    print("=" * 60)

    # 先看服务在不在
    try:
        v = get("/api/version")
        print(f"  服务运行：{v.get('version', '?')}")
    except Exception as e:
        print(f"  ❌ 服务未运行：{e}")
        return False, []

    assert len(ROUNDS) == 30, f"应 30 轮，实际 {len(ROUNDS)}"
    print(f"  准备 {len(ROUNDS)} 轮（万历十五年→万历二十九年）")
    # 读当前真实限流
    try:
        s = get("/api/version")
        print(f"  服务版本：{s.get('version', '?')}")
    except Exception:
        pass
    # 限流从环境读
    import os
    llm_max = int(os.environ.get("LLM_MAX_REQUESTS", 30))
    llm_win = float(os.environ.get("LLM_WINDOW_SECONDS", 300))
    print(f"  限流：{llm_max}/{llm_win}s（实时）")
    print()

    results = []
    total_t0 = time.time()
    for i, (name, era_id, gender, location, loc_desc, identity, life_exp) in enumerate(ROUNDS, 1):
        body = {
            "era_id": era_id,
            "gender": gender,
            "location": location,
            "location_description": loc_desc,
            "identity_description": identity,
            "life_expectation": life_exp,
        }
        print(f"[{i:2d}/30] {name}")
        ok, elapsed, resp = call_with_retry(name, body)
        if ok:
            char = resp.get("character", {})
            name_v = char.get("name", "?")
            raw_len = len(resp.get("raw", ""))
            print(f"    ✓ {elapsed:5.1f}s | {name_v} | raw={raw_len} 字符")
            results.append({
                "round": i,
                "name": name,
                "character": name_v,
                "elapsed": elapsed,
                "raw_len": raw_len,
                "ok": True,
            })
        else:
            err = resp.get("error", "unknown")[:60]
            print(f"    ❌ {elapsed:5.1f}s | {err}")
            results.append({
                "round": i,
                "name": name,
                "error": err,
                "elapsed": elapsed,
                "ok": False,
            })
        # 间隔 35s（避免连续触发限流 + 留 buffer 给 LLM 27-30s 响应）
        if i < 30:
            time.sleep(35)

    total_elapsed = time.time() - total_t0
    return True, results, total_elapsed


def summarize(results, total_elapsed):
    """收尾总结"""
    print("\n" + "=" * 60)
    print("30 轮真实 LLM 测试总结")
    print("=" * 60)
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    print(f"  成功：{ok_count}/30  ({ok_count / 30 * 100:.0f}%)")
    print(f"  失败：{fail_count}/30")
    print(f"  总耗时：{total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")
    if ok_count > 0:
        ok_results = [r for r in results if r["ok"]]
        avg_elapsed = sum(r["elapsed"] for r in ok_results) / len(ok_results)
        print(f"  平均单轮：{avg_elapsed:.1f}s")
    # 角色名列表
    chars = [r.get("character", "?") for r in results if r.get("character")]
    if chars:
        print(f"\n  生成角色（前 10）：{chars[:10]}")
    # 失败列表
    fails = [r for r in results if not r["ok"]]
    if fails:
        print(f"\n  失败：")
        for f in fails:
            print(f"    R{f['round']:02d} {f['name']}: {f.get('error', '?')}")
    return ok_count


def main():
    ok, results, total = test_real_llm_30_rounds()
    print()
    ok_count = summarize(results, total)
    if ok and ok_count >= 25:  # 至少 25/30 成功（83%）
        print(f"\n🎉 30 轮测试通过：{ok_count}/30 成功")
        return 0
    else:
        print(f"\n❌ 失败：{ok_count}/30（需 ≥25/30）")
        return 1


if __name__ == "__main__":
    sys.exit(main())
