"""🆕 v1.8.8 运行时配置（热加载 .env）

设计目标：
- .env 改了，代码不重启即可生效
- 全局 get_setting() 函数访问当前值
- 用 mtime 检测文件变化，自动 reload
"""
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any, Optional

ENV_PATH = Path(os.environ.get("ENV_PATH", ".env"))
_LOCK = Lock()
_CACHE = {}
_LAST_MTIME = 0
_LAST_RELOAD = 0
_RELOAD_TTL = 5.0  # 5s 内不重复读盘


def _parse_env() -> dict:
    """从 .env 读全部键值"""
    out = {}
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def _maybe_reload(force: bool = False) -> dict:
    """🆕 v1.8.8 热加载：mtime 变了才 reload，且 5s 内最多 1 次"""
    global _CACHE, _LAST_MTIME, _LAST_RELOAD
    with _LOCK:
        now = time.time()
        if not force and (now - _LAST_RELOAD) < _RELOAD_TTL:
            return _CACHE
        try:
            mtime = ENV_PATH.stat().st_mtime
        except Exception:
            return _CACHE
        if force or mtime > _LAST_MTIME:
            _CACHE = _parse_env()
            _LAST_MTIME = mtime
            _LAST_RELOAD = now
        return _CACHE


def get_setting(key: str, default: Any = None) -> Any:
    """🆕 v1.8.8 读 .env 设置（热加载）

    优先 .env 当前值 → 然后环境变量 → 最后 default
    """
    cache = _maybe_reload()
    if key in cache:
        return cache[key]
    env_v = os.environ.get(key)
    if env_v is not None:
        return env_v
    return default


def set_setting(key: str, value: Any) -> None:
    """🆕 v1.8.8 写 .env（force reload）"""
    global _CACHE
    with _LOCK:
        try:
            _maybe_reload(force=True)
            # 改 _CACHE（不写盘，写盘由 admin 端点处理）
            _CACHE[key] = str(value)
        except Exception:
            pass


def get_all_settings() -> dict:
    """返回所有 .env 设置（不热加载）"""
    return _parse_env()
