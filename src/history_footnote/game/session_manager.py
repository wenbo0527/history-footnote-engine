"""🆕 v1.8.0 Session Manager

设计：
- sessions.json 持久化（CRUD）
- 32 hex (128-bit) session_id
- HMAC 签 cookie 防伪造
- Sliding 续期（每次操作刷新 expires_at）
- 24h 过期
- 启动时 + 后台线程清理过期 session

用法：
    sm = SessionManager(storage_root=Path('saves'))
    session = sm.create(account_id, ip, user_agent)
    cookie = sm.sign_cookie(session.session_id)  # "session_id=xxx.signature"
    sm.lookup(cookie)  # 验签 + 续期
    sm.delete(cookie)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import os


SESSION_TTL_SECONDS = 24 * 3600  # 24h
SESSION_ID_BYTES = 16  # 128 bit


@dataclass
class Session:
    session_id: str  # 32 hex
    account_id: str
    created_at: str
    last_active_at: str
    expires_at: str
    ip: str
    user_agent: str


def _now_ts() -> int:
    return int(time.time())


def _now_iso(plus_seconds: int = 0) -> str:
    """ISO 格式时间戳"""
    from datetime import datetime, timezone, timedelta
    dt = datetime.now(timezone.utc) + timedelta(seconds=plus_seconds)
    return dt.isoformat()


def _get_hmac_secret() -> str:
    """从环境变量拿 HMAC secret"""
    return os.environ.get("SESSION_HMAC_SECRET", "hfe-default-hmac-secret-change-me")


def _sign_session_id(session_id: str) -> str:
    """HMAC-SHA256 签 session_id"""
    secret = _get_hmac_secret().encode("utf-8")
    return hmac.new(secret, session_id.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def _verify_signature(session_id: str, signature: str) -> bool:
    """验签"""
    expected = _sign_session_id(session_id)
    return hmac.compare_digest(expected, signature)


def _parse_iso(iso_str: str) -> int:
    from datetime import datetime
    if not iso_str:
        return 0
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return 0


class SessionManager:
    """Session CRUD + 过期清理 + HMAC 签 cookie"""

    def __init__(self, storage_root: Path):
        self.storage_root = Path(storage_root)
        self.sessions_file = self.storage_root / "sessions.json"
        self._lock = threading.RLock()
        self.storage_root.mkdir(parents=True, exist_ok=True)
        if not self.sessions_file.exists():
            self._save({"sessions": []})
        # 启动时清理过期
        self._cleanup_expired()

    # ----- CRUD -----

    def _load(self) -> list[dict]:
        with self._lock:
            try:
                data = json.loads(self.sessions_file.read_text(encoding="utf-8"))
                return data.get("sessions", [])
            except (json.JSONDecodeError, OSError):
                return []

    def _save(self, data: dict) -> None:
        with self._lock:
            tmp = self.sessions_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.sessions_file)

    def create(self, account_id: str, ip: str = "", user_agent: str = "") -> Session:
        """创建新 session"""
        sid = secrets.token_hex(SESSION_ID_BYTES)  # 32 hex
        now = _now_iso()
        expires = _now_iso(plus_seconds=SESSION_TTL_SECONDS)
        s = Session(
            session_id=sid,
            account_id=account_id,
            created_at=now,
            last_active_at=now,
            expires_at=expires,
            ip=ip,
            user_agent=user_agent,
        )
        with self._lock:
            sessions = self._load()
            sessions.append(asdict(s))
            self._save({"sessions": sessions})
        return s

    def lookup(self, cookie_value: str, sliding: bool = True) -> Optional[Session]:
        """查找 session（验签 + 续期）

        cookie_value 格式: "<session_id>.<signature>"
        Returns:
            Session（已续期）或 None
        """
        if not cookie_value or "." not in cookie_value:
            return None
        sid, sig = cookie_value.rsplit(".", 1)
        if not _verify_signature(sid, sig):
            return None
        with self._lock:
            sessions = self._load()
            now_ts = _now_ts()
            for s in sessions:
                if s["session_id"] == sid:
                    # 过期检查
                    expires_ts = _parse_iso(s["expires_at"])
                    if expires_ts <= now_ts:
                        # 过期：删
                        sessions.remove(s)
                        self._save({"sessions": sessions})
                        return None
                    if sliding:
                        # 续期
                        s["last_active_at"] = _now_iso()
                        s["expires_at"] = _now_iso(plus_seconds=SESSION_TTL_SECONDS)
                        self._save({"sessions": sessions})
                    return Session(**s)
            return None

    def delete(self, session_id: str) -> bool:
        """删 session"""
        with self._lock:
            sessions = self._load()
            for s in sessions:
                if s["session_id"] == session_id:
                    sessions.remove(s)
                    self._save({"sessions": sessions})
                    return True
            return False

    def delete_by_account(self, account_id: str) -> int:
        """删某 account 的所有 session（kill_sessions）"""
        with self._lock:
            sessions = self._load()
            before = len(sessions)
            sessions = [s for s in sessions if s["account_id"] != account_id]
            killed = before - len(sessions)
            self._save({"sessions": sessions})
            return killed

    def list_sessions(self) -> list[Session]:
        """列出所有 session"""
        with self._lock:
            return [Session(**s) for s in self._load()]

    # ----- Cookie -----

    @staticmethod
    def sign_cookie(session_id: str) -> str:
        """签 cookie 值: <session_id>.<signature>"""
        return f"{session_id}.{_sign_session_id(session_id)}"

    @staticmethod
    def parse_cookie(cookie_header: str, cookie_name: str = "session_id") -> Optional[str]:
        """从 Cookie 头解析 session cookie"""
        if not cookie_header:
            return None
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{cookie_name}="):
                return part[len(cookie_name) + 1:]
        return None

    # ----- 清理 -----

    def _cleanup_expired(self) -> int:
        """清过期 session"""
        with self._lock:
            sessions = self._load()
            now_ts = _now_ts()
            before = len(sessions)
            sessions = [s for s in sessions if _parse_iso(s["expires_at"]) > now_ts]
            cleaned = before - len(sessions)
            self._save({"sessions": sessions})
            return cleaned

    def cleanup_expired(self) -> int:
        """公开清理方法"""
        return self._cleanup_expired()


# ----- 后台清理线程 -----

_CLEANUP_INTERVAL = 3600  # 1h


def start_session_cleanup_thread(sm: SessionManager) -> threading.Thread:
    """启动后台定期清理线程"""
    def _loop():
        while True:
            try:
                time.sleep(_CLEANUP_INTERVAL)
                sm.cleanup_expired()
            except Exception:
                pass
    t = threading.Thread(target=_loop, daemon=True, name="session-cleanup")
    t.start()
    return t
