#!/usr/bin/env python
"""🆕 v2.10.16 — 故事模式 E2E 测试（零 LLM 验证）

验证:
- /api/scripted/start 启动剧本
- /api/scripted/input 玩家选择
- effects + flag 副作用正确
- chapter_complete 章节结束
- 关键: llm_calls=0 在所有响应里

跑法:
  PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21016_story_mode.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_BASE = "http://127.0.0.1:8765"


def _http(url: str, method: str = "GET", body: dict | None = None, timeout: float = 10.0) -> tuple[int, dict]:
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
            return e.code, {"error": "non-json response"}


def test_story_mode_full_flow() -> None:
    print("=== v2.10.16 故事模式 E2E 测试（零 LLM）===")

    # 1. 创建 session
    print("Step 1: 创建 session...")
    import random
    sid = f"wanli1587_{random.randint(100000, 999999)}_test"
    status, data = _http(f"{API_BASE}/api/start", "POST", {
        "session_id": sid,
        "era_id": "wanli1587",
    })
    if status != 200:
        print(f"  ❌ start 失败: {status} {data}")
        sys.exit(1)
    actual_sid = data.get("session_id") or sid
    print(f"  ✅ session: {actual_sid}")

    # 2. 启动故事模式
    print("Step 2: 启动故事模式 (/api/scripted/start)...")
    status, data = _http(f"{API_BASE}/api/scripted/start", "POST", {
        "session_id": actual_sid,
        "chapter_id": 1,
    })
    if status != 200:
        print(f"  ❌ start 失败: {status} {data}")
        sys.exit(1)
    assert data.get("scripted_mode") is True, "未进入 scripted mode"
    assert data.get("llm_calls") == 0, f"llm_calls 必须是 0，实际 {data.get('llm_calls')}"
    assert len(data.get("voice_options", [])) == 4, f"必须有 4 个 voice_options"
    assert "万历十五年" in data.get("narrative", ""), "narrative 必须含万历十五年"
    print(f"  ✅ start OK: {len(data['voice_options'])} options, llm_calls={data['llm_calls']}")
    print(f"     node: {data['scripted_node_id']}")

    # 3. 选 borrow_money
    print("Step 3: 选择 borrow_money...")
    status, data = _http(f"{API_BASE}/api/scripted/input", "POST", {
        "session_id": actual_sid,
        "input": "borrow_money",
    })
    if status != 200:
        print(f"  ❌ input 失败: {status} {data}")
        sys.exit(1)
    assert data.get("llm_calls") == 0, "llm_calls 必须是 0"
    effects = data.get("effects_applied", {})
    assert effects.get("cash_delta") == 5, f"cash_delta 错误: {effects}"
    assert effects.get("debt_delta") == 5, f"debt_delta 错误: {effects}"
    assert "has_debt" in data.get("flag_added", []), "必须设置 has_debt flag"
    assert data.get("cash") == 5, "state cash 应为 5"
    print(f"  ✅ borrow_money OK: cash={data['cash']} debt={data['debt']}")
    print(f"     effects: {effects}")
    print(f"     flag_added: {data['flag_added']}")

    # 4. 选 buy_silk_urgent
    print("Step 4: 选择 buy_silk_urgent...")
    status, data = _http(f"{API_BASE}/api/scripted/input", "POST", {
        "session_id": actual_sid,
        "input": "buy_silk_urgent",
    })
    if status != 200:
        print(f"  ❌ input 失败: {status} {data}")
        sys.exit(1)
    assert data.get("llm_calls") == 0, "llm_calls 必须是 0"
    effects = data.get("effects_applied", {})
    assert effects.get("cash_delta") == -4, f"cash_delta 错误: {effects}"
    assert effects.get("rice_delta") == 5, f"rice_delta 错误: {effects}"
    print(f"  ✅ buy_silk_urgent OK: cash={data['cash']} rice={data['rice']}")

    # 5. 选 repay_debt (→ resolution)
    print("Step 5: 选择 repay_debt (→ resolution)...")
    status, data = _http(f"{API_BASE}/api/scripted/input", "POST", {
        "session_id": actual_sid,
        "input": "repay_debt",
    })
    if status != 200:
        print(f"  ❌ input 失败: {status} {data}")
        sys.exit(1)
    assert data.get("chapter_complete") is True, "应触发 chapter_complete"
    assert data.get("llm_calls") == 0, "llm_calls 必须是 0"
    print(f"  ✅ chapter_complete OK: node={data['scripted_node_id']}")
    print(f"     state: cash={data['cash']} debt={data['debt']}")
    print(f"     flags: {data['scripted_flags']}")

    # 6. GET /api/scripted/state
    print("Step 6: GET /api/scripted/state...")
    status, data = _http(f"{API_BASE}/api/scripted/state?session_id={actual_sid}")
    if status != 200:
        print(f"  ❌ state 失败: {status} {data}")
        sys.exit(1)
    assert data.get("scripted_chapter_complete") is True
    print(f"  ✅ state OK: node={data['scripted_node_id']}, complete={data['scripted_chapter_complete']}")

    # 7. 验证 LLM 调用总次数
    print("Step 7: 验证零 LLM 调用...")
    # 累计 llm_calls
    # 这里我们重新走一遍来统计
    total_llm = 0
    sid2 = f"wanli1587_{random.randint(100000, 999999)}_test2"
    _http(f"{API_BASE}/api/start", "POST", {"session_id": sid2, "era_id": "wanli1587"})
    _, d = _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": sid2, "chapter_id": 1})
    total_llm += d.get("llm_calls", 0)
    for _ in range(3):
        _, d = _http(f"{API_BASE}/api/scripted/input", "POST", {"session_id": sid2, "input": "borrow_money"})
        total_llm += d.get("llm_calls", 0)
    assert total_llm == 0, f"LLM 调用总计 {total_llm} 必须为 0"
    print(f"  ✅ 总 LLM 调用 = {total_llm}")

    print()
    print("=" * 60)
    print("✅ 7/7 全部通过！故事模式（零 LLM）端到端验证完成")
    print("=" * 60)


def main() -> None:
    try:
        test_story_mode_full_flow()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ 测试失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()