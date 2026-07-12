"""🆕 v1.7.30 管理员 API

GET  /api/admin/users           — 列出所有账户
GET  /api/admin/saves           — 列出所有存档
GET  /api/admin/tokens          — token 消耗统计
GET  /api/admin/config          — 读 era.json 配置
POST /api/admin/config          — 热更新部分字段
POST /api/admin/users/{id}/role — 修改账户 role
DELETE /api/admin/users/{id}    — 删除账户（含存档）
POST /api/admin/saves/delete    — 删除指定存档

认证：所有路由需 account_id 且 role=admin

🆕 v2.10.1 W52 P1-3: Settings 模块拆到 admin_settings.py
（GET/POST /api/admin/settings + reset，~170 行）
本文件末尾 re-export 这 3 个 handler，保证 router_registry 无需改动。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs

from history_footnote.account_system import AccountSystem
from history_footnote.session_manager import SessionManager
from history_footnote.audit import audit_log
from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.session import _storage_root_for_account


# 🆕 v1.8.0 SessionManager 单例
_SESSION_MANAGER_SINGLETON: SessionManager | None = None


def _get_session_manager() -> SessionManager:
    """获取 SessionManager 单例"""
    global _SESSION_MANAGER_SINGLETON
    if _SESSION_MANAGER_SINGLETON is None:
        storage_root = Path(os.environ.get("SESSION_STORAGE_ROOT", "saves"))
        _SESSION_MANAGER_SINGLETON = SessionManager(storage_root=storage_root)
    return _SESSION_MANAGER_SINGLETON


# 允许热更新的 era.json 字段（白名单，避免误改）
ADMIN_CONFIG_WHITELIST = {
    "era.era_name",
    "era.description",
    "era.major_events",  # 管理员可调整大事件时间
    "world.economy.silver_inflow",
    "world.bureaucracy.key_rule",
}


def _get_account_system() -> AccountSystem:
    storage_root = _storage_root_for_account()
    key = str(storage_root)
    # 全局单例（与 routers/account.py 共享）
    from history_footnote.web_server.routers.account import _get_account_system
    return _get_account_system(storage_root)


def _require_admin(handler, body_or_query: dict) -> tuple[bool, str | None]:
    """验证 admin 权限（v1.7.46+ 必须通过 token + admin role 双检）
    Returns: (is_admin, account_id)
    """
    if not _check_admin_token(handler, body_or_query):
        return False, None
    account_id = body_or_query.get("account_id") or ""
    if not account_id:
        return False, "account_id 必填"
    sys_inst = _get_account_system()
    account = sys_inst.get_account(account_id)
    if account is None:
        return False, "账户不存在"
    if account.role != "admin":
        return False, "需要 admin 权限"
    return True, account_id


def _admin_get_account_id(handler, query: str) -> str | None:
    """从 query 拿 account_id"""
    qs = parse_qs(query)
    return qs.get("account_id", [None])[0]


def _admin_get_token(handler, query: str) -> str:
    """从 query 拿 token"""
    qs = parse_qs(query)
    return qs.get("token", [""])[0] or ""


# 🆕 v1.8.0 Session 鉴权

def _get_client_ip(handler) -> str:
    """从 X-Forwarded-For 头取 client IP（nginx 已配）"""
    return handler.headers.get("X-Forwarded-For", "").split(",")[0].strip() or handler.client_address[0] if hasattr(handler, "client_address") else ""


def _get_session_from_request(handler) -> tuple[bool, str, str]:
    """从请求提取 session cookie 并验证

    Returns:
        (ok, cookie_value, error_msg)
    """
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SessionManager.parse_cookie(cookie_header)
    if not cookie:
        return False, "", "no_session_cookie"
    return True, cookie, ""


def _check_session(handler) -> bool:
    """🆕 v1.8.0 检查 session cookie

    Returns:
        True=通过（session 有效 + 账户是 admin）
        False=未通过（已写 401 拒绝）
    """
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SessionManager.parse_cookie(cookie_header)
    if not cookie:
        return False  # 无 cookie，让 _check_admin_token 回退
    sm = _get_session_manager()
    session = sm.lookup(cookie, sliding=True)
    if not session:
        # 写 audit session_expired
        audit_log(event="session_expired", ip=_get_client_ip(handler),
                  user_agent=handler.headers.get("User-Agent", ""))
        return False
    # 检查 role
    sys_inst = _get_account_system_local()
    account = sys_inst.get_account(session.account_id)
    if not account or account.role != "admin":
        return False
    return True


def _check_session_with_account(handler) -> tuple[bool, str, object]:
    """🆕 v1.8.0 检查 session + 返回 account

    Returns:
        (ok, account_id, account_or_none)
    """
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SessionManager.parse_cookie(cookie_header)
    if not cookie:
        return False, "", None
    sm = _get_session_manager()
    session = sm.lookup(cookie, sliding=True)
    if not session:
        return False, "", None
    sys_inst = _get_account_system_local()
    account = sys_inst.get_account(session.account_id)
    if not account or account.role != "admin":
        return False, session.account_id, account
    return True, session.account_id, account


def _get_account_system_local():
    """🆕 v1.8.0 每次新建 AccountSystem（不缓存）"""
    return AccountSystem(storage_root=Path("saves"))


def _check_admin_token(handler, params: dict) -> bool:
    """🆕 v1.7.46 鉴权加固：所有 admin 路由需 ADMIN_TOKEN
    Returns: True=通过；False=已写 401/500 拒绝
    优先级：body.token > X-Admin-Token header

    🆕 v1.8.0 双轨制：
    - 优先 cookie (session)
    - 回退 ADMIN_TOKEN header（保 v1.7.47 脚本兼容）
    """
    # 1. 先尝试 session cookie
    if _check_session(handler):
        return True
    # 2. 回退 ADMIN_TOKEN
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        logger.exception("[/api/admin/*] ADMIN_TOKEN 未配置且无 session")
        handler._json(500, {"error": "服务器未配置 ADMIN_TOKEN"})
        return False
    provided = (
        params.get("token", "")
        or handler.headers.get("X-Admin-Token", "")
    )
    if provided != expected:
        handler._json(401, {"error": "需要有效 token"})
        return False
    return True


# ============= 路由 =============



# ============================================================
# 🆕 v2.10.1 W52 P1-3: Re-export 所有已拆 handler
# ============================================================
# 6 个子模块已拆出,admin.py 只保留 helper + 此处 re-export
# 保证 router_registry.py 中 _admin.handle_* 引用无变化

from history_footnote.web_server.routers.admin_settings import (
    handle_GET_admin_settings,
    handle_POST_admin_settings,
    handle_POST_admin_settings_reset,
)
from history_footnote.web_server.routers.admin_users import (
    handle_GET_admin_users,
    handle_POST_admin_user_role,
    handle_DELETE_admin_user,
)
from history_footnote.web_server.routers.admin_saves import (
    handle_GET_admin_saves,
    handle_DELETE_admin_save,
)
from history_footnote.web_server.routers.admin_tokens import (
    handle_GET_admin_tokens,
)
from history_footnote.web_server.routers.admin_config import (
    handle_GET_admin_config,
    handle_POST_admin_config,
)
from history_footnote.web_server.routers.admin_session import (
    handle_GET_admin_trials,
    handle_POST_admin_grant_trial_invite,
    handle_POST_admin_login,
    handle_POST_admin_logout,
    handle_GET_admin_whoami,
    handle_POST_admin_kill_sessions,
)
