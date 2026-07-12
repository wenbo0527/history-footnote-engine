"""🆕 v2.10.1 W52 P1-3: Admin Settings 拆分模块

原 admin.py v1.8.6 段（行 807-978）拆出。
- GET  /api/admin/settings         — 读 .env 关键设置
- POST /api/admin/settings         — 白名单热更新（重启生效）
- POST /api/admin/settings/reset   — 恢复默认

Auth 依赖 admin._shared 中的 helper：
- _check_admin_token
- _admin_get_token
- _get_client_ip
- audit_log
"""
from __future__ import annotations

import os
from pathlib import Path

from history_footnote.audit import audit_log
from history_footnote.web_server.routers.admin import (
    _check_admin_token,
    _admin_get_token,
    _get_client_ip,
)


ENV_PATH = Path(os.environ.get("ENV_PATH", ".env"))


def _read_env_settings() -> dict:
    """从 .env 读当前设置（不依赖环境变量）"""
    settings = {
        "LLM_MAX_REQUESTS": 20,
        "LLM_WINDOW_SECONDS": 60.0,
        "GLOBAL_MAX_REQUESTS": 60,
        "GLOBAL_WINDOW_SECONDS": 60.0,
        "LLM_PRIMARY_PROVIDER": "minimax-anthropic",
        "ADMIN_TOKEN": "",
    }
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if k in settings:
                try:
                    if "SECONDS" in k:
                        settings[k] = float(v)
                    else:
                        settings[k] = int(v) if v.isdigit() else v
                except Exception:
                    pass
    except Exception:
        pass
    return settings


def _write_env_settings(updates: dict) -> tuple[bool, str]:
    """写 .env（保留其他行）"""
    try:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        new_lines = []
        keys_to_set = set(updates.keys())
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                new_lines.append(line)
                continue
            k = stripped.split("=", 1)[0].strip()
            if k in keys_to_set:
                new_lines.append(f"{k}={updates[k]}")
                keys_to_set.discard(k)
            else:
                new_lines.append(line)
        for k in keys_to_set:
            new_lines.append(f"{k}={updates[k]}")
        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True, "ok"
    except Exception as e:
        return False, str(e)


def handle_GET_admin_settings(handler, query: str) -> bool:
    """GET /api/admin/settings — 返回当前 .env 关键设置（admin only）"""
    if not _check_admin_token(handler, {"token": _admin_get_token(handler, query)}):
        handler._json(401, {"error": "需要有效 session 或 ADMIN_TOKEN"})
        return True
    settings = _read_env_settings()
    if "ADMIN_TOKEN" in settings:
        token = settings["ADMIN_TOKEN"]
        settings["ADMIN_TOKEN"] = f"***{token[-4:]}" if len(token) >= 4 else "***"
    handler._json(200, {
        "settings": settings,
        "restart_required": True,
        "env_path": str(ENV_PATH),
    })
    return True


def handle_POST_admin_settings(handler, body: dict) -> bool:
    """POST /api/admin/settings — 白名单热更新（重启生效）"""
    if not _check_admin_token(handler, body or {}):
        handler._json(401, {"error": "需要有效 session 或 ADMIN_TOKEN"})
        return True
    if not isinstance(body, dict):
        handler._json(400, {"error": "body must be dict"})
        return True
    ALLOWED = {
        "LLM_MAX_REQUESTS": int,
        "LLM_WINDOW_SECONDS": float,
        "GLOBAL_MAX_REQUESTS": int,
        "GLOBAL_WINDOW_SECONDS": float,
        "LLM_PRIMARY_PROVIDER": str,
    }
    updates = {}
    for k, v in body.items():
        if k not in ALLOWED:
            continue
        try:
            updates[k] = ALLOWED[k](v)
        except (ValueError, TypeError):
            type_name = "int" if ALLOWED[k] is int else ("float" if ALLOWED[k] is float else "string")
            handler._json(400, {"error": f"{k} 必须为 {type_name}"})
            return True
        if ALLOWED[k] is int and updates[k] < 1:
            handler._json(400, {"error": f"{k} 必须 ≥ 1"})
            return True
        if ALLOWED[k] is float and updates[k] < 1.0:
            handler._json(400, {"error": f"{k} 必须 ≥ 1.0"})
            return True
        if ALLOWED[k] is str and k == "LLM_PRIMARY_PROVIDER":
            if updates[k] not in ("minimax-anthropic", "deepseek", "minimax-openai"):
                handler._json(400, {"error": "LLM_PRIMARY_PROVIDER 必须为 minimax-anthropic/deepseek/minimax-openai"})
                return True
    if not updates:
        handler._json(400, {"error": "未提供有效字段", "allowed": list(ALLOWED.keys())})
        return True
    ok, msg = _write_env_settings(updates)
    if not ok:
        handler._json(500, {"error": f"写 .env 失败：{msg}"})
        return True
    audit_log(event="settings_update", updates=updates, route="/api/admin/settings", method="POST", status=200,
              ip=_get_client_ip(handler))
    handler._json(200, {
        "ok": True,
        "updated": updates,
        "restart_required": True,
        "message": "已写入 .env，请重启服务生效",
    })
    return True


def handle_POST_admin_settings_reset(handler, body: dict) -> bool:
    """POST /api/admin/settings/reset — 恢复默认（LLM 20/60s, GLOBAL 60/60s）"""
    if not _check_admin_token(handler, body or {}):
        handler._json(401, {"error": "需要有效 session 或 ADMIN_TOKEN"})
        return True
    defaults = {
        "LLM_MAX_REQUESTS": 20,
        "LLM_WINDOW_SECONDS": 60.0,
        "GLOBAL_MAX_REQUESTS": 60,
        "GLOBAL_WINDOW_SECONDS": 60.0,
        "LLM_PRIMARY_PROVIDER": "minimax-anthropic",
    }
    ok, msg = _write_env_settings(defaults)
    if not ok:
        handler._json(500, {"error": f"写 .env 失败：{msg}"})
        return True
    audit_log(event="settings_reset", defaults=defaults, route="/api/admin/settings/reset", method="POST", status=200,
              ip=_get_client_ip(handler))
    handler._json(200, {
        "ok": True,
        "defaults": defaults,
        "restart_required": True,
        "message": "已恢复默认，请重启服务生效",
    })
    return True