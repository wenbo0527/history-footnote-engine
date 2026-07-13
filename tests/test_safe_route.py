"""🆕 v2.10.3 safe_route 装饰器 + dispatch 兜底测试

验证：
1. safe_route 装饰器在 handler 抛 Exception 时返回 500 + error_id
2. safe_route 不破坏正常返回（成功路径透传 bool）
3. dispatch_GET / dispatch_POST 的兜底层对未装饰 handler 同样生效
4. dispatch_GET 静态资源 / 根路径兜底
5. dispatch 对未注册 path 返回 False（不抢 Handler 的 404）
6. 🆕 v2.10.4 P3-A：低风险 router 已装饰器化 + 高风险 router 保留手写样板

依赖注意：
- 装饰器测试只依赖 handler_base.py（轻量）
- dispatch 兜底测试需要 import router_registry，会触发 web_server.__init__
  → views.session → game_loop → dm_agent → langchain_core 链
- 因此 dispatch 测试在缺 langchain_core 的环境（如精简 CI）下 skip
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from io import BytesIO
from http.server import BaseHTTPRequestHandler
from unittest.mock import MagicMock


def _has_langchain_core() -> bool:
    return importlib.util.find_spec("langchain_core") is not None


def _make_handler():
    """构造一个最小可用的 handler mock：能接收 _json 调用并记录状态"""
    h = MagicMock(spec=BaseHTTPRequestHandler)
    h.wfile = BytesIO()
    # _json 在 HandlerBaseMixin 里
    def fake_json(status, data):
        h.wfile.write(f"status={status}|data={data}".encode())
    h._json = fake_json
    return h


# 装饰器测试同样需要 handler_base，但 import 触发包 __init__ 链
@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import handler_base（包级副作用）")
class TestSafeRoute(unittest.TestCase):
    def test_success_passes_through(self):
        """成功路径：handler 自己的返回值透传"""
        from history_footnote.web_server.handler_base import safe_route

        @safe_route(scope="test_ok")
        def ok_handler(handler, body):
            handler._json(200, {"ok": True})
            return True

        h = _make_handler()
        result = ok_handler(h, {})
        self.assertTrue(result)
        self.assertIn("status=200", h.wfile.getvalue().decode())

    def test_exception_returns_500_with_error_id(self):
        """handler 抛 Exception → 500 + error_id + scope 名"""
        from history_footnote.web_server.handler_base import safe_route

        @safe_route(scope="boom")
        def boom_handler(handler, body):
            raise ValueError("intentional")

        h = _make_handler()
        result = boom_handler(h, {})
        self.assertTrue(result)
        body = h.wfile.getvalue().decode()
        self.assertIn("status=500", body)
        self.assertIn("boom failed", body)
        # error_id 8 位
        import re
        m = re.search(r"error_id':\s*'([0-9a-f]{8})'", body)
        self.assertIsNotNone(m, f"error_id not found in {body!r}")

    def test_different_exception_types_all_caught(self):
        """多种 Exception 类型都被兜住"""
        from history_footnote.web_server.handler_base import safe_route

        @safe_route(scope="multi")
        def multi_exc(handler, body):
            raise KeyError("k")

        h1 = _make_handler()
        multi_exc(h1, {})
        self.assertIn("status=500", h1.wfile.getvalue().decode())

        @safe_route(scope="multi2")
        def type_exc(handler, body):
            raise TypeError("t")

        h2 = _make_handler()
        type_exc(h2, {})
        self.assertIn("status=500", h2.wfile.getvalue().decode())

    def test_json_send_failure_silenced(self):
        """_json 自身失败 → 不二次崩溃"""
        from history_footnote.web_server.handler_base import safe_route

        @safe_route(scope="json_fail")
        def fn(handler, body):
            raise RuntimeError("x")

        h = MagicMock()
        h._json.side_effect = OSError("socket closed")
        # 不抛即通过
        result = fn(h, {})
        self.assertTrue(result)
        h._json.assert_called_once()

    def test_get_handler_one_arg(self):
        """GET handler 单参数也能装饰"""
        from history_footnote.web_server.handler_base import safe_route

        @safe_route(scope="get1")
        def get_handler(handler):
            handler._json(200, {"v": 1})
            return True

        h = _make_handler()
        result = get_handler(h)
        self.assertTrue(result)
        self.assertIn("status=200", h.wfile.getvalue().decode())


# ============================================================
# 2. dispatch 兜底层（需 langchain_core 在环境里）
# ============================================================

@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import router_registry")
class TestDispatchSafetyNet(unittest.TestCase):
    def test_dispatch_get_undecorated_handler_raises(self):
        """未装饰 handler 抛 Exception → dispatch 层兜底 500"""
        from history_footnote.web_server import router_registry

        def bad_handler(handler):
            raise RuntimeError("kaboom")

        # 直接注入
        router_registry.GET_ROUTES["/_test_dispatch_bad"] = bad_handler
        try:
            h = _make_handler()
            result = router_registry.dispatch_GET(h, "/_test_dispatch_bad", "")
            self.assertTrue(result)
            body = h.wfile.getvalue().decode()
            self.assertIn("status=500", body)
            self.assertIn("_test_dispatch_bad failed", body)
            self.assertIn("bad_handler", body)  # fn_name 应在日志里
        finally:
            router_registry.GET_ROUTES.pop("/_test_dispatch_bad", None)

    def test_dispatch_post_undecorated_handler_raises(self):
        from history_footnote.web_server import router_registry

        def bad_post(handler, body):
            raise ValueError("post boom")

        router_registry.POST_ROUTES["/_test_dispatch_post_bad"] = bad_post
        try:
            h = _make_handler()
            result = router_registry.dispatch_POST(h, "/_test_dispatch_post_bad", {})
            self.assertTrue(result)
            body = h.wfile.getvalue().decode()
            self.assertIn("status=500", body)
            self.assertIn("POST /_test_dispatch_post_bad", body)
            self.assertIn("bad_post", body)
        finally:
            router_registry.POST_ROUTES.pop("/_test_dispatch_post_bad", None)

    def test_dispatch_unknown_path_returns_false(self):
        """未注册 path → False（不抢 Handler 404）"""
        from history_footnote.web_server import router_registry

        h = _make_handler()
        result = router_registry.dispatch_GET(h, "/not_registered_path_xxx", "")
        self.assertFalse(result)
        self.assertEqual(h.wfile.getvalue(), b"")

        result = router_registry.dispatch_POST(h, "/not_registered_post_xxx", {})
        self.assertFalse(result)
        self.assertEqual(h.wfile.getvalue(), b"")

    def test_dispatch_decorated_handler_double_safe(self):
        """装饰过的 handler 抛 Exception → 装饰器先兜（dispatch 不重复 log）"""
        from history_footnote.web_server import router_registry
        from history_footnote.web_server.handler_base import safe_route

        @safe_route(scope="doubled")
        def fn(handler):
            raise RuntimeError("first")

        router_registry.GET_ROUTES["/_test_dispatch_decorated"] = fn
        try:
            h = _make_handler()
            result = router_registry.dispatch_GET(h, "/_test_dispatch_decorated", "")
            self.assertTrue(result)
            body = h.wfile.getvalue().decode()
            # 装饰器作用域优先
            self.assertIn("doubled failed", body)
            self.assertNotIn("[dispatch]", body)
        finally:
            router_registry.GET_ROUTES.pop("/_test_dispatch_decorated", None)


# ============================================================
# 3. 静态资源 / 根路径兜底（需 langchain_core）
# ============================================================

@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import router_registry")
class TestDispatchBuiltinPaths(unittest.TestCase):
    def test_static_path_404_doesnt_crash(self):
        """不存在静态资源 → 内部 404 不应崩 dispatch"""
        from history_footnote.web_server import router_registry

        h = _make_handler()
        result = router_registry.dispatch_GET(h, "/static/__nonexistent__.css", "")
        self.assertTrue(result)
        # _serve_static 内部自己 _json(404)，不应触发兜底层
        self.assertIn("status=404", h.wfile.getvalue().decode())

    def test_root_path_serves_html(self):
        from history_footnote.web_server import router_registry

        h = _make_handler()
        result = router_registry.dispatch_GET(h, "/", "")
        self.assertTrue(result)
        # html 响应 — 不一定含 "status=200" 字面，但 _html 一定不发 error
        self.assertNotIn("status=500", h.wfile.getvalue().decode())


# ============================================================
# 4. 🆕 v2.10.4 P3-A：低风险 router 装饰器化回归测试
# ============================================================

@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import handler_base（包级副作用）")
class TestP3ALowRiskRouters(unittest.TestCase):
    """P3-A 改造验证：低风险 router 已装饰器化"""

    def test_tasks_router_uses_safe_route(self):
        from history_footnote.web_server.routers import tasks
        # 装饰过的函数（@wraps）会有 __wrapped__ 属性指向原函数
        self.assertTrue(hasattr(tasks.handle_POST_task_complete, "__wrapped__"),
                        "handle_POST_task_complete 应被 @safe_route 装饰")

    def test_state_router_uses_safe_route(self):
        from history_footnote.web_server.routers import state
        self.assertTrue(hasattr(state.handle_GET_state, "__wrapped__"),
                        "handle_GET_state 应被 @safe_route 装饰")

    def test_eras_router_uses_safe_route(self):
        from history_footnote.web_server.routers import eras
        self.assertTrue(hasattr(eras.handle_GET_eras, "__wrapped__"),
                        "handle_GET_eras 应被 @safe_route 装饰")
        self.assertTrue(hasattr(eras.handle_GET_identities, "__wrapped__"),
                        "handle_GET_identities 应被 @safe_route 装饰")


@unittest.skipUnless(_has_langchain_core(), "需要 langchain_core 才能 import handler_base（包级副作用）")
class TestRemainingHandcodedEx(unittest.TestCase):
    """P3-A 决策：剩余样板保留（业务异常 / 非标 API 响应）

    验证：account.py / session.py / input.py / misc.py / chapter.py 这些 router
    仍保留 except Exception 样板（因为含业务异常或非标 API 响应）
    它们的保护由 dispatch 兜底（P1-A）承担
    """

    def test_account_module_imports(self):
        """account.py 仍存在 + register 含业务异常，保留手写样板"""
        from history_footnote.web_server.routers import account
        # account.handle_POST_account_register 不应被装饰（保留业务异常）
        # 它的 except 里有迁移逻辑 + 非标 str(e) 响应
        self.assertFalse(hasattr(account.handle_POST_account_register, "__wrapped__"),
                        "account.register 含业务异常，保留手写样板")

    def test_session_module_imports(self):
        from history_footnote.web_server.routers import session
        # v2.10.2+ session.py 只有 start/archives handler（session_load 改名了）
        # 找有 __wrapped__ 属性的：装饰器化 → 没有 __wrapped__
        # 这里验证 start 仍保留手写样板（含业务异常如 account_id 绑定）
        self.assertFalse(hasattr(session.handle_POST_start, "__wrapped__"),
                        "session.start 含业务异常（account_id 绑定 + 抽卡），保留手写样板")


if __name__ == "__main__":
    # 直接跑（CI 调用：pytest tests/test_safe_route.py）
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)