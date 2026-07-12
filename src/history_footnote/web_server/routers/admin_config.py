"""🆕 v2.10.1 W52 P1-3 followup 2: Admin Config 模块

admin.py v1.7.30-2.10.1 段（行 199-295）拆出。
- GET  /api/admin/config  — 读取 era.json 安全字段
- POST /api/admin/config  — 更新白名单字段

依赖：admin.ADMIN_CONFIG_WHITELIST + admin.* helpers
"""
from __future__ import annotations

from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.routers.admin import (
    _check_admin_token,
    _admin_get_token,
    _admin_get_account_id,
    _get_account_system,
    ADMIN_CONFIG_WHITELIST,
)


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
        from history_footnote.resource_cache import load_era_config
        config = load_era_config("wanli1587")
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
        for key, value in updates.items():
            parts = key.split(".")
            target = config
            for p in parts[:-1]:
                target = target.setdefault(p, {})
            target[parts[-1]] = value
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