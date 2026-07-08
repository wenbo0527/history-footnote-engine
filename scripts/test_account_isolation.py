"""测试账户隔离"""
import requests
import json
import time

BASE = "http://localhost:8765"

# 1. 创建带 account_id 的新游戏
print("=== 1. 创建新游戏 (account_id='test_123') ===")
resp = requests.post(f"{BASE}/api/start", json={
    "era_id": "wanli1587",
    "identity": "weaving_male",
    "gender": "male",
    "character": {"name": "acc_test2", "age": 30, "occupation": "织工", "hometown": "盛泽镇"},
    "account_id": "test_123"
}, timeout=30)
data = resp.json()
sid = data.get("session_id")
print(f"  session: {sid}")

# 2. 看 meta.json
print("\n=== 2. meta.json ===")
meta_path = f"saves/{sid}/meta.json"
try:
    with open(meta_path) as f:
        meta = json.load(f)
    print(f"  account_id: {meta.get('account_id', 'MISSING')}")
    print(f"  session_id: {meta.get('session_id', 'MISSING')}")
    print(f"  era_id: {meta.get('era_id', 'MISSING')}")
except FileNotFoundError:
    print(f"  ❌ {meta_path} 不存在")
    print(f"  （v1.7.30 start 时不写 meta.json，需先调一次 /api/input）")

# 3. 调 /api/input 触发 save
print("\n=== 3. 调 /api/input 触发 save ===")
resp2 = requests.post(f"{BASE}/api/input", json={
    "session_id": sid,
    "input": "我先看看家里情况"
}, timeout=30)
print(f"  status: {resp2.status_code}")
print(f"  round: {resp2.json().get('round_number')}")

# 4. 再看 meta.json
print("\n=== 4. meta.json (after save) ===")
time.sleep(1)
try:
    with open(meta_path) as f:
        meta = json.load(f)
    print(f"  account_id: {meta.get('account_id', 'MISSING')}")
    print(f"  summary: {meta.get('summary', 'MISSING')}")
except FileNotFoundError:
    print(f"  ❌ {meta_path} 仍不存在")

# 5. 列出 test_123 账户的存档
print("\n=== 5. 列出 test_123 账户的存档 ===")
r = requests.get(f"{BASE}/api/archives", params={"account": "test_123"}, timeout=10)
data = r.json()
print(f"  共 {len(data.get('archives', []))} 个存档")
for a in data.get("archives", [])[:5]:
    print(f"    - {a['session_id']}: account_id={a.get('account_id')}, round={a.get('current_round')}")

# 6. 列出 default 账户（应看不到 test_123 的）
print("\n=== 6. 列出 default 账户（应只有旧存档/无账户存档）===")
r = requests.get(f"{BASE}/api/archives", params={"account": "default"}, timeout=10)
data = r.json()
print(f"  共 {len(data.get('archives', []))} 个存档")
test_123_count = sum(1 for a in data.get("archives", []) if a.get("account_id") == "test_123")
print(f"  其中 test_123 账户: {test_123_count} 个（应为 0）")
