"""快速 smoke test: /api/start 真实端到端"""
import json
import sys
import urllib.request

URL = "http://localhost:8765/api/start"
body = {
    "era_id": "wanli1587",
    "identity": "weaving_male",
    "gender": "male",
    "character": {
        "name": "沈织户",
        "age": 30,
        "occupation": "织工",
        "background": "沈家原也不是盛泽本地人，正德年间祖上从嘉兴府桐乡逃水患过来，在盛泽镇东巷子买了这两间屋子、置了一台旧织机，从此落脚。传到沈织户手里，织机是两台，欠着绸缎牙行周二爷三两银子的旧账",
        "starting_situation": "手头现银一两二钱，欠牙行周二爷三两（利息每月三分），上月赊的桑叶钱八钱还没结。马上要交春税折银（合四钱二分），大毛束脩下月也该续了",
        "family": {
            "wife": "张氏（26岁）",
            "mother": "张氏（58岁）",
            "son": "大毛（5岁）",
        },
    },
}
data = json.dumps(body).encode("utf-8")
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as resp:
    d = json.loads(resp.read().decode("utf-8"))

print("=" * 60)
print("🆕 v1.9.5 修复后 /api/start 返回")
print("=" * 60)
print(f"  cash              = {d.get('cash')}    (期望 1.2)")
print(f"  debt              = {d.get('debt')}    (期望 3.0)")
print(f"  monthly_burn      = {d.get('monthly_burn')}    (期望 ~0.42)")
print(f"  character.name    = {d.get('character',{}).get('name')}")
print(f"  character.age     = {d.get('character',{}).get('age')}")
print(f"  character.bg      = {(d.get('character',{}).get('background') or '')[:40]}")
print(f"  family members    = {[m.get('name') for m in d.get('family_members',[])]}")
print(f"  active_tasks      = {[t.get('title')[:30] for t in d.get('sidebar_data',{}).get('active_tasks',[])]}")
print(f"  upcoming_deadlines= {[x.get('name') for x in d.get('sidebar_data',{}).get('upcoming_deadlines',[])]}")
print(f"  initial_state_src = {d.get('sidebar_data',{}).get('financial_status',{}).get('initial_state_source')}")
print(f"  session_id (last8)= {(d.get('session_id') or '')[-8:]}")

print("\n" + "=" * 60)
print("断言验证")
print("=" * 60)
checks = [
    ("cash = 1.2", d.get("cash") == 1.2),
    ("debt = 3.0", d.get("debt") == 3.0),
    ("monthly_burn ≈ 0.42", abs((d.get("monthly_burn") or 0) - 0.42) < 0.01),
    ("character.name = 沈织户", d.get("character", {}).get("name") == "沈织户"),
    ("character.age = 30", d.get("character", {}).get("age") == 30),
    ("family 包含张氏", any("张氏" in (m.get("name") or "") for m in d.get("family_members", []))),
    ("family 包含大毛", any("大毛" in (m.get("name") or "") for m in d.get("family_members", []))),
    ("有 2 个 active_tasks", len(d.get("sidebar_data", {}).get("active_tasks", [])) >= 2),
    ("有 1+ 个 upcoming_deadlines", len(d.get("sidebar_data", {}).get("upcoming_deadlines", [])) >= 1),
]
passed = 0
for name, ok in checks:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}")
    if ok:
        passed += 1
print(f"\n通过: {passed}/{len(checks)}")
sys.exit(0 if passed == len(checks) else 1)
