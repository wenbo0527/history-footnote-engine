"""🆕 v1.7.30 账户 API 路由

POST /api/account/register    — 用邀请码创建账户
POST /api/account/login       — 验证账户（不需密码，简化）
GET  /api/account/saves       — 列出该账户的存档
POST /api/account/saves       — 创建新存档（绑定账户）
DELETE /api/account/saves/{save_id}  — 删除存档
GET  /api/account/info        — 查账户信息
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs

from history_footnote.account_system import AccountSystem
from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.session import _storage_root_for_account


# 全局 AccountSystem 单例
_account_systems: dict[str, AccountSystem] = {}
_account_systems_lock = __import__("threading").RLock()


def _get_account_system(storage_root: Path) -> AccountSystem:
    """获取/创建 AccountSystem 单例"""
    key = str(storage_root)
    with _account_systems_lock:
        if key not in _account_systems:
            _account_systems[key] = AccountSystem(storage_root)
        return _account_systems[key]


# ============= 路由实现 =============

def handle_POST_account_register(handler, body: dict) -> bool:
    """POST /api/account/register
    Body: {username, invite_code, password, email?, migrate_from_guest_id?}

    🆕 v1.7.30: 接 password（scrypt 哈希）
    - username 必填
    - invite_code 必填（限流 + 防滥用）
    - password 必填（>= 6 字符）
    🆕 v2.7+ 游客迁移：
    - 传 migrate_from_guest_id → 把该 guest_id 拥有的存档迁到新账户
    """
    username = (body.get("username") or "").strip()
    invite_code = (body.get("invite_code") or "").strip()
    password = body.get("password") or ""
    email = (body.get("email") or "").strip()
    role = body.get("role") or "user"
    # 🆕 v2.7+: migrate_from 优先从 cookie 拿（前端不用带），body 兜底
    migrate_from = (body.get("migrate_from_guest_id") or "").strip()
    if not migrate_from:
        try:
            cookie_id = handler._get_guest_id_from_cookie_or_query()
            if cookie_id and cookie_id.startswith("guest_"):
                migrate_from = cookie_id
        except Exception:
            pass

    if not username or not invite_code:
        handler._json(400, {"error": "username 和 invite_code 必填"})
        return True
    if not password or len(password) < 6:
        handler._json(400, {"error": "password 至少 6 字符"})
        return True

    try:
        storage_root = _storage_root_for_account()
        sys_inst = _get_account_system(storage_root)
        account, err = sys_inst.create_account(
            username=username,
            invite_code=invite_code,
            email=email,
            role=role,
        )
        if account is None:
            handler._json(400, {"error": err or "创建账户失败"})
            return True
        # 🆕 v1.7.30: 设置密码
        sys_inst.set_password(account.account_id, password)
        # 重新读（拿到 password_hash / password_set_at）
        account = sys_inst.get_account(account.account_id)
        sys_inst.update_last_login(account.account_id)

        # 🆕 v2.7+ 游客存档迁移
        migrated = 0
        if migrate_from and migrate_from != account.account_id:
            try:
                from history_footnote.resource_cache import get_save_manager
                sm = get_save_manager()
                migrated = sm.migrate_account_id(migrate_from, account.account_id)
            except Exception as e:
                logger.warning(f"[/api/account/register] 游客存档迁移失败: {e}")

        handler._json(200, {
            "account_id": account.account_id,
            "username": account.username,
            "email": account.email,
            "role": account.role,
            "created_at": account.created_at,
            "last_login_at": account.last_login_at,
            "migrated_archives": migrated,  # 🆕 反馈给前端
        })
    except Exception as e:
        logger.exception(f"[/api/account/register] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_account_login(handler, body: dict) -> bool:
    """POST /api/account/login
    Body: {username, password}

    🆕 v1.7.30: 接入 scrypt 密码验证
    - 老账户（无 password_hash）→ 拒绝（强制首次登录注册）
    - 失败 5 次 → 锁定 5 分钟
    """
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        handler._json(400, {"error": "username 和 password 必填"})
        return True

    try:
        storage_root = _storage_root_for_account()
        sys_inst = _get_account_system(storage_root)
        account = sys_inst.get_account_by_username(username)
        if account is None:
            handler._json(404, {"error": "账户不存在或密码错误"})
            return True

        # 🆕 v1.7.30: 先检查锁定
        is_locked, retry_after = sys_inst.is_locked(account.account_id)
        if is_locked:
            handler._json(429, {
                "error": f"账户已锁定，请在 {retry_after} 秒后重试",
                "retry_after": retry_after,
            })
            return True

        # 验证密码
        if not sys_inst.verify_password(account.account_id, password):
            # 累加失败次数（>= 5 自动锁定 15 min）
            fail_count, now_locked = sys_inst.increment_fail_count(account.account_id)
            if now_locked:
                handler._json(429, {
                    "error": "密码错误 5 次，账户已锁定 15 分钟",
                    "locked": True,
                })
            else:
                handler._json(401, {
                    "error": f"密码错误（还有 {5 - fail_count} 次机会）",
                    "fail_count": fail_count,
                })
            return True

        # 登录成功：清空 fail_count
        sys_inst.reset_fail_count(account.account_id)
        sys_inst.update_last_login(account.account_id)
        handler._json(200, {
            "account_id": account.account_id,
            "username": account.username,
            "email": account.email,
            "role": account.role,
            "last_login_at": account.last_login_at,
            "created_at": account.created_at,
        })
    except Exception as e:
        logger.exception(f"[/api/account/login] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_account_saves(handler, query: str) -> bool:
    """GET /api/account/saves?account_id=xxx
    Returns: {saves: [{save_id, account_id, bound_at, ...}]}
    """
    qs = parse_qs(query)
    account_id = qs.get("account_id", [None])[0]
    if not account_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    try:
        storage_root = _storage_root_for_account()
        sys_inst = _get_account_system(storage_root)
        saves = sys_inst.list_saves(account_id)
        handler._json(200, {"saves": saves, "account_id": account_id})
    except Exception as e:
        logger.exception(f"[/api/account/saves] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_account_create_save(handler, body: dict) -> bool:
    """POST /api/account/saves
    Body: {account_id, save_id?}
    Returns: {save_id, account_id, save_path}
    """
    account_id = (body.get("account_id") or "").strip()
    save_id = (body.get("save_id") or "").strip()
    if not account_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    try:
        storage_root = _storage_root_for_account()
        sys_inst = _get_account_system(storage_root)
        account = sys_inst.get_account(account_id)
        if account is None:
            handler._json(404, {"error": "账户不存在"})
            return True
        # 生成 save_id
        from history_footnote.account_system import _generate_save_id
        if not save_id:
            save_id = f"save_{_generate_save_id()[:8]}"
        success = sys_inst.bind_save(account_id, save_id)
        if not success:
            handler._json(500, {"error": "绑定存档失败"})
            return True
        save_path = sys_inst.get_save_path(account_id, save_id)
        handler._json(200, {
            "save_id": save_id,
            "account_id": account_id,
            "username": account.username,
            "save_path": str(save_path),
            "bound_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        })
    except Exception as e:
        logger.exception(f"[/api/account/saves] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_account_info(handler, query: str) -> bool:
    """GET /api/account/info?account_id=xxx
    Returns: 账户详细信息
    """
    qs = parse_qs(query)
    account_id = qs.get("account_id", [None])[0]
    if not account_id:
        handler._json(400, {"error": "account_id 必填"})
        return True
    try:
        storage_root = _storage_root_for_account()
        sys_inst = _get_account_system(storage_root)
        account = sys_inst.get_account(account_id)
        if account is None:
            handler._json(404, {"error": "账户不存在"})
            return True
        handler._json(200, account.to_dict())
    except Exception as e:
        logger.exception(f"[/api/account/info] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_account_invite_codes(handler, query: str) -> bool:
    """GET /api/account/invite_codes
    Returns: 所有邀请码（管理员视图）
    """
    try:
        storage_root = _storage_root_for_account()
        sys_inst = _get_account_system(storage_root)
        codes = sys_inst.list_invite_codes()
        handler._json(200, {
            "codes": [
                {**c.to_dict(), "is_valid": c.is_valid()[0]}
                for c in codes
            ]
        })
    except Exception as e:
        logger.exception(f"[/api/account/invite_codes] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True
