"""🆕 v1.7.29 web_server 子包

历史背景：
- 之前 web_server.py 单文件 1429 行，承担 HTTP 路由 + 序列化 + 静态资源 + LLM 流式 + 任务管理
- v1.7.29 拆为 router-group 结构

结构：
- web_server/handler_base.py — _json / _html / _gzip / _serve_static / 限流工具
- web_server/static_assets.py — INDEX_HTML 加载
- web_server/views/format_state.py — 状态序列化
- web_server/views/session.py — Session 池接口
- web_server/routers/{state,session,input,tasks,glossary,misc,character,eras,observability}.py
- web_server/router_registry.py — 路由注册表 + dispatch

100% 向后兼容：
- `from history_footnote.web_server import _format_state, _session_get, INDEX_HTML, Handler, run` 仍然 work
- 所有外部脚本（CI/测试/OpenAPI 生成器）无需改动

如何兼容：Python 同名时优先选包。本模块把 web_server.py 的所有公共符号 re-export。
"""
from __future__ import annotations

# ============================================================
# 模块级单例 — web_server.py 原原本本搬到本包
# ============================================================

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from history_footnote.config import Server
from history_footnote.web_enhancements import (
    GLOBAL_RATE_LIMITER,
    setup_keepalive,
)

# ===== Views（状态序列化层） =====
from history_footnote.web_server.views.format_state import (
    build_sidebar_data as _build_sidebar_data,
    detect_intent as _detect_intent_for_response,
    format_state as _format_state,
    render_wiki_summary_safe as _render_wiki_summary_safe,
)

# ===== Views（session 池接口） =====
from history_footnote.web_server.views.session import (
    _get_or_load_session,
    new_session as _new_session,
    session_get as _session_get,
    session_pop as _session_pop,
    session_set as _session_set,
)

# ===== Static assets =====
from history_footnote.web_server.static_assets import INDEX_HTML

# ===== Logger =====
from history_footnote.web_server.handler_base import logger

# ===== Router registry =====
from history_footnote.web_server.router_registry import dispatch_GET, dispatch_POST


# ============================================================
# Handler 类：路由分发入口（依赖 dispatch_GET / dispatch_POST）
# ============================================================

class Handler(BaseHTTPRequestHandler):
    """HTTP handler — 只做分发，不再持有任何具体路由逻辑"""

    def log_message(self, fmt, *args):
        pass  # 静默

    # --- 工具方法（从 handler_base 拷贝到实例以保持兼容） ---

    def _gzip_if_accepted(self, body: bytes) -> bytes:
        from history_footnote.web_server.handler_base import HandlerBaseMixin
        return HandlerBaseMixin._gzip_if_accepted(self, body)

    def _json(self, status: int, data: dict):
        from history_footnote.web_server.handler_base import HandlerBaseMixin
        return HandlerBaseMixin._json(self, status, data)

    def _html(self, html: str):
        from history_footnote.web_server.handler_base import HandlerBaseMixin
        return HandlerBaseMixin._html(self, html)

    def _serve_static(self, path: str):
        from history_footnote.web_server.handler_base import HandlerBaseMixin
        return HandlerBaseMixin._serve_static(self, path)

    def _rate_limit_or_429(self, limiter, scope: str = "Too Many Requests"):
        from history_footnote.web_server.handler_base import HandlerBaseMixin
        return HandlerBaseMixin._rate_limit_or_429(self, limiter, scope)

    # --- 路由分发 ---

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parsed.query
        if not GLOBAL_RATE_LIMITER.allow(self.client_address[0]):
            self._json(429, {"error": "Too Many Requests", "limit": "60 req/min"})
            return
        if not dispatch_GET(self, path, query):
            self._json(404, {"error": "not found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        from history_footnote.web_server.handler_base import parse_request_body
        body = parse_request_body(self)
        if not GLOBAL_RATE_LIMITER.allow(self.client_address[0]):
            self._json(429, {"error": "Too Many Requests", "limit": "60 req/min"})
            return
        if not dispatch_POST(self, path, body):
            self._json(404, {"error": "not found", "method": "POST", "path": path})


# ============================================================
# 入口函数 run()
# ============================================================

def run(host: str = "0.0.0.0", port: int = Server.DEFAULT_PORT):
    """启动 web 服务器（开发用）"""
    setup_keepalive()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"🎭 历史注脚体验引擎 已启动")
    print(f"   地址: http://{host}:{port}/")
    print(f"   按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务停止")
        server.shutdown()


# ============================================================
# 模块入口：保留 `python -m history_footnote.web_server` 调用方式
# ============================================================

if __name__ == "__main__":
    run()
