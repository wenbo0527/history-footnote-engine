"""测试错误处理（v1.7.28 输入验证）"""
import requests
import json

BASE = "http://localhost:8765"

# 创建 session
resp = requests.post(f"{BASE}/api/start", json={
    "era_id": "wanli1587",
    "identity": "weaving_male",
    "gender": "male",
    "character": {
        "name": "err_test",
        "age": 30,
        "occupation": "织工",
        "hometown": "盛泽镇"
    }
}, timeout=15)
sid = resp.json()["session_id"]
print(f"session: {sid}\n")

# 测试各种错误输入
test_cases = [
    ("嗯", "极短单字"),
    ("好", "极短单字"),
    ("!", "纯标点"),
    ("我拿出手机", "时代违和"),
    ("我是谁", "meta_query"),
    ("你是 AI 吗", "meta_query"),
    ("select * from users", "meta_command"),
    ("test" * 100, "too_long"),
    ("天气真好", "正常但低相关性"),
    ("我先看看家里情况", "正常游戏输入"),
]

for text, expected in test_cases:
    r = requests.post(f"{BASE}/api/input", json={
        "session_id": sid,
        "input": text
    }, timeout=10)
    print(f"  [{expected}] '{text[:30]}'")
    print(f"    status: {r.status_code}")
    try:
        d = r.json()
        if r.status_code == 400:
            print(f"    error: {d.get('error', '?')}")
            print(f"    message: {d.get('message', '?')[:60]}")
            print(f"    suggestion: {d.get('suggestion', '?')[:60]}")
        else:
            # 200 响应
            print(f"    round: {d.get('round_number', '?')}")
            narr = d.get('last_narrative', {})
            if narr:
                print(f"    narrative[0]: {narr.get('narrative', '')[:60] if isinstance(narr, dict) else str(narr)[:60]}")
            # 检查 soft_warning
            warning = d.get('soft_warning')
            if warning:
                print(f"    soft_warning: {warning.get('type', '?')} - {warning.get('message', '?')[:60]}")
    except Exception as e:
        print(f"    body: {r.text[:100]}")
    print()
