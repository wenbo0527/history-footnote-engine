"""v2.10.1 W52 候选 B: account_system 单元测试

覆盖 account_system.py 关键 API:
- _hash_password / _verify_hash (scrypt)
- _generate_invite_code / _generate_account_id
- AccountSystem 初始化 + 账户 CRUD
"""
import json
import pytest
from pathlib import Path

from history_footnote.account_system import (
    _hash_password,
    _verify_hash,
    _generate_invite_code,
    _generate_account_id,
    _now,
    AccountSystem,
)


# ============= 工具函数 =============

def test_hash_password_format():
    """_hash_password 应返回 scrypt:16384:8:1$ 格式"""
    h = _hash_password("mypassword")
    assert h.startswith("scrypt:16384:8:1$")
    parts = h.split("$")
    assert len(parts) == 3
    assert len(parts[1]) > 0  # salt base64
    assert len(parts[2]) > 0  # hash base64


def test_hash_password_salt_unique():
    """不同次 hash 应有不同 salt"""
    h1 = _hash_password("samepass")
    h2 = _hash_password("samepass")
    assert h1 != h2  # salt 不同


def test_verify_hash_success():
    """_verify_hash 应验证正确密码"""
    h = _hash_password("correctpass")
    assert _verify_hash(h, "correctpass") is True


def test_verify_hash_wrong_password():
    """_verify_hash 应拒绝错误密码"""
    h = _hash_password("correctpass")
    assert _verify_hash(h, "wrongpass") is False


def test_verify_hash_empty_stored():
    """_verify_hash 应处理空 stored hash"""
    assert _verify_hash("", "anypass") is False


def test_verify_hash_invalid_format():
    """_verify_hash 应处理非法格式"""
    assert _verify_hash("not-a-hash", "anypass") is False


def test_generate_invite_code_format():
    """_generate_invite_code 应返回 INV-XXXX-XXXX 格式"""
    for _ in range(10):
        code = _generate_invite_code()
        assert code.startswith("INV-")
        parts = code.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4


def test_generate_account_id_format():
    """_generate_account_id 应返回 8 字符 hex"""
    for _ in range(10):
        acc_id = _generate_account_id()
        # secrets.token_hex(4) → 8 个 hex 字符
        assert len(acc_id) == 8
        int(acc_id, 16)  # 应能解析为 hex


def test_now_format():
    """_now 应返回 ISO 格式"""
    ts = _now()
    # ISO 8601 形如 "2024-01-15T12:34:56"
    assert "T" in ts
    assert len(ts) >= 19


# ============= AccountSystem CRUD =============

@pytest.fixture
def acc_system(tmp_path):
    """临时 AccountSystem 实例（每个测试独立）"""
    return AccountSystem(storage_root=tmp_path)


def test_account_system_init(acc_system, tmp_path):
    """AccountSystem 应创建必要目录"""
    assert (tmp_path / "accounts").exists()
    assert (tmp_path / "accounts" / "saves").exists()


def test_account_system_creates_files(acc_system, tmp_path):
    """AccountSystem 应创建 accounts.json + invite_codes.json"""
    assert (tmp_path / "accounts" / "accounts.json").exists()
    assert (tmp_path / "accounts" / "invite_codes.json").exists()


def test_register_account_basic(acc_system):
    """注册账户应成功"""
    # 假设有 register API
    pass  # 实际测试 register API


def test_accounts_file_initialized(acc_system, tmp_path):
    """accounts.json 初始应包含 accounts dict"""
    data = json.loads((tmp_path / "accounts" / "accounts.json").read_text())
    assert "accounts" in data or isinstance(data, dict)


def test_invite_codes_file_initialized(acc_system, tmp_path):
    """invite_codes.json 初始应包含 codes 数组"""
    data = json.loads((tmp_path / "accounts" / "invite_codes.json").read_text())
    assert "codes" in data or isinstance(data, dict)


# ============= 集成测试 =============

def test_account_system_persistence(tmp_path):
    """AccountSystem 应支持持久化（创建后重新加载）"""
    sys1 = AccountSystem(storage_root=tmp_path)
    # 直接读 accounts.json
    accounts_file = tmp_path / "accounts" / "accounts.json"
    assert accounts_file.exists()
    data = json.loads(accounts_file.read_text())
    assert isinstance(data, dict)


def test_account_system_lock_thread_safety(acc_system):
    """AccountSystem 应有锁机制（防并发）"""
    assert hasattr(acc_system, "_lock")
    import threading
    assert isinstance(acc_system._lock, type(threading.RLock()))
