"""🆕 v2.10.x W62: 公开 API 网关

- rate_limit 限流（per user/IP）
- api_key 认证
- openapi_spec() 返 OpenAPI 3.0 spec
"""
from __future__ import annotations
import time
import hashlib
import threading
from typing import Literal

_rate_lock = threading.Lock()
_rate_storage: dict[str, list[float]] = {}

_api_keys: dict[str, dict] = {
    "demo_key": {"name": "demo", "tier": "free", "rate_limit": 60},
    "pro_key": {"name": "pro", "tier": "pro", "rate_limit": 600},
}


def rate_limit_check(key: str, limit: int = 60, window_seconds: float = 60) -> dict:
    """检查限流

    Returns:
        {
            "allowed": bool,
            "remaining": int,
            "reset_at": float,
        }
    """
    now = time.time()
    with _rate_lock:
        if key not in _rate_storage:
            _rate_storage[key] = []
        # 清理窗口外的记录
        _rate_storage[key] = [t for t in _rate_storage[key] if now - t < window_seconds]
        count = len(_rate_storage[key])
        if count >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": now + window_seconds,
            }
        _rate_storage[key].append(now)
        return {
            "allowed": True,
            "remaining": limit - count - 1,
            "reset_at": now + window_seconds,
        }


def rate_limit_reset(key: str) -> None:
    with _rate_lock:
        if key in _rate_storage:
            del _rate_storage[key]


def api_key_validate(key: str) -> dict | None:
    """验证 API key，返元信息"""
    return _api_keys.get(key)


def api_key_register(name: str, tier: Literal["free", "pro", "enterprise"] = "free") -> str:
    """注册新 API key"""
    new_key = hashlib.sha256(f"{name}_{time.time()}".encode()).hexdigest()[:32]
    _api_keys[new_key] = {"name": name, "tier": tier, "rate_limit": 60 if tier == "free" else 600}
    return new_key


def openapi_spec() -> dict:
    """OpenAPI 3.0 spec"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "History Footnote Engine API",
            "version": "2.10.0",
            "description": "章节制叙事游戏 API",
        },
        "servers": [{"url": "http://localhost:8000", "description": "本地开发"}],
        "paths": {
            "/api/input": {
                "post": {
                    "summary": "提交玩家输入",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "session_id": {"type": "string"},
                                        "input": {"type": "string"},
                                        "voice_id": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "responses": {
                        "200": {"description": "OK"},
                        "400": {"description": "Bad request"},
                    },
                },
            },
            "/api/archives": {
                "get": {
                    "summary": "存档列表",
                    "parameters": [
                        {"name": "account", "in": "query", "schema": {"type": "string"}},
                        {"name": "include_archived", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/metrics": {
                "get": {
                    "summary": "性能指标",
                    "responses": {"200": {"description": "OK"}},
                },
            },
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                },
            },
        },
    }
