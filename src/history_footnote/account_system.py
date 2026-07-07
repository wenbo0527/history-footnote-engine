"""🆕 v1.7.30 账户体系 + 邀请码系统

数据结构（JSON 存储）：
- accounts/accounts.json: 账户列表
- accounts/invite_codes.json: 邀请码列表
- accounts/saves/{account_id}/{save_id}.json: 存档

Account:
- account_id: uuid
- username: str
- email: str (optional)
- invite_code_used: str
- created_at: str
- role: admin / user / guest
- bound_at: str

InviteCode:
- code: str (格式: INV-XXXX-XXXX)
- account_id: str or None (使用了)
- max_uses: int (默认 1，可多)
- used_count: int
- created_at: str
- expires_at: str (optional)
- label: str (描述用途)
"""
from __future__ import annotations

import json
import re
import secrets
import string
import threading
import hashlib
import base64
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


ACCOUNTS_DIR_NAME = "accounts"
SAVES_DIR_NAME = "saves"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _generate_invite_code() -> str:
    """生成 INV-XXXX-XXXX 格式的邀请码"""
    alphabet = string.ascii_uppercase + string.digits
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"INV-{part1}-{part2}"


def _generate_account_id() -> str:
    """生成账户 ID (8 字符)"""
    return secrets.token_hex(4)


def _generate_save_id() -> str:
    """生成存档 ID (12 字符)"""
    return secrets.token_hex(6)


def _atomic_write(path: Path, data: dict) -> None:
    """原子写 JSON 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


# ============= 账户 =============

@dataclass
class Account:
    account_id: str
    username: str
    email: str = ""
    invite_code_used: str = ""
    created_at: str = field(default_factory=_now)
    role: str = "user"  # admin / user / guest
    bound_at: str = field(default_factory=_now)
    last_login_at: str = ""
    # 🆕 v1.8.0 scrypt password + 失败锁定
    password_hash: str = ""
    password_set_at: str = ""
    fail_count: int = 0
    lock_until: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


# ============= 邀请码 =============

@dataclass
class InviteCode:
    code: str
    account_id: str = ""  # 使用者（空 = 有效）
    max_uses: int = 1
    used_count: int = 0
    created_at: str = field(default_factory=_now)
    expires_at: str = ""
    label: str = ""  # 用途描述

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "InviteCode":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def is_valid(self) -> tuple[bool, str]:
        """验证邀请码是否可用
        Returns: (valid, reason)
        """
        if self.used_count >= self.max_uses:
            return False, f"邀请码已用完（{self.used_count}/{self.max_uses}）"
        if self.expires_at:
            try:
                exp = datetime.fromisoformat(self.expires_at)
                if datetime.now() > exp:
                    return False, f"邀请码已过期（{self.expires_at}）"
            except ValueError:
                pass
        return True, "有效"


# ============= 账户系统 =============

class AccountSystem:
    """账户系统（线程安全）

    存储位置：
    - {storage_root}/accounts/accounts.json
    - {storage_root}/accounts/invite_codes.json
    - {storage_root}/accounts/saves/{account_id}/{save_id}.json
    """

# ----- 🆕 v1.8.0 scrypt helpers -----

def _hash_password(password: str) -> str:
    """scrypt 哈希

    格式: scrypt:16384:8:1$<salt-b64>$<hash-b64>
    🆕 v1.8.0 调整：n=16384（macOS OpenSSL 默认 maxscrypt=32MB 限制）
    n=32768 需要 32MB，16384 仅需 16MB，安全性仍足够
    """
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt:16384:8:1${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"


def _verify_hash(stored: str, password: str) -> bool:
    """验证 scrypt 哈希

    处理 3 种情况：
    1. 老数据无 password_hash（空字符串）→ False
    2. 哈希不匹配 → False
    3. 哈希匹配 → True
    """
    if not stored or not stored.startswith("scrypt:"):
        return False
    try:
        parts = stored.split("$")
        if len(parts) != 3:
            return False
        header, salt_b64, hash_b64 = parts
        n_str, r_str, p_str = header.split(":")[1:]
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_str), r=int(r_str), p=int(p_str),
            dklen=len(expected),
        )
        return secrets.compare_digest(actual, expected)
    except Exception:
        return False


def _now_iso(plus_seconds: int = 0) -> str:
    """当前时间（ISO 格式），可加秒数"""
    dt = datetime.now(timezone.utc) + timedelta(seconds=plus_seconds)
    return dt.isoformat()


def _now_ts() -> int:
    """当前时间戳（秒）"""
    return int(datetime.now(timezone.utc).timestamp())


def _parse_iso(iso_str: str) -> int:
    """解析 ISO 字符串为时间戳（秒）"""
    if not iso_str:
        return 0
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return 0


class AccountSystem:
    def __init__(self, storage_root: Path):
        self.storage_root = Path(storage_root)
        self.accounts_dir = self.storage_root / ACCOUNTS_DIR_NAME
        self.saves_dir = self.accounts_dir / SAVES_DIR_NAME
        self.accounts_file = self.accounts_dir / "accounts.json"
        self.invite_codes_file = self.accounts_dir / "invite_codes.json"
        # 线程锁
        self._lock = threading.RLock()
        # 初始化
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        self.saves_dir.mkdir(parents=True, exist_ok=True)
        if not self.accounts_file.exists():
            _atomic_write(self.accounts_file, {"accounts": []})
        if not self.invite_codes_file.exists():
            _atomic_write(self.invite_codes_file, {"codes": []})

    # ----- 邀请码管理 -----

    def _load_invite_codes(self) -> list[InviteCode]:
        data = json.loads(self.invite_codes_file.read_text(encoding="utf-8"))
        return [InviteCode.from_dict(c) for c in data.get("codes", [])]

    def _save_invite_codes(self, codes: list[InviteCode]) -> None:
        _atomic_write(
            self.invite_codes_file,
            {"codes": [c.to_dict() for c in codes]},
        )

    def create_invite_code(
        self, label: str = "", max_uses: int = 1, expires_at: str = ""
    ) -> InviteCode:
        """创建邀请码"""
        with self._lock:
            code = _generate_invite_code()
            inv = InviteCode(
                code=code,
                max_uses=max_uses,
                label=label,
                expires_at=expires_at,
            )
            codes = self._load_invite_codes()
            codes.append(inv)
            self._save_invite_codes(codes)
            return inv

    def verify_invite_code(self, code: str) -> tuple[bool, str, Optional[InviteCode]]:
        """验证邀请码
        Returns: (valid, reason, invite_code_obj)
        """
        with self._lock:
            codes = self._load_invite_codes()
            for inv in codes:
                if inv.code == code:
                    valid, reason = inv.is_valid()
                    return valid, reason, inv if valid else None
            return False, "邀请码不存在", None

    def use_invite_code(self, code: str, account_id: str) -> bool:
        """使用邀请码（绑定账户）"""
        with self._lock:
            codes = self._load_invite_codes()
            for inv in codes:
                if inv.code == code:
                    valid, _ = inv.is_valid()
                    if not valid:
                        return False
                    inv.used_count += 1
                    if inv.account_id:
                        inv.account_id = inv.account_id + "," + account_id
                    else:
                        inv.account_id = account_id
                    self._save_invite_codes(codes)
                    return True
            return False

    def list_invite_codes(self) -> list[InviteCode]:
        with self._lock:
            return self._load_invite_codes()

    # ----- 账户管理 -----

    def _load_accounts(self) -> list[Account]:
        data = json.loads(self.accounts_file.read_text(encoding="utf-8"))
        return [Account.from_dict(a) for a in data.get("accounts", [])]

    def _save_accounts(self, accounts: list[Account]) -> None:
        _atomic_write(
            self.accounts_file,
            {"accounts": [a.to_dict() for a in accounts]},
        )

    def create_account(
        self, username: str, invite_code: str, email: str = "", role: str = "user"
    ) -> tuple[Optional[Account], str]:
        """创建账户
        Returns: (account, error_msg)
        """
        with self._lock:
            # 验证邀请码
            valid, reason, inv = self.verify_invite_code(invite_code)
            if not valid:
                return None, reason
            # 检查用户名重复
            accounts = self._load_accounts()
            if any(a.username == username for a in accounts):
                return None, f"用户名已存在：{username}"
            # 验证用户名格式
            if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]{2,20}$", username):
                return None, "用户名需 2-20 字符（中文/字母/数字/下划线）"
            # 创建账户
            account = Account(
                account_id=_generate_account_id(),
                username=username,
                email=email,
                invite_code_used=invite_code,
                role=role,
            )
            accounts.append(account)
            self._save_accounts(accounts)
            # 标记邀请码已用
            self.use_invite_code(invite_code, account.account_id)
            return account, ""

    def get_account(self, account_id: str) -> Optional[Account]:
        with self._lock:
            for a in self._load_accounts():
                if a.account_id == account_id:
                    return a
            return None

    def get_account_by_username(self, username: str) -> Optional[Account]:
        with self._lock:
            for a in self._load_accounts():
                if a.username == username:
                    return a
            return None

    def list_accounts(self) -> list[Account]:
        with self._lock:
            return self._load_accounts()

    # ----- 🆕 v1.8.0 scrypt password -----

    def set_password(self, account_id: str, password: str) -> bool:
        """设置/重置密码（scrypt 哈希）

        Returns:
            True 成功
        """
        with self._lock:
            accounts = self._load_accounts()
            for a in accounts:
                if a.account_id == account_id:
                    a.password_hash = _hash_password(password)
                    a.password_set_at = _now_iso()
                    a.fail_count = 0
                    a.lock_until = ""
                    self._save_accounts(accounts)
                    return True
            return False

    def verify_password(self, account_id: str, password: str) -> bool:
        """验证密码"""
        with self._lock:
            accounts = self._load_accounts()
            for a in accounts:
                if a.account_id == account_id:
                    return _verify_hash(a.password_hash or "", password)
            return False

    def is_locked(self, account_id: str) -> tuple[bool, int]:
        """检查账户是否锁定

        Returns:
            (is_locked, retry_after_seconds)
        """
        with self._lock:
            accounts = self._load_accounts()
            for a in accounts:
                if a.account_id == account_id:
                    if not a.lock_until:
                        return False, 0
                    try:
                        lock_ts = _parse_iso(a.lock_until)
                    except Exception:
                        return False, 0
                    now = _now_ts()
                    if lock_ts > now:
                        return True, int(lock_ts - now)
                    # 已过期：解锁
                    a.lock_until = ""
                    a.fail_count = 0
                    self._save_accounts(accounts)
                    return False, 0
            return False, 0

    def increment_fail_count(self, account_id: str) -> tuple[int, bool]:
        """增加失败计数；达 5 次则锁定 15 min

        Returns:
            (current_fail_count, is_now_locked)
        """
        with self._lock:
            accounts = self._load_accounts()
            for a in accounts:
                if a.account_id == account_id:
                    a.fail_count = (a.fail_count or 0) + 1
                    is_locked = False
                    if a.fail_count >= 5:
                        a.lock_until = _now_iso(plus_seconds=15 * 60)
                        is_locked = True
                    self._save_accounts(accounts)
                    return a.fail_count, is_locked
            return 0, False

    def reset_fail_count(self, account_id: str) -> None:
        """登录成功重置失败计数"""
        with self._lock:
            accounts = self._load_accounts()
            for a in accounts:
                if a.account_id == account_id:
                    a.fail_count = 0
                    a.lock_until = ""
                    self._save_accounts(accounts)
                    return

    def update_last_login(self, account_id: str) -> None:
        with self._lock:
            accounts = self._load_accounts()
            for a in accounts:
                if a.account_id == account_id:
                    a.last_login_at = _now()
                    self._save_accounts(accounts)
                    return

    # ----- 存档绑定 -----

    def bind_save(self, account_id: str, save_id: str) -> bool:
        """把存档绑定到账户（按 account_id 目录）"""
        account = self.get_account(account_id)
        if account is None:
            return False
        # 保存目录: {storage_root}/accounts/saves/{account_id}/{save_id}.json
        save_path = self._save_path(account_id, save_id)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        # 绑定元数据
        meta = {
            "account_id": account_id,
            "username": account.username,
            "save_id": save_id,
            "bound_at": _now(),
        }
        meta_path = save_path.parent / f"{save_id}.meta.json"
        _atomic_write(meta_path, meta)
        return True

    def unbind_save(self, account_id: str, save_id: str) -> bool:
        """解绑存档（不删除文件，只删 meta）"""
        meta_path = self._save_path(account_id, save_id).parent / f"{save_id}.meta.json"
        if meta_path.exists():
            meta_path.unlink()
            return True
        return False

    def list_saves(self, account_id: str) -> list[dict]:
        """列出账户的所有存档
        Returns: [{save_id, account_id, username, bound_at, save_path}, ...]
        """
        with self._lock:
            account = self.get_account(account_id)
            if account is None:
                return []
            account_dir = self.saves_dir / account_id
            if not account_dir.exists():
                return []
            results = []
            for meta_path in account_dir.glob("*.meta.json"):
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    results.append(meta)
                except (json.JSONDecodeError, OSError):
                    continue
            # 按 bound_at 倒序
            results.sort(key=lambda x: x.get("bound_at", ""), reverse=True)
            return results

    def get_save_path(self, account_id: str, save_id: str) -> Path:
        """获取存档实际路径（由调用方负责写入）"""
        return self._save_path(account_id, save_id)

    def _save_path(self, account_id: str, save_id: str) -> Path:
        return self.saves_dir / account_id / f"{save_id}.json"

    # ----- 管理员 -----

    # 🆕 v1.7.30 体验版（无需邀请码，30 回合限制 + 10 回合反馈）

    TRIAL_MAX_ROUNDS = 30
    TRIAL_FEEDBACK_INTERVAL = 10
    TRIAL_FILE = "trial.json"

    def _get_trial_path(self) -> Path:
        return self.accounts_dir / self.TRIAL_FILE

    def _load_trial(self) -> dict:
        path = self._get_trial_path()
        if not path.exists():
            return {"current": None, "history": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"current": None, "history": []}

    def _save_trial(self, trial: dict) -> None:
        _atomic_write(self._get_trial_path(), trial)

    def start_trial(self) -> dict:
        """开始一次体验版（不需要邀请码）

        Returns: {trial_id, current_round, started_at, feedback_required_at}
        """
        with self._lock:
            trial = self._load_trial()
            new_trial = {
                "trial_id": secrets.token_hex(8),
                "current_round": 0,
                "started_at": _now(),
                "feedback_required_at": self.TRIAL_FEEDBACK_INTERVAL,  # 第 10 回合要求反馈
                "feedback_submitted": False,
                "ended_at": None,
                "contact": "",
                "invite_code_received": False,
            }
            trial["current"] = new_trial
            self._save_trial(trial)
            return new_trial

    def get_current_trial(self) -> dict | None:
        with self._lock:
            trial = self._load_trial()
            return trial.get("current")

    def increment_trial_round(self) -> dict | None:
        """增加体验版轮数（玩家每轮结束调用）"""
        with self._lock:
            trial = self._load_trial()
            current = trial.get("current")
            if not current:
                return None
            current["current_round"] += 1
            # 检查是否需要反馈
            if current["current_round"] >= self.TRIAL_MAX_ROUNDS and not current.get("ended_at"):
                current["ended_at"] = _now()
            self._save_trial(trial)
            return current

    def is_trial_round_feedback_required(self) -> bool:
        """当前是否需要提交反馈（每 10 回合）"""
        with self._lock:
            current = self.get_current_trial()
            if not current:
                return False
            round_num = current.get("current_round", 0)
            # 每 10 轮（10/20/30）且未提交
            if round_num > 0 and round_num % self.TRIAL_FEEDBACK_INTERVAL == 0 and not current.get("feedback_submitted"):
                return True
            return False

    def submit_trial_feedback(self, feedback: str, contact: str = "") -> bool:
        """提交体验版反馈

        Args:
            feedback: 反馈/建议
            contact: 联系方式（可选）

        Returns: 是否成功
        """
        with self._lock:
            trial = self._load_trial()
            current = trial.get("current")
            if not current:
                return False
            current["feedback_submitted"] = True
            current["contact"] = contact
            # 记录历史
            history = trial.get("history", [])
            history.append({
                "trial_id": current.get("trial_id"),
                "round": current.get("current_round"),
                "feedback": feedback,
                "contact": contact,
                "submitted_at": _now(),
            })
            trial["history"] = history
            self._save_trial(trial)
            return True

    def end_trial(self) -> dict | None:
        """结束体验版（玩家主动结束 / 30 回合到）"""
        with self._lock:
            trial = self._load_trial()
            current = trial.get("current")
            if not current:
                return None
            if not current.get("ended_at"):
                current["ended_at"] = _now()
            # 移入 history
            history = trial.get("history", [])
            history.append(current)
            trial["history"] = history
            trial["current"] = None
            self._save_trial(trial)
            return current

    def grant_invite_code_for_trial(self, contact: str) -> InviteCode | None:
        """如果反馈意见被采纳，奖励一个邀请码（管理员操作）

        Args:
            contact: 联系方式（用于查找 trial history）

        Returns: 创建的邀请码
        """
        with self._lock:
            inv = self.create_invite_code(
                label=f"trial-reward-{secrets.token_hex(4)}",
                max_uses=1,
            )
            return inv

    def ensure_default_admin(self, admin_code: str | None = None) -> tuple[InviteCode | None, Account | None]:
        """确保至少有一个 admin 邀请码 + 至少一个 admin 账户（系统初始化用）

        Returns: (invite_code, account)
        - 若已有 admin 邀请码：返回 (None, None)
        - 若没有：创建 admin 邀请码 + 创建 admin 账户（用户名=admin）

        默认 admin 账户:
        - username: "admin"
        - account_id: "00000000"
        - 邀请码: "INV-ADMIN-2024"（首次启动生成）
        """
        with self._lock:
            codes = self._load_invite_codes()
            accounts = self._load_accounts()
            # 已有 admin 邀请码
            admin_codes = [c for c in codes if "admin" in c.label.lower()]
            if admin_codes:
                return None, None
            # 已有 admin 账户
            existing_admin = next((a for a in accounts if a.role == "admin"), None)
            if existing_admin:
                return None, None
            # 创建 admin 邀请码（10 次可用）
            inv = self.create_invite_code(
                label="admin-bootstrap",
                max_uses=10,
            )
            # 用这个码创建 admin 账户
            admin_acc, err = self.create_account(
                username="admin",
                invite_code=inv.code,
                role="admin",
            )
            if admin_acc:
                # 把 account_id 改为 "00000000"（固定 ID，方便记忆）
                # 必须重新读 accounts 找到这个 admin 对象再改
                accounts = self._load_accounts()
                for a in accounts:
                    if a.username == "admin" and a.role == "admin":
                        a.account_id = "00000000"
                        admin_acc = a
                        break
                self._save_accounts(accounts)
                return inv, admin_acc
            return inv, None
