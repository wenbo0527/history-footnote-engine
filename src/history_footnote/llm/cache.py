"""🆕 v1.9.2 LLM 响应缓存 + 降级

设计目标：
- LLM 成功时：写缓存（hash → character + raw）
- LLM 失败时：找最近一次同类缓存（避免"character generation failed"）
- 模糊匹配：关键词 Jaccard ≥ 0.6 视为同一类

存：saves/llm_cache.json（每次写入即同步落盘）
"""
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Optional, Tuple

CACHE_PATH = Path("saves/llm_cache.json")
_SIMILARITY_THRESHOLD = 0.3  # 🆕 v1.9.2 调低（短文本 Jaccard 严，0.3 更宽松）


def _load() -> dict:
    """读缓存（dict: hash → entry）"""
    try:
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(cache: dict) -> None:
    """写缓存（落盘）"""
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _extract_keywords(text: str) -> set:
    """提取关键词（2+ 字中文词 / 简单分词）"""
    if not text:
        return set()
    # 移除标点
    text = re.sub(r"[，。！？、；：\"'…—()（）\[\]【】\s]+", " ", text)
    # 2+ 字词 + 1 字高频词
    words = set()
    # 2-4 字词
    for n in (2, 3, 4):
        for i in range(len(text) - n + 1):
            w = text[i:i + n].strip()
            if w:
                words.add(w)
    # 1 字高频
    common_1 = set("你我他她它织机工农商兵学教买卖钱银税关局")  # 常用字
    for c in text:
        if c in common_1:
            words.add(c)
    return words


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


def make_key(era_id: str, gender: str, location: str, identity: str, life_exp: str) -> str:
    """🆕 v1.9.4 双层缓存键（带 _type 区分公共/玩家层）"""
    raw = f"{era_id}|{gender}|{location}|{identity}|{life_exp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_player_key(account_id: str, era_id: str, gender: str, location: str, identity: str, life_exp: str) -> str:
    """🆕 v1.9.4 玩家层缓存键（带 account_id 隔离）"""
    raw = f"player:{account_id}|{era_id}|{gender}|{location}|{identity}|{life_exp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get(era_id: str, gender: str, location: str, identity: str, life_exp: str, account_id: str = "") -> Optional[dict]:
    """🆕 v1.9.4 查精确匹配：先玩家层（account_id），再公共层（无 account）"""
    cache = _load()
    # 1. 玩家层
    if account_id:
        key = make_player_key(account_id, era_id, gender, location, identity, life_exp)
        entry = cache.get(key)
        if entry:
            entry["cache_hit"] = "exact_player"
            return entry
    # 2. 公共层（不查精确，只模糊 + 兜底）
    key = make_key(era_id, gender, location, identity, life_exp)
    entry = cache.get(key)
    if entry:
        entry["cache_hit"] = "exact_public"
        return entry
    return None


def find_similar(era_id: str, gender: str, location: str, identity: str, life_exp: str, account_id: str = "") -> Optional[dict]:
    """🆕 v1.9.4 模糊匹配：先玩家层（account_id），再公共层"""
    cache = _load()
    target_kw = _extract_keywords(f"{location} {identity} {life_exp}")
    # 1. 玩家层模糊
    if account_id:
        candidates = []
        for k, entry in cache.items():
            if not k.startswith("player:"):
                continue
            if entry.get("era_id") != era_id or entry.get("gender") != gender:
                continue
            if entry.get("account_id") != account_id:
                continue
            c_kw = _extract_keywords(f"{entry.get('location', '')} {entry.get('identity', '')} {entry.get('life_exp', '')}")
            sim = _jaccard(target_kw, c_kw)
            if sim >= _SIMILARITY_THRESHOLD:
                candidates.append((sim, entry))
        if candidates:
            candidates.sort(key=lambda x: (x[0], x[1].get("ts", 0)), reverse=True)
            best = candidates[0][1].copy()
            best["cache_hit"] = f"similar_player:{candidates[0][0]:.2f}"
            return best
    # 2. 公共层模糊（不区分玩家）
    candidates = []
    for k, entry in cache.items():
        if k.startswith("player:"):
            continue  # 跳过玩家层
        if entry.get("era_id") != era_id or entry.get("gender") != gender:
            continue
        c_kw = _extract_keywords(f"{entry.get('location', '')} {entry.get('identity', '')} {entry.get('life_exp', '')}")
        sim = _jaccard(target_kw, c_kw)
        if sim >= _SIMILARITY_THRESHOLD:
            candidates.append((sim, entry))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1].get("ts", 0)), reverse=True)
    best = candidates[0][1].copy()
    best["cache_hit"] = f"similar_public:{candidates[0][0]:.2f}"
    return best


def find_latest(era_id: str, account_id: str = "") -> Optional[dict]:
    """🆕 v1.9.4 兜底：先玩家层（account_id），再公共层"""
    cache = _load()
    # 1. 玩家层兜底
    if account_id:
        latest, latest_ts = None, 0
        for k, entry in cache.items():
            if not k.startswith("player:"):
                continue
            if entry.get("account_id") != account_id or entry.get("era_id") != era_id:
                continue
            ts = entry.get("ts", 0)
            if ts > latest_ts:
                latest_ts = ts
                latest = entry
        if latest:
            latest = latest.copy()
            latest["cache_hit"] = "latest_player"
            return latest
    # 2. 公共层兜底
    latest, latest_ts = None, 0
    for k, entry in cache.items():
        if k.startswith("player:"):
            continue
        if entry.get("era_id") != era_id:
            continue
        ts = entry.get("ts", 0)
        if ts > latest_ts:
            latest_ts = ts
            latest = entry
    if latest:
        latest = latest.copy()
        latest["cache_hit"] = "latest_public"
    return latest


def put(era_id: str, gender: str, location: str, identity: str, life_exp: str,
        character: dict, raw: str, account_id: str = "") -> None:
    """🆕 v1.9.4 双层写：玩家层（account_id）+ 公共层"""
    cache = _load()
    ts = int(time.time())
    # 1. 公共层（无 account）
    public_key = make_key(era_id, gender, location, identity, life_exp)
    cache[public_key] = {
        "type": "public",
        "era_id": era_id,
        "gender": gender,
        "location": location,
        "identity": identity,
        "life_exp": life_exp,
        "character": character,
        "raw": raw,
        "ts": ts,
    }
    # 2. 玩家层（带 account_id）
    if account_id:
        player_key = make_player_key(account_id, era_id, gender, location, identity, life_exp)
        cache[player_key] = {
            "type": "player",
            "account_id": account_id,
            "era_id": era_id,
            "gender": gender,
            "location": location,
            "identity": identity,
            "life_exp": life_exp,
            "character": character,
            "raw": raw,
            "ts": ts,
        }
    # 限制大小（保留最新 500 条总）
    if len(cache) > 500:
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("ts", 0), reverse=True)
        for k in sorted_keys[500:]:
            del cache[k]
    _save(cache)


def stats() -> dict:
    """缓存统计"""
    cache = _load()
    return {
        "size": len(cache),
        "path": str(CACHE_PATH),
        "threshold": _SIMILARITY_THRESHOLD,
    }


# ============================================================
# 🆕 v1.9.3 narrative cache（按 action 文本缓存）
# ============================================================

def get_narrative(action_key: str) -> Optional[dict]:
    """查 narrative 精确缓存"""
    cache = _load()
    return cache.get(f"narr:{action_key}")


def put_narrative(action_key: str, narrative: str) -> None:
    """写 narrative 缓存"""
    cache = _load()
    cache[f"narr:{action_key}"] = {
        "type": "narrative",
        "action_key": action_key,
        "narrative": narrative,
        "ts": int(time.time()),
    }
    if len(cache) > 500:  # narrative 缓存更多
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("ts", 0), reverse=True)
        for k in sorted_keys[500:]:
            del cache[k]
    _save(cache)


def make_narrative_key(state_dict: dict, player_input: str) -> str:
    """🆕 v1.9.3 narrative 缓存键（基于 state + action 简化 hash）"""
    # 只 hash 关键 state 字段（避免 state 变化大导致缓存失效）
    key_state = {
        "round": state_dict.get("current_round", 0),
        "city": state_dict.get("current_city", ""),
        "occupation": (state_dict.get("character", {}) or {}).get("occupation", ""),
    }
    raw = f"{key_state}|{player_input.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
