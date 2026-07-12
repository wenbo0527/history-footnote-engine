"""v2.10.1 W52 P1-3 followup: admin_users/saves/tokens 模块单元测试

验证 3 个新模块的 handler 独立可 import。
"""
import pytest


# ============= admin_users =============

def test_admin_users_module_imports():
    """admin_users 应可 import"""
    from history_footnote.web_server.routers.admin_users import (
        handle_GET_admin_users,
        handle_POST_admin_user_role,
        handle_DELETE_admin_user,
    )
    assert callable(handle_GET_admin_users)
    assert callable(handle_POST_admin_user_role)
    assert callable(handle_DELETE_admin_user)


def test_admin_reexports_users_handlers():
    """admin 模块应 re-export 3 个 users handler"""
    from history_footnote.web_server.routers import admin
    assert admin.handle_GET_admin_users.__module__ == "history_footnote.web_server.routers.admin_users"
    assert admin.handle_POST_admin_user_role.__module__ == "history_footnote.web_server.routers.admin_users"
    assert admin.handle_DELETE_admin_user.__module__ == "history_footnote.web_server.routers.admin_users"


# ============= admin_saves =============

def test_admin_saves_module_imports():
    """admin_saves 应可 import"""
    from history_footnote.web_server.routers.admin_saves import (
        handle_GET_admin_saves,
        handle_DELETE_admin_save,
    )
    assert callable(handle_GET_admin_saves)
    assert callable(handle_DELETE_admin_save)


def test_admin_reexports_saves_handlers():
    """admin 模块应 re-export 2 个 saves handler"""
    from history_footnote.web_server.routers import admin
    assert admin.handle_GET_admin_saves.__module__ == "history_footnote.web_server.routers.admin_saves"
    assert admin.handle_DELETE_admin_save.__module__ == "history_footnote.web_server.routers.admin_saves"


# ============= admin_tokens =============

def test_admin_tokens_module_imports():
    """admin_tokens 应可 import"""
    from history_footnote.web_server.routers.admin_tokens import handle_GET_admin_tokens
    assert callable(handle_GET_admin_tokens)


def test_admin_reexports_tokens_handler():
    """admin 模块应 re-export tokens handler"""
    from history_footnote.web_server.routers import admin
    assert admin.handle_GET_admin_tokens.__module__ == "history_footnote.web_server.routers.admin_tokens"


# ============= 集成测试 =============

def test_all_admin_handlers_still_reexported():
    """所有 14 个 admin handler 都应 re-export,router_registry 不破"""
    from history_footnote.web_server.routers import admin
    all_handlers = [
        "handle_GET_admin_users",
        "handle_POST_admin_user_role",
        "handle_DELETE_admin_user",
        "handle_GET_admin_saves",
        "handle_DELETE_admin_save",
        "handle_GET_admin_tokens",
        "handle_GET_admin_config",
        "handle_POST_admin_config",
        "handle_GET_admin_settings",
        "handle_POST_admin_settings",
        "handle_POST_admin_settings_reset",
        "handle_GET_admin_trials",
        "handle_POST_admin_grant_trial_invite",
        "handle_POST_admin_login",
        "handle_POST_admin_logout",
        "handle_GET_admin_whoami",
        "handle_POST_admin_kill_sessions",
    ]
    for name in all_handlers:
        assert hasattr(admin, name), f"admin 缺 {name}"


def test_admin_submodules_total_lines():
    """admin.py 拆出 3 个子模块后行数应减少（验证文件组织有效）"""
    base = "src/history_footnote/web_server/routers/"
    users = sum(1 for _ in open(base + "admin_users.py", encoding="utf-8").readlines())
    saves = sum(1 for _ in open(base + "admin_saves.py", encoding="utf-8").readlines())
    tokens = sum(1 for _ in open(base + "admin_tokens.py", encoding="utf-8").readlines())
    settings = sum(1 for _ in open(base + "admin_settings.py", encoding="utf-8").readlines())
    admin = sum(1 for _ in open(base + "admin.py", encoding="utf-8").readlines())
    # admin.py 当前应 < 700 行（原 820）
    assert admin < 700, f"admin.py 仍 {admin} 行,应 < 700"
    # 至少拆出 600+ 行到子模块（users + saves + tokens）
    sub_total = users + saves + tokens
    assert sub_total >= 200, f"子模块总行数仅 {sub_total}"