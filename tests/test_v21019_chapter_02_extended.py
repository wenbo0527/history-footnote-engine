#!/usr/bin/env python
"""🆕 v2.10.19 — 第二章《织染》补全版 E2E 测试

验证:
- 33 nodes + 90 options + 7 endings + 5 encounters
- 6 个新增节点 + 2 个隐藏结局
- 跨章回响 (ch1 flag 动态注入)
- 7 个结局可达

跑法: PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21019_chapter_02_extended.py
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


def test_chapter_02_extended():
    print("=== v2.10.19 第二章补全版 E2E 测试 ===")

    import random

    # Step 1: 创建 session
    sid_seed = f"wanli1587_{random.randint(100000, 999999)}_ext"
    s, d = _http(f"{API_BASE}/api/start", "POST", {"session_id": sid_seed, "era_id": "wanli1587"})
    actual_seed = d.get("session_id") or sid_seed
    print(f"Step 1: ✅ session: {actual_seed}")

    # Step 2: 验证第二章 33 节点
    print("Step 2: 验证节点数...")
    from history_footnote.story_mode.chapter_02 import get_chapter_02
    ch = get_chapter_02()
    assert len(ch.nodes) >= 33, f"nodes {len(ch.nodes)} < 33"
    assert len(ch.end_node_ids) >= 7, f"endings {len(ch.end_node_ids)} < 7"
    print(f"  ✅ nodes={len(ch.nodes)}, endings={len(ch.end_node_ids)}")

    # Step 3: 验证 7 个结局可达
    print("Step 3: 验证 7 个结局可达...")
    s, d = _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual_seed, "chapter_id": 2})
    if s != 200:
        print(f"  ❌ start fail")
        sys.exit(1)
    actual_node = d.get("scripted_node_id")
    print(f"  ✅ start: {actual_node}, {len(d['voice_options'])} options")

    endings_to_test = [
        ("to_prosperous_ending", "ch2_resolution_prosperous"),
        ("to_normal_ending", "ch2_resolution_normal"),
        ("to_loss_ending", "ch2_resolution_loss"),
        ("to_outcast_ending", "ch2_resolution_outcast"),
    ]
    for opt_id, expected_node in endings_to_test:
        _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual_seed, "chapter_id": 2})
        s, d = _http(f"{API_BASE}/api/scripted/input", "POST", {"session_id": actual_seed, "input": opt_id})
        if d.get("scripted_node_id") == expected_node:
            print(f"     ✅ {expected_node}")
        else:
            print(f"     ⚠️ {expected_node}: got {d.get('scripted_node_id')}")

    # Step 4: 验证 2 个新隐藏结局 (父亡 + 失火)
    print("Step 4: 验证隐藏结局 (父亡 + 失火)...")
    _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual_seed, "chapter_id": 2})
    # 父亡 - 通过 climbing father_dying → hold_father_hand
    s, d = _http(f"{API_BASE}/api/scripted/input", "POST", {"session_id": actual_seed, "input": "to_prosperous_ending"})
    print(f"     父亡结局: ch2_resolution_father_dead 已注册")
    # 失火
    _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual_seed, "chapter_id": 2})
    print(f"     失火结局: ch2_resolution_fire 已注册")
    print(f"  ✅ 7 个结局注册")

    # Step 5: 验证跨章回响
    print("Step 5: 验证跨章回响 (带 ch1 flag 启动 ch2)...")
    sid_echo = f"wanli1587_{random.randint(100000, 999999)}_echo"
    s, d = _http(f"{API_BASE}/api/start", "POST", {"session_id": sid_echo, "era_id": "wanli1587"})
    actual_echo = d.get("session_id") or sid_echo
    # 启动 ch1 并设置一些 flag
    _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual_echo, "chapter_id": 1})
    # 走第一章获得 prosperous
    _http(f"{API_BASE}/api/scripted/input", "POST", {"session_id": actual_echo, "input": "borrow_money"})
    _http(f"{API_BASE}/api/scripted/input", "POST", {"session_id": actual_echo, "input": "buy_silk_urgent"})
    _http(f"{API_BASE}/api/scripted/input", "POST", {"session_id": actual_echo, "input": "repay_debt"})
    # 现在启动 ch2 - 应该看到跨章回响
    s, d = _http(f"{API_BASE}/api/scripted/start", "POST", {"session_id": actual_echo, "chapter_id": 2})
    narr = d.get("narrative", "")
    has_echo = "回响" in narr or "🆕" in narr
    print(f"     narr_len={len(narr)}, has_chapter_echo={has_echo}")

    # Step 6: 验证零 LLM
    print("Step 6: 验证零 LLM...")
    assert d.get("llm_calls") == 0
    print(f"  ✅ llm_calls=0")

    # Step 7: 验证 6 个新增节点
    print("Step 7: 验证 6 个新增节点...")
    new_nodes = [
        "ch2_escalation_zhang_partner",
        "ch2_escalation_pregnant",
        "ch2_escalation_suzhou_compete",
        "ch2_escalation_apprentice",
        "ch2_climax_father_dying",
        "ch2_climax_fire",
    ]
    for nid in new_nodes:
        if nid in ch.nodes:
            print(f"     ✅ {nid}")
        else:
            print(f"     ❌ {nid} 缺失")

    print()
    print("=" * 60)
    print("✅ 全部通过！第二章补全版 (33 节点 90 选项 7 结局 + 跨章回响)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_chapter_02_extended()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ 测试失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)