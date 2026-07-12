"""🆕 v2.10.1 W52 P1-3 followup 2: Admin Session 模块

admin.py v1.7.30-2.10.1 段（行 305-552）拆出。包含两类端点：
1. 体验版管理（v1.7.30）
   - GET  /api/admin/trials
   - POST /api/admin/grant_trial_invite
2. Admin Session 端点（v1.8.0）
   - POST /api/admin/login
   - POST /api/admin/logout
   - GET  /api/admin/whoami
   - POST /api/admin/kill_sessions

依赖：admin.* helpers（_check_admin_token / _check_session / _get_session_manager 等）
"""
from __future__ import annotations

import json

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.routers.admin import (
    _check_admin_token,
    _admin_get_token,
    _admin_get_account_id,
    _get_account_system,
    _get_account_system_local,
    _get_session_manager,
    _get_client_ip,
    _check_session,
    _check_session_with_account,
    audit_log,
)
from history_footnote.session_manager import SessionManager


# ============= 体验版管理 =============

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


# ============= Admin Session 端点 =============

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