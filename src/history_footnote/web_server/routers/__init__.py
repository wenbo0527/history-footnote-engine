"""🆕 v1.7.29 routers 子包 — 把 web_server.py 的 do_GET / do_POST 路由分发拆成独立模块。

每个模块提供 handle_GET(handler, path, query_string) / handle_POST(handler, path, body) 函数，
由 web_server.Handler 在 do_GET / do_POST 中按 path 前缀调用。

设计原则：
- 每路由完成一件事
- 异常时统一返回 500 + error_id（落日志）
- 不构造 GameLoop（统一用 views/session.py 的工具）
- 不直接调 self.client_address 之类基础设施，用 handler 的 _rate_limit_or_429
"""
