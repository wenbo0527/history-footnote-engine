"""测 500 错误 (用正确路径)"""
import sys, time, urllib.request, urllib.error
sys.path.insert(0, 'src')
import os
os.environ.setdefault('LLM_MAX_REQUESTS', '100')
os.environ.setdefault('LLM_WINDOW_SECONDS', '60.0')
os.environ.setdefault('HFE_BASE_DIR', '/tmp/hfe_test')

import urllib.error

tests = [
    'http://localhost:8765/api/eras',
    'http://localhost:8765/api/identities',
    'http://localhost:8765/api/state',
    'http://localhost:8765/api/chapter/state',
    'http://localhost:8765/api/chapter/blueprint',
    'http://localhost:8765/api/character_wiki',
    'http://localhost:8765/api/archives',
    'http://localhost:8765/api/account/info',
    'http://localhost:8765/api/menu',
    'http://localhost:8765/api/saves/list',
    'http://localhost:8765/api/version',
    'http://localhost:8765/api/llm/stats',
    'http://localhost:8765/api/monitor/health',
    'http://localhost:8765/api/admin/whoami',
    'http://localhost:8765/api/trial/current',
]
for url in tests:
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8', errors='ignore')[:100]
            print(f'GET {url}: {resp.status} {data[:80]}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:200]
        print(f'GET {url}: HTTPError {e.code} {body}')
    except Exception as e:
        print(f'GET {url}: ERROR {type(e).__name__} {e}')
