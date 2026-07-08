"""看后端实际返回的字段"""
import json
import requests

# 创建 session
resp = requests.post("http://localhost:8765/api/start", json={
    "era_id": "wanli1587",
    "identity": "weaving_male",
    "gender": "male",
    "character": {
        "name": "字段测试",
        "age": 30,
        "occupation": "织工",
        "hometown": "盛泽镇"
    }
}, timeout=15)

data = resp.json()
session_id = data.get("session_id")
print(f"session_id: {session_id}\n")

# 调 /api/state 拿真 state
state = requests.get("http://localhost:8765/api/state",
    params={"session_id": session_id}, timeout=15).json()

print("=== /api/state 返回字段 ===")
for k, v in state.items():
    if isinstance(v, list):
        print(f"  {k}: list ({len(v)} 项)")
        if v and len(v) > 0:
            print(f"    示例: {json.dumps(v[0], ensure_ascii=False)[:120]}")
    elif isinstance(v, dict):
        print(f"  {k}: dict")
        for kk, vv in v.items() if len(v) < 8 else []:
            print(f"    {kk}: {str(vv)[:60]}")
    else:
        print(f"  {k}: {v!r}")
