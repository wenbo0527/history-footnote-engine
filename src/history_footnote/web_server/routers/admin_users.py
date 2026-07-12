"""🆕 v2.10.1 W52 P1-3 followup: Admin Users 模块

admin.py v1.7.30-2.10.1 段（行 196-230, 439-521）拆出。
- GET  /api/admin/users           — 列出所有账户
- POST /api/admin/users/role      — 修改账户 role
- DELETE /api/admin/users         — 删除账户

Auth 依赖 admin._shared 中的 helper：
- _check_admin_token / _admin_get_token / _admin_get_account_id
- _get_account_system
- audit_log / logger
"""
from __future__ import annotations

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.routers.admin import (
    _check_admin_token,
    _admin_get_token,
    _admin_get_account_id,
    _get_account_system,
)


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