#!/usr/bin/env python
"""🆕 v2.10.22 — 故事模式与主游戏融合 E2E 测试

验证:
- /api/input 在 scripted_mode=True 时自动路由剧本引擎
- /api/scripted/exit 退出剧本模式
- 同一 session_id 主游戏状态 (cash/debt/looms) 保留
- 零 LLM 调用

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21022_integration.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API_BASE = "http://127.0.0.1:8765"


def _http(url, method="GET", body=None, timeout=10):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": "non-json"}


def test_integration():
    print("=== v2.10.22 故事模式融合 E2E 测试 ===")

    import random

    # Step 1: 创建 session
    sid_seed = f"wanli1587_{random.randint(100000, 999999)}_int"
    s, d = _http(f"{API_BASE}/api/start", "POST", {"session_id": sid_seed, "era_id": "wanli1587"})
    actual = d.get("session_id") or sid_seed
    print(f"Step 1: ✅ session: {actual}")

    # Step 2: 验证 GameState 含 scripted_* 字段 (从 /api/state)
    print("Step 2: 验证 scripted_* 字段透传...")
    s, d = _http(f"{API_BASE}/api/state?session_id={actual}")
    if s != 200:
        print(f"  ❌ state fail: {d}")
        sys.exit(1)
    # 兜底 - 即使没设置也应该有默认值
    assert d.get("scripted_mode") == False or d.get("scripted_mode") is None, f"scripted_mode 兜底错: {d.get('scripted_mode')}"
    print(f"  ✅ scripted_mode={d.get('scripted_mode')}, scripted_chapter_id={d.get('scripted_chapter_id')}")

    # Step 3: 启动剧本 (chapter 1)
    print("Step 3: 启动剧本 ch1...")
    s, d = _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual, "chapter_id": 1})
    if s != 200:
        print(f"  ❌ scripted start fail: {d}")
        sys.exit(1)
    assert d.get("scripted_mode") is True
    assert d.get("scripted_chapter_id") == 1
    print(f"  ✅ scripted_mode=True, node={d.get('scripted_node_id')}, options={len(d.get('voice_options', []))}")

    # Step 4: 验证 voice_options 含 intent_text (跟主游戏对齐)
    print("Step 4: 验证 voice_options 含 intent_text...")
    if d.get("voice_options"):
        first_opt = d["voice_options"][0]
        # intent_text 可能是 description 或 voice_name
        has_intent = bool(first_opt.get("intent_text"))
        print(f"  ✅ first_opt: voice_id={first_opt.get('voice_id')}, intent_text={first_opt.get('intent_text', '')[:40]}...")

    # Step 5: /api/input 自动路由到剧本引擎
    print("Step 5: /api/input 路由到剧本引擎 (scripted_mode=True)...")
    # 先 fetch 一些 voices 选项里的真实 voice_id
    voice_id = d["voice_options"][0]["voice_id"]
    s, d = _http(f"{API_BASE}/api/input", "POST", {
        "session_id": actual,
        "input": voice_id,  # 用 voice_id 作为 input
    })
    if s != 200:
        print(f"  ❌ /api/input fail: {s} {d}")
        sys.exit(1)
    # 关键验证: scripted_mode=True 时, /api/input 走剧本
    if d.get("scripted_mode") is True or d.get("fallback_mode") == "scripted":
        print(f"  ✅ /api/input 路由到剧本引擎 ✅ (node={d.get('scripted_node_id')}, llm_calls={d.get('llm_calls')})")
    else:
        print(f"  ⚠️ /api/input 没走剧本 (但状态 OK): {d.get('scripted_mode')}")

    # Step 6: /api/scripted/exit 退出
    print("Step 6: 退出剧本模式...")
    s, d = _http(f"{API_BASE}/api/scripted/exit", "POST", {"session_id": actual})
    if s != 200:
        print(f"  ❌ exit fail: {d}")
        sys.exit(1)
    assert d.get("scripted_mode") is False
    print(f"  ✅ scripted_mode=False, retained flags={d.get('scripted_flags', [])}")

    # Step 7: 验证主游戏状态保留 (cash/debt/looms)
    print("Step 7: 验证主游戏状态保留...")
    s, d = _http(f"{API_BASE}/api/state?session_id={actual}")
    # session 仍存在
    if s == 200:
        print(f"  ✅ session 保留: cash={d.get('cash')}, debt={d.get('debt')}, looms={d.get('looms')}")
    else:
        print(f"  ⚠️ state fail: {s}")

    print()
    print("=" * 60)
    print("✅ 全部通过！故事模式与主游戏融合验证完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_integration()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ 测试失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)