"""测试所有 modal API 的真实响应"""
import json
import requests

BASE = "http://localhost:8765"

# 创建 session
resp = requests.post(f"{BASE}/api/start", json={
    "era_id": "wanli1587",
    "identity": "weaving_male",
    "gender": "male",
    "character": {
        "name": "弹层测试",
        "age": 30,
        "occupation": "织工",
        "hometown": "盛泽镇"
    }
}, timeout=15)
sid = resp.json()["session_id"]
print(f"session_id: {sid}\n")

# 1. /api/character_wiki (GET)
print("=" * 60)
print("1. /api/character_wiki (GET)")
print("=" * 60)
try:
    r = requests.get(f"{BASE}/api/character_wiki", params={"session_id": sid}, timeout=8)
    print(f"  status: {r.status_code}")
    data = r.json()
    print(f"  keys: {list(data.keys())}")
    if 'wiki' in data:
        wiki = data['wiki']
        print(f"  wiki keys: {list(wiki.keys()) if isinstance(wiki, dict) else 'not dict'}")
        if isinstance(wiki, dict):
            for k, v in wiki.items():
                print(f"    {k}: {str(v)[:80]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. /api/recap (POST, 调 LLM)
print("\n" + "=" * 60)
print("2. /api/recap (POST)")
print("=" * 60)
try:
    r = requests.post(f"{BASE}/api/recap", json={"session_id": sid, "rounds": 5}, timeout=30)
    print(f"  status: {r.status_code}")
    data = r.json()
    print(f"  keys: {list(data.keys())}")
    for k, v in data.items():
        print(f"    {k}: {str(v)[:80]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. /api/glossary (POST, 调 LLM)
print("\n" + "=" * 60)
print("3. /api/glossary (POST)")
print("=" * 60)
try:
    r = requests.post(f"{BASE}/api/glossary", json={
        "session_id": sid,
        "terms": ["桑叶", "牙人"]
    }, timeout=30)
    print(f"  status: {r.status_code}")
    data = r.json()
    print(f"  keys: {list(data.keys())}")
    for k, v in data.items():
        print(f"    {k}: {str(v)[:80]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 4. /api/feedback (POST)
print("\n" + "=" * 60)
print("4. /api/feedback (POST)")
print("=" * 60)
try:
    r = requests.post(f"{BASE}/api/feedback", json={
        "session_id": sid,
        "category": "bug",
        "message": "测试反馈"
    }, timeout=8)
    print(f"  status: {r.status_code}")
    print(f"  body: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 5. /api/archives (GET)
print("\n" + "=" * 60)
print("5. /api/archives (GET)")
print("=" * 60)
try:
    r = requests.get(f"{BASE}/api/archives", params={"account": "test"}, timeout=8)
    print(f"  status: {r.status_code}")
    print(f"  body: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")
