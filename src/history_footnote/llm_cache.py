"""🆕 v1.7.43 LLM 输出缓存

依据架构诊断：
- 玩家"我又织了一匹湖绫"重复输入时，LLM 重新生成 narrative（30s 等待）
- 应缓存 input hash → narrative 输出

设计：
- cache_key = hash(player_input + state_signature + hints)
- LRU 淘汰（max 1000 条）
- 可禁用（force_refresh=True）

效果：
- 重复 narrative 0 LLM 调用
- 玩家等待 30s → 0.1s
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Optional


_LOG = logging.getLogger("history_footnote.llm_cache")


class LLMCache:
    """LLM 输出缓存（按 input hash）"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        # OrderedDict 用于 LRU
        self._cache: "OrderedDict[str, dict]" = OrderedDict()
        # 统计
        self._hits = 0
        self._misses = 0

    def _make_key(self, player_input: str, state_signature: dict,
                  hints: dict) -> str:
        """生成 cache key"""
        key_data = {
            "input": player_input,
            "state": state_signature,
            "hints": {k: v for k, v in hints.items() if v},
        }
        s = json.dumps(key_data, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def get(self, player_input: str, state_signature: dict,
            hints: dict) -> Optional[dict]:
        """获取缓存（命中返回 dict，否则 None）"""
        key = self._make_key(player_input, state_signature, hints)
        if key in self._cache:
            # 移到末尾（最近用）
            self._cache.move_to_end(key)
            self._hits += 1
            cached = self._cache[key]
            # 标记从缓存
            return {**cached, "_from_cache": True}
        self._misses += 1
        return None

    def put(self, player_input: str, state_signature: dict,
            hints: dict, response: dict) -> None:
        """存入缓存"""
        key = self._make_key(player_input, state_signature, hints)
        # 删除 _from_cache 标记
        clean = {k: v for k, v in response.items() if k != "_from_cache"}
        self._cache[key] = clean
        # LRU 淘汰
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def get_stats(self) -> dict:
        """统计"""
        total = self._hits + self._misses
        return {
            "cache_size": len(self._cache),
            "cache_max": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(total, 1),
        }

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# ============= Global singleton =============

_GLOBAL_CACHE: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """获取全局 LLM 缓存"""
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = LLMCache(max_size=1000)
    return _GLOBAL_CACHE


def reset_llm_cache() -> None:
    global _GLOBAL_CACHE
    _GLOBAL_CACHE = None


# ============= State signature helper =============

def make_state_signature(state) -> dict:
    """生成 state signature（用于 cache key）

    只取关键字段（避免太多变化）
    """
    return {
        "round": state.round_number,
        "city": state.current_city,
        "cash_rounded": round(state.cash or 0, 1),
        "debt_rounded": round(state.debt or 0, 1),
        "items_count": len(state.discoveries.get("items", {}) or {}),
        "persons_count": len(state.discoveries.get("persons", {}) or {}),
        "triggered_count": len(state.triggered_events or []),
    }


# ============= 烟雾测试 =============

if __name__ == "__main__":
    print("=== LLM Cache 烟雾测试 ===\n")
    cache = LLMCache(max_size=3)
    state_sig = {"round": 1, "city": "shengze"}
    hints = {"wiki_hint": "苏州", "drama_hint": ""}

    # 1. miss
    result = cache.get("我织湖绫", state_sig, hints)
    print(f"  1. miss: {result}")
    assert result is None

    # 2. put + get (hit)
    cache.put("我织湖绫", state_sig, hints, {"narrative": "你在织机前坐下..."})
    result = cache.get("我织湖绫", state_sig, hints)
    print(f"  2. hit: {result.get('_from_cache')}, narrative: {result.get('narrative', '')[:20]}")
    assert result is not None and result.get("_from_cache") is True

    # 3. 改 state → miss
    state_sig2 = {"round": 2, "city": "shengze"}
    result = cache.get("我织湖绫", state_sig2, hints)
    print(f"  3. 改 state 后: {result}")
    assert result is None

    # 4. LRU
    cache.put("x1", {"a": 1}, {}, {"n": 1})
    cache.put("x2", {"a": 2}, {}, {"n": 2})
    cache.put("x3", {"a": 3}, {}, {"n": 3})
    cache.put("x4", {"a": 4}, {}, {"n": 4})  # 触发 LRU 淘汰
    print(f"  4. LRU 淘汰: cache_size={len(cache._cache)} (max=3)")
    assert len(cache._cache) == 3

    # 5. stats
    print(f"  5. stats: {cache.get_stats()}")
    print("  ✅ 全部断言通过")
