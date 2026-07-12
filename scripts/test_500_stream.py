"""测 /api/input_stream 500 行为"""
import sys, json, urllib.request, urllib.error
sys.path.insert(0, 'src')

url = 'http://localhost:8765/api/input_stream'
data = json.dumps({"session_id": "wanli1587_20260712_223211", "input": "我织了一匹湖绫"}).encode()
req = urllib.request.Request(url, data=data, method='POST', headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        # Read first 500 bytes
        body = resp.read(500).decode('utf-8', errors='ignore')
        print(f'STATUS: {resp.status}')
        print(f'BODY (500 chars): {body}')
except urllib.error.HTTPError as e:
    body = e.read(500).decode('utf-8', errors='ignore')
    print(f'HTTPError: {e.code}')
    print(f'BODY: {body}')
except Exception as e:
    print(f'ERROR: {type(e).__name__} {e}')
