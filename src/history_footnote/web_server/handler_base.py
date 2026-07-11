"""🆕 v1.7.29 Handler 基础设施

包含所有路由 handler 都依赖的工具方法（_json / _html / _gzip / _serve_static 等）
与限流工具。
"""
from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import logging
import re
import time as _time
import uuid
import base64
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
# 🆕 v2.7+ 签名 Cookie 工具
# ============================================================

import secrets
import os as _os
from history_footnote.config import GuestCookie as _GuestCookie

# 模块级：开发 fallback secret（仅当 GuestCookie.SECRET 为空时使用，并 warning 一次）
_DEV_FALLBACK_SECRET = "hfe-dev-only-insecure-" + _os.path.basename(_os.getcwd())
_SECRET_WARNED = False


def _get_cookie_secret() -> bytes:
    """获取 cookie 签名密钥"""
    global _SECRET_WARNED
    secret = _GuestCookie.SECRET
    if not secret:
        secret = _DEV_FALLBACK_SECRET
        if not _SECRET_WARNED:
            logger.warning(
                "[v2.7] WEB_COOKIE_SECRET 未设置，使用开发 fallback 密钥"
                "（生产环境必须设置！请用 `python -c 'import secrets; print(secrets.token_hex(32))'` 生成）"
            )
            _SECRET_WARNED = True
    return secret.encode("utf-8") if isinstance(secret, str) else secret


def _sign_cookie_value(raw: str) -> str:
    """生成 cookie 值：base64url(raw) + "." + base64url(hmac_sha256(raw, secret))"""
    payload = base64.urlsafe_b64encode(raw.encode("utf-8")).rstrip(b"=").decode("ascii")
    sig = hmac.new(_get_cookie_secret(), raw.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{payload}.{sig_b64}"


def _verify_cookie_value(signed: str) -> str | None:
    """验证签名 cookie 值，失败返回 None"""
    if not signed or "." not in signed:
        return None
    try:
        payload_b64, sig_b64 = signed.rsplit(".", 1)
        # 还原 base64 padding
        payload_b64 += "=" * (-len(payload_b64) % 4)
        sig_b64 += "=" * (-len(sig_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8")
        expected_sig = hmac.new(_get_cookie_secret(), raw.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64.encode("ascii"))
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        return raw
    except Exception:
        return None


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

    def _json_with_cookies(self, status: int, data: dict, cookies: list[str] | None = None):
        """🆕 v2.7+ 写 JSON 响应 + 多个 Set-Cookie header

        cookies: 额外要发的 Set-Cookie 字符串列表（不传就用 self._pending_set_cookies）
        """
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        body = self._gzip_if_accepted(body)
        all_cookies = list(getattr(self, "_pending_set_cookies", []))
        if cookies:
            all_cookies.extend(cookies)
        self.send_response(status)
        for c in all_cookies:
            self.send_header("Set-Cookie", c)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        # 清空暂存
        self._pending_set_cookies = []

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

    def setup(self):
        """🆕 v2.7+ 每个请求初始化 _pending_set_cookies

        BaseHTTPRequestHandler.setup() 在 do_GET 之前调用。
        """
        super().setup() if hasattr(super(), 'setup') else None
        self._pending_set_cookies = []

    # --- 🆕 v2.7+ 签名 Cookie 工具（handler 实例方法） ---

    def _read_cookie(self, name: str) -> str | None:
        """从 Cookie 头读指定 name 的值

        Returns: raw cookie value（未验签），或 None
        """
        raw = self.headers.get("Cookie", "")
        if not raw:
            return None
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                if k.strip() == name:
                    return v.strip()
        return None

    def _set_signed_cookie(
        self, name: str, value: str, max_age: int | None = None,
        secure: bool | None = None, samesite: str | None = None,
        httponly: bool = True,
    ) -> None:
        """Set-Cookie 签名值（HttpOnly 默认 true，防 XSS）

        Args:
            name: cookie 名
            value: 原始值（会被签名）
            max_age: 秒；None 用 GuestCookie.MAX_AGE
            secure: None 用 GuestCookie.SECURE
            samesite: None 用 GuestCookie.SAMESITE
            httponly: 默认 True
        """
        if max_age is None:
            max_age = _GuestCookie.MAX_AGE
        if secure is None:
            secure = _GuestCookie.SECURE
        if samesite is None:
            samesite = _GuestCookie.SAMESITE

        signed = _sign_cookie_value(value)
        cookie_parts = [
            f"{name}={signed}",
            "Path=/",
            f"Max-Age={max_age}",
        ]
        if httponly:
            cookie_parts.append("HttpOnly")
        if secure:
            cookie_parts.append("Secure")
        if samesite:
            cookie_parts.append(f"SameSite={samesite}")
        self.send_header("Set-Cookie", "; ".join(cookie_parts))

    def _clear_signed_cookie(self, name: str) -> None:
        """Set-Cookie 清空（Max-Age=0）"""
        self.send_header("Set-Cookie", f"{name}=; Path=/; Max-Age=0; HttpOnly")

    def _get_or_create_guest_id(self) -> str:
        """🆕 v2.7+ 从 cookie 拿 guest_id；无效则创建（cookie 写到 _pending_cookies）

        优先级：Cookie > 现有 account

        Returns: guest_xxx 形式 ID

        注意：这里**不**直接 send_header(Set-Cookie)，而是把 Set-Cookie 字符串
        暂存到 self._pending_cookies，调用方通过 _json_with_cookies 一起发送。
        BaseHTTPRequestHandler 的 send_header 必须在 send_response 之后才会生效，
        所以不能在 helper 阶段直接调 send_header。
        """
        signed = self._read_cookie(_GuestCookie.NAME)
        if signed:
            raw = _verify_cookie_value(signed)
            if raw and raw.startswith("guest_"):
                return raw
        # 没有/无效 → 创建
        from history_footnote.account_system import AccountSystem
        from history_footnote.web_server.views.session import _storage_root_for_account
        sys_inst = AccountSystem(storage_root=_storage_root_for_account())
        guest = sys_inst.create_guest()
        # 暂存 Set-Cookie（不在 helper 里直接 send_header）
        self._pending_set_cookies.append(self._build_signed_cookie_header(_GuestCookie.NAME, guest.account_id))
        return guest.account_id

    def _build_signed_cookie_header(self, name: str, value: str,
                                     max_age: int | None = None,
                                     secure: bool | None = None,
                                     samesite: str | None = None,
                                     httponly: bool = True) -> str:
        """构造 Set-Cookie 字符串（不发 header）"""
        if max_age is None:
            max_age = _GuestCookie.MAX_AGE
        if secure is None:
            secure = _GuestCookie.SECURE
        if samesite is None:
            samesite = _GuestCookie.SAMESITE
        signed = _sign_cookie_value(value)
        parts = [f"{name}={signed}", "Path=/", f"Max-Age={max_age}"]
        if httponly:
            parts.append("HttpOnly")
        if secure:
            parts.append("Secure")
        if samesite:
            parts.append(f"SameSite={samesite}")
        return "; ".join(parts)

    def _get_guest_id_from_cookie_or_query(self, query: str = "") -> str:
        """🆕 v2.7+ 从 cookie 优先拿 ID；fallback 到 query 参数

        用于向后兼容：老前端仍传 ?account_id=xxx
        """
        signed = self._read_cookie(_GuestCookie.NAME)
        if signed:
            raw = _verify_cookie_value(signed)
            if raw:
                return raw
        # 退到 query
        if query:
            qs = parse_qs(query)
            qs_aid = qs.get("account_id", [""])[0] or qs.get("account", [""])[0]
            if qs_aid:
                return qs_aid
        # 都没有 → 创建 + Set-Cookie
        return self._get_or_create_guest_id()


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
