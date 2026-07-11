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

import os  # 🆕 v2.7+ LLM warmup: 读 MINIMAX_MODEL
import time  # 🆕 v2.7+ LLM warmup: 计时

from history_footnote.config import Server, GuestCookie
from history_footnote.web_enhancements import (
    GLOBAL_RATE_LIMITER,
    setup_keepalive,
)
from history_footnote.web_server.handler_base import HandlerBaseMixin

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

class Handler(HandlerBaseMixin, BaseHTTPRequestHandler):
    """HTTP handler — 只做分发，不再持有任何具体路由逻辑

    🆕 v2.7+ 继承 HandlerBaseMixin 直接拿到所有工具方法（包括 cookie 工具）
    """

    def log_message(self, fmt, *args):
        pass  # 静默

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
    setup_keepalive(Handler)
    # 🆕 v2.7+ 启动时跑一次冷存档清理（30 天未动 → _archive/）
    if GuestCookie.ARCHIVE_ON_STARTUP:
        try:
            from history_footnote.resource_cache import get_save_manager
            sm = get_save_manager()
            moved = sm.archive_inactive_sessions(within_days=GuestCookie.ARCHIVE_DAYS)
            if moved:
                logger.info(f"[v2.7] 冷存档清理：{moved} 个会话移入 _archive/")
            else:
                logger.info(f"[v2.7] 冷存档清理：无过期会话")
        except Exception as e:
            logger.warning(f"[v2.7] 冷存档清理失败（忽略）: {e}")

    # 🆕 v2.7+ 启动 LLM 预热（消除首次 /api/input 的 53.9s SSL 冷启动）
    # 原理：在 HTTP server 启动**之前**后台调一次 LLM，让 MiniMax-M3 端点的
    #       外部 SSL 路由 + 模型冷加载在玩家**看不见的时刻**完成
    # 节省：玩家首次 /api/input 从 53.9s → 10-30s
    # 风险：极低（try/except + 后台线程，主流程不受影响）
    import threading

    def _warmup_llm() -> None:
        """🆕 v2.7+ LLM 预热（后台线程）

        设计要点：
        - daemon=True → 主进程退出时自动结束
        - try/except → 任何失败都**不影响**主服务
        - 短消息 "hi" → 触发 SSL/路由/token 验证，但不消耗大量 tokens
        - 60s timeout → 避免卡死（极端情况下模型无响应）
        """
        try:
            from history_footnote.llm_providers import make_llm_for_purpose
            from history_footnote.llm_wrapper import LLMWrapper

            logger.info("[v2.7+ warmup] 启动 LLM 预热（消除首次 53.9s 冷启动）")

            # 构造主 provider 的 LLM（minimax-anthropic）
            warmup_llm = make_llm_for_purpose(
                purpose="dm",
                provider="minimax-anthropic",
                model=os.environ.get("MINIMAX_MODEL", "MiniMax-M3"),
            )

            # 用 LLMWrapper 包一层（带 timeout / fallback）
            wrapped = LLMWrapper(
                primary_provider="minimax-anthropic",
                timeout=60.0,
                retry_on_same=1,
            )

            # 调一次简短消息（"hi"），触发 SSL 路由 + 模型冷加载
            # 不传 tool schema → 避免 bind_tools 失败
            t0 = time.time()
            wrapped.invoke(
                [{"role": "user", "content": "hi"}],
                timeout=60.0,
            )
            dt = (time.time() - t0) * 1000
            logger.info(
                f"[v2.7+ warmup] ✅ LLM 预热完成（{dt:.0f}ms）"
                f"—— 首次 /api/input 不再 53.9s 冷启动"
            )
        except Exception as e:
            # 预热失败**不影响**服务启动（仅 warn log）
            logger.warning(f"[v2.7+ warmup] ⚠️ 预热失败（不影响启动）: {e}")

    # 后台线程执行预热（不阻塞主线程 / HTTP server 启动）
    threading.Thread(target=_warmup_llm, daemon=True, name="llm-warmup").start()
    logger.info("[v2.7+ warmup] LLM 预热已在后台启动（不等它完成即可接收 HTTP 请求）")

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
