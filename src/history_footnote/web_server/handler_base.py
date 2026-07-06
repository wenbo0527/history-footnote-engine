"""🆕 v1.7.29 Handler 基础设施

包含所有路由 handler 都依赖的工具方法（_json / _html / _gzip / _serve_static 等）
与限流工具。
"""
from __future__ import annotations

import gzip
import json
import logging
import re
import time as _time
import uuid
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 🆕 v1.7.29 web_server 子包统一 logger
logger = logging.getLogger("history_footnote.web_server")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
logger.propagate = False  # 防止与 root logger 重复输出


# ============================================================
# MIME type 与请求体解析
# ============================================================

MIME_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def parse_request_body(handler: BaseHTTPRequestHandler) -> dict:
    """解析 POST 请求体为 dict。解析失败返回空 dict。"""
    try:
        length = int(handler.headers.get("Content-Length", 0))
    except (TypeError, ValueError):
        return {}
    if not length:
        return {}
    try:
        raw = handler.rfile.read(length).decode("utf-8")
    except Exception:
        logger.exception("读 POST body 失败")
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def safe_error_id() -> str:
    return str(uuid.uuid4())[:8]


def safe_send_json_error(handler: BaseHTTPRequestHandler, e: Exception, scope: str):
    """统一错误响应：落日志 + error_id + 500"""
    error_id = safe_error_id()
    logger.exception(f"[{scope}] {error_id} failed: {e}")
    handler._json(500, {"error": f"{scope} failed", "error_id": error_id})


# ============================================================
# Mixin：所有 handler 实例共享这些工具
# ============================================================

class HandlerBaseMixin:
    """所有 Router 用的工具方法（用 mixin 方式注入到 BaseHTTPRequestHandler）"""

    def log_message(self, fmt, *args):
        pass  # 静默标准库日志

    def _gzip_if_accepted(self, body: bytes) -> bytes:
        """🆕 v1.6.2 P1 A7：如果客户端支持 GZIP，返回压缩后的 body"""
        accept_encoding = self.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding.lower() and len(body) > 1024:
            return gzip.compress(body, compresslevel=6)
        return body

    def _json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        body = self._gzip_if_accepted(body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str):
        body = html.encode("utf-8")
        body = self._gzip_if_accepted(body)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str):
        """服务 /static/ 下的静态资源（防止路径穿越攻击）"""
        from history_footnote.web import STATIC_DIR
        rel = path[len("/static/"):]
        if ".." in rel or rel.startswith("/"):
            self._json(400, {"error": "invalid path"})
            return
        file_path = STATIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self._json(404, {"error": "not found", "path": rel})
            return
        ext = file_path.suffix
        mime = MIME_TYPES.get(ext, "application/octet-stream")
        try:
            body = file_path.read_bytes()
        except OSError:
            logger.exception("读静态文件失败: %s", file_path)
            self._json(500, {"error": "read failed"})
            return
        body = self._gzip_if_accepted(body)
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def _rate_limit_or_429(self, limiter, scope: str = "Too Many Requests") -> bool:
        """统一限流检查：被限流就返回 True 并自动写 429；通过返回 False。"""
        client_ip = self.client_address[0]
        if not limiter.allow(client_ip):
            self._json(429, {"error": scope, "limit": "see RateLimits config"})
            return True
        return False

    def _t_now(self) -> float:
        return _time.time()


def extract_last_consumed(dm_output: str, fallback: int = 1) -> tuple[bool, int]:
    """从 game_loop 的 print 输出里还原 is_action + time_cost。

    用于 /api/input 端点拿到 game._run_round 的副作用。
    """
    if "[💬 问询]" in dm_output:
        return False, 0
    m = re.search(r"本次行动消耗\s*(\d+)\s*点", dm_output)
    if m:
        return True, int(m.group(1))
    return True, fallback
