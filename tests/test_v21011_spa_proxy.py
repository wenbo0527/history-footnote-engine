#!/usr/bin/env python
"""🆕 v2.10.11 — SPA server /api/* proxy E2E test

🆕 v2.10.11 修复: 'Unexpected token <, <!DOCTYPE ... is not valid JSON'

SPA 静态服务器之前没代理 /api/* → 前端 fetch('/api/menu') 拿到 HTML
SvelteKit fallback 页面（<!DOCTYPE ...），触发 JSON parse 错误。

本测试验证 spa_server.py 启动后能正确代理 /api/* 到后端 8765。

跑法：
  PYTHONPATH=src /opt/anaconda3/bin/python tests/test_v21011_spa_proxy.py

要求：
- 后端 web_server 在 8765 运行
- spa_server.py 是 v2.10.11+ (带 BACKEND_URL 代理)
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _wait_port_free(port: int, timeout: float = 5.0) -> bool:
    """等端口空出来"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.1)
    return False


def _wait_http_ready(url: str, timeout: float = 10.0) -> bool:
    """等 HTTP server 启动完成"""
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status in (200, 400, 404):
                    return True
        except Exception as e:
            last_err = e
        time.sleep(0.2)
    print(f"  wait_http_ready last_err: {last_err!r}", file=sys.stderr)
    return False


def _http_get(url: str, timeout: float = 5.0) -> tuple[int, str, bytes]:
    """返回 (status, content-type, body)"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", e.read()


def _http_post(url: str, body: dict | None = None, timeout: float = 5.0) -> tuple[int, str, bytes]:
    """返回 (status, content-type, body)"""
    data = json.dumps(body).encode() if body else b""
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", e.read()


def test_spa_server_proxy() -> None:
    """🆕 v2.10.11: 测试 spa_server 代理 /api/* 到后端"""
    print("=== v2.10.11 SPA proxy 测试 ===")

    # 1. 确认后端在 8765 运行
    print("Step 1: 检查后端 8765 是否运行...")
    status, ct, body = _http_get("http://127.0.0.1:8765/api/version")
    if status != 200:
        print(f"  ❌ 后端 8765 不可用: status={status}")
        print(f"  请先启动后端: PYTHONPATH=src python -c 'from history_footnote.web_server import run; run()'")
        sys.exit(1)
    print(f"  ✅ 后端 8765 OK: {ct}")

    # 2. 启动 SPA server 在随机端口（8766 可能被占用）
    print("Step 2: 启动 SPA server (动态端口)...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        spa_port = s.getsockname()[1]
    print(f"  SPA port: {spa_port}")

    # 启动 spa_server 子进程
    proc = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "scripts" / "spa_server.py"),
            str(spa_port),
            str(ROOT / "src" / "frontend" / "build"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not _wait_http_ready(f"http://127.0.0.1:{spa_port}", timeout=10.0):
            print("  ❌ SPA server 启动超时")
            return

        spa_base = f"http://127.0.0.1:{spa_port}"

        # 3. 测试 SPA 静态 fallback
        print("Step 3: 测试 SPA fallback (非 /api/*)...")
        status, ct, body = _http_get(f"{spa_base}/login")
        if status != 200 or b"<" not in body[:50]:
            print(f"  ❌ SPA fallback 失败: status={status}")
            return
        print(f"  ✅ SPA fallback OK: status={status}, {len(body)} bytes")

        # 4. 🆕 核心: 测试 /api/* 代理
        print("Step 4: 测试 /api/* 代理 (修复 v2.10.11 的核心)...")
        status, ct, body = _http_get(f"{spa_base}/api/state?session_id=test_proxy")
        # 后端对未知 session 返回 404 — 但必须是 JSON 不是 HTML
        if status not in (200, 404):
            print(f"  ❌ /api/state 代理失败: status={status}")
            return
        # 关键验证: 必须是 JSON, 不能是 HTML
        try:
            data = json.loads(body)
            print(f"  ✅ /api/state 返回 JSON: {data}")
        except json.JSONDecodeError:
            print(f"  ❌ /api/state 返回非 JSON (v2.10.11 修复未生效):")
            print(f"     body[:200] = {body[:200]}")
            sys.exit(1)

        # 5. 测试 /api/menu (访客流程核心端点)
        print("Step 5: 测试 /api/menu (访客流程)...")
        status, ct, body = _http_get(f"{spa_base}/api/menu")
        if status != 200:
            print(f"  ❌ /api/menu 代理失败: status={status}")
            sys.exit(1)
        try:
            data = json.loads(body)
            if "user" not in data:
                print(f"  ❌ /api/menu 返回无 user 字段: {data}")
                sys.exit(1)
            print(f"  ✅ /api/menu 返回 JSON: user={data['user']['account_id']}")
        except json.JSONDecodeError:
            print(f"  ❌ /api/menu 返回非 JSON:")
            print(f"     body[:200] = {body[:200]}")
            sys.exit(1)

        # 6. 测试 POST /api/* 代理
        print("Step 6: 测试 POST /api/* 代理...")
        status, ct, body = _http_post(f"{spa_base}/api/version", {"x": 1})
        if status not in (200, 400):
            print(f"  ❌ POST 代理失败: status={status}")
            sys.exit(1)
        print(f"  ✅ POST 代理 OK: status={status}")

        # 7. 测试 4xx 透传
        print("Step 7: 测试 4xx 错误透传...")
        status, ct, body = _http_get(f"{spa_base}/api/state")  # 缺 session_id
        if status != 400:
            print(f"  ❌ 4xx 未透传: status={status}")
            sys.exit(1)
        print(f"  ✅ 4xx 透传 OK: status={status}")

        # 8. 测试 SPA static asset (mmx-output)
        print("Step 8: 测试 SPA 静态资源 (mmx-output)...")
        status, ct, body = _http_get(f"{spa_base}/mmx-output/jian-ye-A-v4.jpg")
        if status != 200:
            print(f"  ❌ 静态资源失败: status={status}")
            sys.exit(1)
        print(f"  ✅ 静态资源 OK: status={status}, {len(body)} bytes")

        print()
        print("=" * 50)
        print("✅ 全部 6/6 通过！spa_server /api/* 代理修复有效")
        print("=" * 50)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    try:
        test_spa_server_proxy()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ 测试失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()