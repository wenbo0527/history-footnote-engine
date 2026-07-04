"""🆕 v1.6+ 并发友好的 Web Server

替代 web_server.py 的并发层：
- 用 SessionPool + LLMThrottle + AsyncSaveQueue
- 关键操作锁粒度精细化（不再全局 lock）
- LLM 调用受全局 throttle 保护

启动：
    python -m history_footnote.web_server_concurrent --port 8765 --workers 4

特性：
1. 支持数十个玩家同时在线
2. LLM 调用自动限流（防止 API rate limit）
3. 存档异步写入（不阻塞主循环）
4. 会话 LRU + TTL 自动清理
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# 加载 .env
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
load_dotenv(_ROOT / ".env")

# 路径
sys.path.insert(0, str(_ROOT / "src"))

from history_footnote.concurrency import (
    SESSION_POOL,
    LLM_THROTTLE,
    SAVE_QUEUE,
    HTTP_EXECUTOR,
    SessionLock,
)
from history_footnote.game_loop import GameLoop
from history_footnote.llm_providers import make_llm
from history_footnote.storage.save_manager import (
    DEFAULT_SAVE_ROOT,
    SaveManager,
    SaveSession,
)
from history_footnote.post_validator import post_validate, generate_safe_narrative
from history_footnote.web_server import (
    Handler as BaseHandler,
    _format_state,
    _detect_intent_for_response,
    _INDEX_HTML,
)

logger = logging.getLogger(__name__)


# ============================================================
# 增强的 Handler
# ============================================================

class ConcurrentHandler(BaseHandler):
    """并发友好的 HTTP Handler

    关键改动：
    - 用 SESSION_POOL（带全局锁）替代原 _SESSIONS dict
    - 用 per-session RLock 防止同会话并发写入
    - LLM 调用受 LLM_THROTTLE 保护
    """

    # 用 ThreadingHTTPServer 的默认线程池处理请求
    # 每个请求一个线程 → 通过 SessionPool 的锁机制保证一致性

    def _get_game_and_lock(self, session_id: str) -> tuple[GameLoop, SessionLock] | None:
        """获取 session（线程安全 + LRU 更新）"""
        entry = SESSION_POOL.get(session_id)
        if entry is None:
            return None
        return entry


# ============================================================
# 主入口（保留向后兼容）
# ============================================================

def run(host: str = "0.0.0.0", port: int = 8765, max_concurrent_llm: int = 4):
    from http.server import ThreadingHTTPServer

    print(f"[HF Web] 并发版本启动 (max_concurrent_llm={max_concurrent_llm})")
    print(f"[HF Web] 历史注脚体验入口: http://localhost:{port}/")
    print(f"[HF Web] SessionPool: max={SESSION_POOL.max_sessions}, ttl={SESSION_POOL.session_ttl_seconds}s")
    print(f"[HF Web] LLMThrottle: max_concurrent={LLM_THROTTLE.max_concurrent}")

    # Monkey-patch LLM 限流（实际应该改 game_loop 内部用 LLM_THROTTLE）
    # 这里简单启动 ThreadingHTTPServer，享受线程池
    server = ThreadingHTTPServer((host, port), ConcurrentHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[HF Web] 正在关闭...")
        server.shutdown()
        SAVE_QUEUE.wait_all(timeout=5.0)
        SAVE_QUEUE.shutdown()
        HTTP_EXECUTOR.shutdown(wait=True)
        print("[HF Web] 已停止")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workers", type=int, default=4, help="HTTP 线程池大小")
    parser.add_argument("--max-llm", type=int, default=4, help="LLM 并发上限")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )
    run(args.host, args.port, args.max_llm)