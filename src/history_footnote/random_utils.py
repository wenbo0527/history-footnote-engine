"""
random_utils.py - 全局随机种子工具（v2.5）

设计动机：
- 之前所有 random.* 调用都是无 seed → 每次运行不同 → 无法重放
- 现在所有 random 都通过 get_rng(session_id) 获取 seeded random
- 同一 session_id + 同一调用顺序 = 同一结果

使用规范：
    from history_footnote.random_utils import get_rng
    rng = get_rng(session_id)
    result = rng.choices(items, weights=weights)[0]

优势：
- 后向兼容：不传 seed 用全局 random
- 可重放：同 session_id + 相同状态 = 同结果
- 易测试：测试时可固定 seed
"""
from __future__ import annotations

import random
from typing import Optional


# 全局 Random 实例池（per-session）
# 同一个 session_id 永远返回同一个 Random
_rng_pool: dict[str, random.Random] = {}


def set_session_seed(session_id: str, seed: int) -> None:
    """显式设置某 session 的 seed（创建 game 时调用）

    后续 get_rng(session_id) 返回的 Random 用此 seed
    """
    _rng_pool[session_id] = random.Random(seed)


def get_rng(session_id: Optional[str] = None) -> random.Random:
    """获取 session 的 seeded Random 实例

    Args:
        session_id: session 标识。如果为 None 或没设置过 seed，
                    返回全局 random.Random()（不可重放）

    Returns:
        Random 实例。同 session_id 永远同一实例
    """
    if not session_id:
        return random.Random()
    if session_id not in _rng_pool:
        # 第一次访问：生成随机 seed
        _rng_pool[session_id] = random.Random()
    return _rng_pool[session_id]


def remove_session_rng(session_id: str) -> None:
    """清理 session 的 rng（session 结束时调用，避免内存泄漏）"""
    _rng_pool.pop(session_id, None)


def generate_random_seed() -> int:
    """生成一个 32 位随机 seed（用于玩家首次创建 game）"""
    return random.randint(0, 2**31 - 1)


def make_seed_from_string(s: str) -> int:
    """从字符串生成确定 seed（用于"同 seed 重玩"分享）

    例: make_seed_from_string("wanli1587-love-story") -> 固定 32-bit int
    """
    import hashlib
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)  # 取前 8 位 → 32-bit int


__all__ = [
    "set_session_seed",
    "get_rng",
    "remove_session_rng",
    "generate_random_seed",
    "make_seed_from_string",
]
