"""🆕 v2.10.9 P1-2 路由签名装饰器单元测试

测试 @get_route / @post_route 装饰器 + get_route_signature 读取逻辑。

注：本测试不依赖 web_server 全套导入（避免 langchain 缺失导致链式 import 失败）。
"""
from __future__ import annotations

# 直接 import 装饰器实现（绕过 web_server/__init__.py）
from history_footnote.web_server.handler_base import (
    get_route,
    post_route,
    get_route_signature,
)


# ============================================================
# 装饰器直接形式（@get_route / @post_route）
# ============================================================

def test_get_route_decorator_default():
    @get_route
    def f(handler, query): pass
    assert get_route_signature(f) == 2


def test_get_route_decorator_no_query_true():
    @get_route(no_query=True)
    def f(handler): pass
    assert get_route_signature(f) == 1


def test_get_route_decorator_no_query_false():
    @get_route(no_query=False)
    def f(handler, query): pass
    assert get_route_signature(f) == 2


def test_post_route_decorator():
    @post_route
    def f(handler, body): pass
    assert get_route_signature(f) == 2


# ============================================================
# 装饰器工厂形式（@post_route() / @get_route(no_query=...)）
# ============================================================

def test_post_route_factory_form():
    @post_route()
    def f(handler, body): pass
    assert get_route_signature(f) == 2


def test_get_route_factory_form():
    @get_route(no_query=True)
    def f(handler): pass
    assert get_route_signature(f) == 1


# ============================================================
# 命名约定回退（无装饰器，向后兼容）
# ============================================================

def test_no_decorator_post():
    def handle_POST_input(handler, body): pass
    assert get_route_signature(handle_POST_input) == 2


def test_no_decorator_get_with_query():
    def handle_GET_eras(handler, query): pass
    assert get_route_signature(handle_GET_eras) == 2


def test_no_decorator_get_no_query_in_exceptions():
    """NO_QUERY_FNS 列表里的函数应返回 1（无 query 参数）"""
    NO_QUERY_NAMES = [
        "handle_GET_metrics",
        "handle_GET_health",
        "handle_GET_llm_reset_stats",
        "handle_GET_monitor_health",
        "handle_GET_monitor_stats",
        "handle_GET_version",
        "handle_GET_feedback_categories",
        "handle_GET_sanitize_patterns",
    ]
    for name in NO_QUERY_NAMES:
        # 动态构造函数（避免重复 def）
        f = lambda handler: None
        f.__name__ = name
        assert get_route_signature(f) == 1, f"{name} 应返回 1，实际 {get_route_signature(f)}"


def test_no_decorator_unknown_get():
    """未知 GET 函数 → 默认 2（与旧行为一致）"""
    def handle_GET_random(handler, query): pass
    assert get_route_signature(handle_GET_random) == 2


# ============================================================
# 装饰器优先级
# ============================================================

def test_decorator_priority_over_naming():
    """装饰器标记优先于命名约定"""
    # 即使名字看起来是 handle_GET_metrics（应返回 1），加了装饰器强制 2
    @get_route
    def handle_GET_metrics(handler, query): pass
    assert get_route_signature(handle_GET_metrics) == 2

    # 即使名字看起来是 handle_POST_xxx（应返回 2），加了 no_query=True 强制 1
    # （虽然 POST 理论上不能 no_query，但装饰器覆盖命名约定）
    @get_route(no_query=True)
    def handle_POST_weird(handler): pass
    assert get_route_signature(handle_POST_weird) == 1