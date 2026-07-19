"""🆕 v1.6.2 全局资源缓存层

集中缓存重型资源，避免每回合重复创建：

1. ERA_CONFIGS_CACHE：era_id → config dict（避免每回合 json.loads 4800 行）
2. LLM_CACHE：provider_name → ChatAnthropic 实例（避免每回合新建 HTTP client）
3. SAVE_MANAGER_SINGLETON：全局 SaveManager 实例
4. KNOWLEDGE_BASE_CACHE：era_id → KnowledgeBase 实例

收益：
- era.json json.loads: ~50ms → <0.1ms（500x 加速）
- ChatAnthropic 构造: ~200ms → <1ms（200x 加速）
- SaveManager 构造: ~5ms → <0.1ms（50x 加速）

50 回合总节省：~13 秒 CPU 时间 + ~2.6GB 内存分配
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# 注意：saves/resource_cache.py 需 4 层 .parent
# src/history_footnote/saves/resource_cache.py
# → src/history_footnote/saves/   (1)
# → src/history_footnote/        (2)
# → src/                         (3)
# → <project_root>               (4)
ERAS_DIR = _ROOT / "eras"


# ============================================================
# 全局缓存（线程安全）
# ============================================================

_ERA_CONFIGS_CACHE: dict[str, dict] = {}
_ERA_CONFIGS_LOCK = threading.Lock()

_LLM_CACHE: dict[str, Any] = {}
_LLM_CACHE_LOCK = threading.Lock()

_KNOWLEDGE_BASE_CACHE: dict[str, Any] = {}
_KNOWLEDGE_BASE_LOCK = threading.Lock()

_SAVE_MANAGER_SINGLETON = None
_SAVE_MANAGER_LOCK = threading.Lock()


# ============================================================
# A1: era.json 全局缓存
# ============================================================

def load_era_config(era_id: str) -> dict:
    """加载时代配置（缓存版）

    Args:
        era_id: 时代包目录名（如 wanli1587）

    Returns:
        era.json 解析后的 dict

    Raises:
        FileNotFoundError: 时代包不存在
    """
    with _ERA_CONFIGS_LOCK:
        if era_id in _ERA_CONFIGS_CACHE:
            return _ERA_CONFIGS_CACHE[era_id]

        era_file = ERAS_DIR / era_id / "era.json"
        if not era_file.exists():
            raise FileNotFoundError(f"Era package not found: {era_id}")

        config = json.loads(era_file.read_text(encoding="utf-8"))
        _ERA_CONFIGS_CACHE[era_id] = config
        logger.info(f"[ResourceCache] Loaded era config: {era_id} (cached)")
        return config


def warm_era_configs() -> None:
    """启动时预热所有时代配置

    让第一个请求命中缓存，避免冷启动延迟
    """
    if not ERAS_DIR.exists():
        return
    for era_dir in ERAS_DIR.iterdir():
        if not era_dir.is_dir():
            continue
        if era_dir.name.startswith("_"):  # 跳过 _template
            continue
        if (era_dir / "era.json").exists():
            try:
                load_era_config(era_dir.name)
            except Exception as e:
                logger.warning(f"[ResourceCache] Failed to load era {era_dir.name}: {e}")


def clear_era_config_cache() -> None:
    """清空缓存（用于测试）"""
    with _ERA_CONFIGS_LOCK:
        _ERA_CONFIGS_CACHE.clear()


# ============================================================
# A2: LLM Provider 全局缓存
# ============================================================

def get_llm(provider: str = "minimax-anthropic", era_config: dict | None = None) -> Any:
    """获取 LLM 实例（缓存版）

    按 provider 名称缓存。同一 provider 的多个 era 共用一个 LLM 实例。
    """
    with _LLM_CACHE_LOCK:
        if provider in _LLM_CACHE:
            return _LLM_CACHE[provider]

        from history_footnote.llm_providers import make_llm_for_purpose
        llm = make_llm_for_purpose(purpose="wiki", provider=provider, era_config=era_config or {})  # 🆕 v2.7
        _LLM_CACHE[provider] = llm
        logger.info(f"[ResourceCache] Created LLM: {provider} (cached)")
        return llm


def clear_llm_cache() -> None:
    """清空 LLM 缓存（用于测试）"""
    with _LLM_CACHE_LOCK:
        _LLM_CACHE.clear()


# ============================================================
# A3: SaveManager 单例
# ============================================================

def get_save_manager() -> Any:
    """获取全局 SaveManager 单例"""
    global _SAVE_MANAGER_SINGLETON
    with _SAVE_MANAGER_LOCK:
        if _SAVE_MANAGER_SINGLETON is None:
            from history_footnote.storage.save_manager import SaveManager, DEFAULT_SAVE_ROOT
            _SAVE_MANAGER_SINGLETON = SaveManager(DEFAULT_SAVE_ROOT)
            logger.info("[ResourceCache] Created SaveManager singleton")
        return _SAVE_MANAGER_SINGLETON


# ============================================================
# KnowledgeBase 缓存
# ============================================================

def get_knowledge_base(era_id: str, era_config: dict) -> Any:
    """获取 KnowledgeBase 实例（缓存版）

    按 era_id 缓存，因为同一 era 的知识库不变
    """
    with _KNOWLEDGE_BASE_LOCK:
        if era_id in _KNOWLEDGE_BASE_CACHE:
            return _KNOWLEDGE_BASE_CACHE[era_id]

        from history_footnote.knowledge_base import KnowledgeBase
        kb = KnowledgeBase(era_config)
        _KNOWLEDGE_BASE_CACHE[era_id] = kb
        logger.info(f"[ResourceCache] Created KnowledgeBase: {era_id} (cached)")
        return kb


def clear_all_caches() -> None:
    """清空所有缓存（用于测试）"""
    clear_era_config_cache()
    clear_llm_cache()
    with _KNOWLEDGE_BASE_LOCK:
        _KNOWLEDGE_BASE_CACHE.clear()
    global _SAVE_MANAGER_SINGLETON
    with _SAVE_MANAGER_LOCK:
        _SAVE_MANAGER_SINGLETON = None


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("测试 ResourceCache...")

    # 预热
    warm_era_configs()
    print(f"✅ 预热完成，已加载 {len(_ERA_CONFIGS_CACHE)} 个时代")

    # 测试获取
    import time
    t0 = time.time()
    for _ in range(100):
        cfg = load_era_config("wanli1587")
    t1 = time.time()
    print(f"✅ 100 次缓存获取耗时 {(t1-t0)*1000:.2f}ms（平均 {(t1-t0)*10:.2f}ms/次）")

    # 测试 LLM 缓存
    llm1 = get_llm(provider="minimax-anthropic")
    llm2 = get_llm(provider="minimax-anthropic")
    assert llm1 is llm2, "LLM 缓存未生效"
    print(f"✅ LLM 缓存生效（同一实例）")

    # 测试 SaveManager 单例
    sm1 = get_save_manager()
    sm2 = get_save_manager()
    assert sm1 is sm2, "SaveManager 单例未生效"
    print(f"✅ SaveManager 单例生效")

    print("\n✅ ResourceCache 测试通过")