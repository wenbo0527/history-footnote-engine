"""🆕 v2.10.1 W52 P1-3 followup: Admin Saves 模块

admin.py v1.7.30-2.10.1 段（行 233-276, 524-558）拆出。
- GET    /api/admin/saves      — 列出存档（默认所有账户；可指定 target_account_id）
- DELETE /api/admin/saves      — 删除指定存档（含 meta + 数据文件）

Auth 依赖 admin._shared 中的 helper：
- _check_admin_token / _admin_get_token / _admin_get_account_id
- _get_account_system
- logger
"""
from __future__ import annotations

from urllib.parse import parse_qs

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.routers.admin import (
    _check_admin_token,
    _admin_get_token,
    _admin_get_account_id,
    _get_account_system,
)


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