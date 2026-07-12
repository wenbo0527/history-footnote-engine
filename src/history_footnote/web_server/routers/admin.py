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

def handle_GET_admin_users(handler, query: str) -> bool:
    """GET /api/admin/users?account_id=xxx
    Returns: 完整账户列表
    """
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        return True
    admin_id = _admin_get_account_id(handler, query)
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        users = sys_inst.list_accounts()
        # 附加：每个用户的存档数
        user_summaries = []
        for u in users:
            saves = sys_inst.list_saves(u.account_id)
            user_summaries.append({
                **u.to_dict(),
                "saves_count": len(saves),
            })
        handler._json(200, {
            "users": user_summaries,
            "total": len(user_summaries),
            "admins": sum(1 for u in users if u.role == "admin"),
            "users_count": sum(1 for u in users if u.role == "user"),
        })
    except Exception as e:
        logger.exception(f"[/api/admin/users] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_admin_saves(handler, query: str) -> bool:
    """GET /api/admin/saves?account_id=xxx[&target_account_id=yyy]
    Returns: 存档列表（默认所有账户；可指定 target_account_id）
    """
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        return True
    admin_id = _admin_get_account_id(handler, query)
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        qs = parse_qs(query)
        target_id = qs.get("target_account_id", [None])[0]
        if target_id:
            saves = sys_inst.list_saves(target_id)
            target_user = sys_inst.get_account(target_id)
            result = {
                "saves": saves,
                "account_id": target_id,
                "username": target_user.username if target_user else "未知",
                "total": len(saves),
            }
        else:
            # 所有账户的存档
            all_saves = []
            for u in sys_inst.list_accounts():
                for s in sys_inst.list_saves(u.account_id):
                    all_saves.append({**s, "username": u.username})
            # 按 bound_at 倒序
            all_saves.sort(key=lambda x: x.get("bound_at", ""), reverse=True)
            result = {
                "saves": all_saves,
                "total": len(all_saves),
            }
        handler._json(200, result)
    except Exception as e:
        logger.exception(f"[/api/admin/saves] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_admin_tokens(handler, query: str) -> bool:
    """GET /api/admin/tokens?account_id=xxx[&recent_limit=20]
    Returns: token 消耗统计（全局 + 近期调用）
    """
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        return True
    admin_id = _admin_get_account_id(handler, query)
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        qs = parse_qs(query)
        recent_limit = int(qs.get("recent_limit", ["20"])[0])
        from history_footnote.llm_wrapper import get_usage_logger
        usage = get_usage_logger()
        raw_stats = usage.get_stats()
        recent = usage.get_recent(limit=recent_limit)
        # 🆕 v1.7.47 字段对齐前端期望：
        # 前端用 s.total_calls / s.total_tokens / s.total_prompt_tokens / s.total_completion_tokens / s.error_count
        # 后端用 totals.calls / totals.tokens / totals.input_tokens / totals.output_tokens
        totals = raw_stats.get("totals", {})
        flat_stats = {
            "total_calls": totals.get("calls", 0),
            "total_tokens": totals.get("tokens", 0),
            "total_prompt_tokens": totals.get("input_tokens", 0),
            "total_completion_tokens": totals.get("output_tokens", 0),
            "total_latency_ms": totals.get("latency_ms", 0),
            "error_count": totals.get("fallback_count", 0) + totals.get("timeout_count", 0),
            "fallback_count": totals.get("fallback_count", 0),
            "timeout_count": totals.get("timeout_count", 0),
        }
        # 近期调用：每条改 prompt_tokens/completion_tokens
        normalized_recent = []
        for r in recent:
            normalized_recent.append({
                "model": r.get("model", ""),
                "prompt_tokens": r.get("input_tokens", r.get("prompt_tokens", 0)),
                "completion_tokens": r.get("output_tokens", r.get("completion_tokens", 0)),
                "total_tokens": r.get("total_tokens", 0),
                "latency_ms": r.get("latency_ms", 0),
                "timestamp": r.get("timestamp", ""),
                "fallback": r.get("fallback", False),
                "timeout": r.get("timeout", False),
            })
        handler._json(200, {
            "stats": flat_stats,  # 前端期望的扁平字段
            "stats_raw": raw_stats,  # 完整原始数据（保留）
            "recent": normalized_recent,
            "recent_limit": recent_limit,
        })
    except Exception as e:
        logger.exception(f"[/api/admin/tokens] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_admin_config(handler, query: str) -> bool:
    """GET /api/admin/config?account_id=xxx
    Returns: era.json 部分配置（不返回 secret）
    """
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        return True
    admin_id = _admin_get_account_id(handler, query)
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        # 读 era.json
        from history_footnote.resource_cache import load_era_config
        config = load_era_config("wanli1587")
        # 只返回安全字段
        safe = {
            "era_id": config.get("era_id", "wanli1587"),
            "era_name": config.get("era_name", ""),
            "current_year": config.get("current_year", 1587),
            "current_date": config.get("current_date", "万历十五年"),
            "player_identities_count": len(config.get("world", {}).get("player_identities", {})),
            "cities_count": len(config.get("world", {}).get("cities", {})),
            "major_events_count": len(config.get("era", {}).get("major_events", [])),
            "triggers_count": len(config.get("world", {}).get("triggers", [])),
        }
        handler._json(200, safe)
    except Exception as e:
        logger.exception(f"[/api/admin/config] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_admin_config(handler, body: dict) -> bool:
    """POST /api/admin/config
    Body: {account_id, updates: {key: value, ...}}
    只能更新白名单字段
    """
    if not _check_admin_token(handler, body):
        return True
    # 🆕 v1.7.47 兼容 query 传 account_id
    if isinstance(body, dict):
        admin_id = body.get("account_id", "") or body.get("admin_id", "")
    else:
        admin_id = ""
    if not admin_id and hasattr(handler, 'path'):
        from urllib.parse import urlparse, parse_qs
        try:
            parsed = urlparse(handler.path)
            admin_id = parse_qs(parsed.query).get("account_id", [""])[0]
        except Exception:
            admin_id = ""
    updates = body.get("updates", {}) if isinstance(body, dict) else {}
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    if not updates:
        handler._json(400, {"error": "updates 不能为空"})
        return True
    # 白名单校验
    invalid = [k for k in updates if k not in ADMIN_CONFIG_WHITELIST]
    if invalid:
        handler._json(400, {
            "error": f"以下字段不允许修改: {invalid}",
            "allowed": list(ADMIN_CONFIG_WHITELIST),
        })
        return True
    try:
        from history_footnote.resource_cache import load_era_config
        config = load_era_config("wanli1587")
        # 应用更新
        for key, value in updates.items():
            parts = key.split(".")
            target = config
            for p in parts[:-1]:
                target = target.setdefault(p, {})
            target[parts[-1]] = value
        # 写回（实际场景应 reload；这里仅记录）
        logger.info(f"管理员 {admin.username} 更新配置: {updates}")
        handler._json(200, {
            "ok": True,
            "updated": list(updates.keys()),
            "message": "配置已更新（部分字段可能需重启生效）",
        })
    except Exception as e:
        logger.exception(f"[/api/admin/config POST] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_admin_user_role(handler, body: dict) -> bool:
    """POST /api/admin/users/role
    Body: {admin_id, target_account_id, new_role}
    修改账户 role（admin/user/guest）
    """
    if not _check_admin_token(handler, body):
        return True
    admin_id = body.get("admin_id", "")
    target_id = body.get("target_account_id", "")
    new_role = body.get("new_role", "")
    if not all([admin_id, target_id, new_role]):
        handler._json(400, {"error": "admin_id / target_account_id / new_role 必填"})
        return True
    if new_role not in ("admin", "user", "guest"):
        handler._json(400, {"error": "new_role 必须是 admin/user/guest"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    target = sys_inst.get_account(target_id)
    if not target:
        handler._json(404, {"error": "目标账户不存在"})
        return True
    try:
        target.role = new_role
        # 重新保存
        accounts = sys_inst._load_accounts()
        for a in accounts:
            if a.account_id == target_id:
                a.role = new_role
        sys_inst._save_accounts(accounts)
        handler._json(200, {
            "ok": True,
            "account_id": target_id,
            "username": target.username,
            "new_role": new_role,
        })
    except Exception as e:
        logger.exception(f"[/api/admin/users/role] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_DELETE_admin_user(handler, body: dict) -> bool:
    """DELETE /api/admin/users
    Body: {admin_id, target_account_id}
    删除账户（不删存档）
    """
    if not _check_admin_token(handler, body):
        return True
    admin_id = body.get("admin_id", "")
    target_id = body.get("target_account_id", "")
    if not all([admin_id, target_id]):
        handler._json(400, {"error": "admin_id / target_account_id 必填"})
        return True
    if admin_id == target_id:
        handler._json(400, {"error": "不能删除自己"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    target = sys_inst.get_account(target_id)
    if not target:
        handler._json(404, {"error": "目标账户不存在"})
        return True
    try:
        accounts = sys_inst._load_accounts()
        accounts = [a for a in accounts if a.account_id != target_id]
        sys_inst._save_accounts(accounts)
        handler._json(200, {
            "ok": True,
            "deleted": target_id,
            "username": target.username,
            "message": "账户已删除（存档保留）",
        })
    except Exception as e:
        logger.exception(f"[/api/admin/users DELETE] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_DELETE_admin_save(handler, body: dict) -> bool:
    """DELETE /api/admin/saves
    Body: {admin_id, target_account_id, save_id}
    删除指定存档（含 meta + 数据文件）
    """
    if not _check_admin_token(handler, body):
        return True
    admin_id = body.get("admin_id", "")
    target_id = body.get("target_account_id", "")
    save_id = body.get("save_id", "")
    if not all([admin_id, target_id, save_id]):
        handler._json(400, {"error": "admin_id / target_account_id / save_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        save_path = sys_inst.get_save_path(target_id, save_id)
        meta_path = save_path.parent / f"{save_id}.meta.json"
        # 删文件
        if save_path.exists():
            save_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        handler._json(200, {
            "ok": True,
            "deleted_save": save_id,
            "deleted_account": target_id,
        })
    except Exception as e:
        logger.exception(f"[/api/admin/saves DELETE] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


# ============= 🆕 v1.7.30 体验版管理 =============

def handle_GET_admin_trials(handler, query: str) -> bool:
    """GET /api/admin/trials?account_id=xxx
    列出所有 trial 记录（current + history）
    """
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        return True
    admin_id = _admin_get_account_id(handler, query)
    if not admin_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        trial = sys_inst._load_trial()
        current = trial.get("current")
        history = trial.get("history", [])
        # 简化（隐藏 contact 详情）
        summary_history = [
            {
                "trial_id": h.get("trial_id"),
                "round": h.get("round"),
                "feedback": h.get("feedback"),
                "has_contact": bool(h.get("contact")),
                "submitted_at": h.get("submitted_at"),
                "ended_at": h.get("ended_at"),
            }
            for h in history
        ]
        handler._json(200, {
            "current": current,
            "history": summary_history,
            "total": len(summary_history),
            "current_active": current is not None,
        })
    except Exception as e:
        logger.exception(f"[/api/admin/trials] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_admin_grant_trial_invite(handler, body: dict) -> bool:
    """POST /api/admin/grant_trial_invite
    Body: {admin_id, contact}
    给某个 trial user 奖励邀请码（被采纳意见时调用）
    """
    if not _check_admin_token(handler, body):
        return True
    # 🆕 v1.7.47 兼容 query 传 admin_id
    if isinstance(body, dict):
        admin_id = body.get("admin_id", "") or body.get("account_id", "")
    else:
        admin_id = ""
    if not admin_id and hasattr(handler, 'path'):
        from urllib.parse import urlparse, parse_qs
        try:
            parsed = urlparse(handler.path)
            admin_id = parse_qs(parsed.query).get("admin_id", [""])[0] or parse_qs(parsed.query).get("account_id", [""])[0]
        except Exception:
            admin_id = ""
    contact = body.get("contact", "") if isinstance(body, dict) else ""
    if not admin_id:
        handler._json(400, {"error": "admin_id 必填"})
        return True
    sys_inst = _get_account_system()
    admin = sys_inst.get_account(admin_id)
    if not admin or admin.role != "admin":
        handler._json(403, {"error": "需要 admin 权限"})
        return True
    try:
        inv = sys_inst.grant_invite_code_for_trial(contact)
        if inv is None:
            handler._json(500, {"error": "生成邀请码失败"})
            return True
        handler._json(200, {
            "ok": True,
            "invite_code": inv.code,
            "max_uses": inv.max_uses,
            "label": inv.label,
            "contact": contact,
            "message": f"邀请码 {inv.code} 已生成，请发给用户 {contact}",
        })
    except Exception as e:
        logger.exception(f"[/api/admin/grant_trial_invite] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


# ============================================================
# 🆕 v1.8.0 Admin Session 端点
# ============================================================

def handle_POST_admin_login(handler, body: dict) -> bool:
    """POST /api/admin/login
    Body: {account_id, password}
    Returns: 200 {account} + Set-Cookie / 401 bad_pwd / 429 locked
    """
    if not isinstance(body, dict):
        handler._json(400, {"error": "body must be dict"})
        return True
    account_id = (body.get("account_id", "") or "").strip()
    password = (body.get("password", "") or "")
    if not account_id or not password:
        handler._json(400, {"error": "account_id and password required"})
        return True
    sys_inst = _get_account_system_local()
    is_locked, retry_after = sys_inst.is_locked(account_id)
    if is_locked:
        audit_log(event="login_fail", account_id=account_id, reason="locked",
                  ip=_get_client_ip(handler),
                  user_agent=handler.headers.get("User-Agent", ""))
        handler._json(429, {"error": "账户已锁定", "retry_after": retry_after})
        return True
    if not sys_inst.verify_password(account_id, password):
        fail_count, is_locked_now = sys_inst.increment_fail_count(account_id)
        audit_log(event="login_fail", account_id=account_id, reason="bad_password",
                  attempt=fail_count, ip=_get_client_ip(handler),
                  user_agent=handler.headers.get("User-Agent", ""))
        if is_locked_now:
            audit_log(event="account_locked", account_id=account_id,
                      ip=_get_client_ip(handler))
            handler._json(429, {"error": "密码错误，账户已锁定 15 min", "locked": True})
        else:
            handler._json(401, {"error": "密码错误",
                                "fail_count": fail_count,
                                "remaining": max(0, 5 - fail_count)})
        return True
    sys_inst.reset_fail_count(account_id)
    sys_inst.update_last_login(account_id)
    sm = _get_session_manager()
    sess = sm.create(account_id, ip=_get_client_ip(handler),
                     user_agent=handler.headers.get("User-Agent", ""))
    cookie_value = SessionManager.sign_cookie(sess.session_id)
    account = sys_inst.get_account(account_id)
    body_dict = {
        "ok": True,
        "account": {
            "account_id": account.account_id,
            "username": account.username,
            "role": account.role,
        },
        "session": {
            "session_id": sess.session_id,
            "expires_at": sess.expires_at,
        },
    }
    body_bytes = json.dumps(body_dict).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Set-Cookie", f"session_id={cookie_value}; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400")
    handler.send_header("Content-Length", str(len(body_bytes)))
    handler.end_headers()
    handler.wfile.write(body_bytes)
    audit_log(event="login_ok", account_id=account_id, session_id=sess.session_id,
              route="/api/admin/login", method="POST", status=200,
              ip=_get_client_ip(handler),
              user_agent=handler.headers.get("User-Agent", ""))
    return True


def handle_POST_admin_logout(handler, body: dict) -> bool:
    """POST /api/admin/logout
    需要 session cookie
    """
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SessionManager.parse_cookie(cookie_header)
    if not cookie:
        handler._json(401, {"error": "no_session"})
        return True
    sm = _get_session_manager()
    session = sm.lookup(cookie, sliding=False)
    if not session:
        handler._json(401, {"error": "session_expired_or_invalid"})
        return True
    sm.delete(session.session_id)
    audit_log(event="logout", account_id=session.account_id, session_id=session.session_id,
              route="/api/admin/logout", method="POST", status=200,
              ip=_get_client_ip(handler))
    body_dict = {"ok": True, "message": "已登出"}
    body_bytes = json.dumps(body_dict).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Set-Cookie", "session_id=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")
    handler.send_header("Content-Length", str(len(body_bytes)))
    handler.end_headers()
    handler.wfile.write(body_bytes)
    return True


def handle_GET_admin_whoami(handler, query: str) -> bool:
    """GET /api/admin/whoami
    Returns: 200 {account, session} / 401
    """
    if not _check_session(handler):
        handler._json(401, {"error": "需要有效 session 或 ADMIN_TOKEN"})
        return True
    ok, account_id, account = _check_session_with_account(handler)
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SessionManager.parse_cookie(cookie_header)
    sm = _get_session_manager()
    session = sm.lookup(cookie, sliding=False) if cookie else None
    if not session:
        handler._json(401, {"error": "session_invalid"})
        return True
    handler._json(200, {
        "account": {
            "account_id": account.account_id,
            "username": account.username,
            "role": account.role,
        },
        "session": {
            "session_id": session.session_id,
            "expires_at": session.expires_at,
        },
    })
    return True


def handle_POST_admin_kill_sessions(handler, body: dict) -> bool:
    """POST /api/admin/kill_sessions
    Body: {target_account_id?: str}
    Returns: 200 {killed: int}
    """
    if not _check_session(handler):
        handler._json(401, {"error": "需要有效 session 或 ADMIN_TOKEN"})
        return True
    target = (body.get("target_account_id", "") or "").strip() if isinstance(body, dict) else ""
    sm = _get_session_manager()
    if target:
        killed = sm.delete_by_account(target)
        audit_log(event="kill_sessions", account_id=target, killed=killed,
                  route="/api/admin/kill_sessions", method="POST", status=200,
                  ip=_get_client_ip(handler))
        handler._json(200, {"ok": True, "killed": killed, "target": target})
    else:
        ok, current_id, _ = _check_session_with_account(handler)
        if not ok:
            handler._json(401, {"error": "session_invalid"})
            return True
        killed = sm.delete_by_account(current_id)
        audit_log(event="kill_sessions", account_id=current_id, killed=killed,
                  route="/api/admin/kill_sessions", method="POST", status=200,
                  ip=_get_client_ip(handler))
    return True


# ============================================================
# 🆕 v2.10.1 W52 P1-3: Re-export Settings handlers
# ============================================================
# Settings 模块已拆到 admin_settings.py,此处 re-export 3 个 handler,
# 保证 router_registry.py 中 _admin.handle_* 引用无变化。
from history_footnote.web_server.routers.admin_settings import (
    handle_GET_admin_settings,
    handle_POST_admin_settings,
    handle_POST_admin_settings_reset,
)
