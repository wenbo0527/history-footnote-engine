"""🆕 v1.7.2 统一配置中心

把所有魔法数字集中管理：
- 限流参数
- 容量限制
- 超时时间
- LLM 端点

支持环境变量覆盖（生产环境用）。

设计原则：
- 单一权威（其他模块从这里 import，不要再硬编码）
- 类型安全（用 NewType 避免误用）
- 向后兼容（默认值与原硬编码一致）
"""
from __future__ import annotations

import os
from typing import NewType


# ============================================================
# 类型定义（防止误用）
# ============================================================

Seconds = NewType("Seconds", float)
Rounds = NewType("Rounds", int)


def _getenv_int(key: str, default: int) -> int:
    """从环境变量读 int，解析失败用默认值"""
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _getenv_float(key: str, default: float) -> float:
    """从环境变量读 float，解析失败用默认值"""
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _getenv_str(key: str, default: str) -> str:
    """从环境变量读 string"""
    return os.getenv(key, default)


def _getenv_bool(key: str, default: bool) -> bool:
    """从环境变量读 bool"""
    val = os.getenv(key, "").lower()
    if val in ("1", "true", "yes", "y"):
        return True
    if val in ("0", "false", "no", "n"):
        return False
    return default


# ============================================================
# 应用信息
# ============================================================

# 版本号（与 issue_reporter.py 保持同步）
# ⚠️ 升级版本时同时修改这两个文件
# 未来可改为 issue_reporter → config 的单向依赖
APP_VERSION = _getenv_str("APP_VERSION", "1.7.23")
APP_VERSION_NAME = _getenv_str("APP_VERSION_NAME", "v1.7.23 - 内测版")
APP_IS_BETA = _getenv_bool("APP_IS_BETA", True)


# ============================================================
# Rate Limits（限流）
# ============================================================

class RateLimits:
    """限流配置（web_enhancements.py 使用）"""
    # 全局每分钟
    GLOBAL_MAX_REQUESTS = _getenv_int("GLOBAL_MAX_REQUESTS", 60)
    GLOBAL_WINDOW_SECONDS = _getenv_float("GLOBAL_WINDOW_SECONDS", 60.0)
    # LLM 每分钟（更严）
    LLM_MAX_REQUESTS = _getenv_int("LLM_MAX_REQUESTS", 20)
    LLM_WINDOW_SECONDS = _getenv_float("LLM_WINDOW_SECONDS", 60.0)
    # 短时限流（防突发）
    BURST_MAX_REQUESTS = _getenv_int("BURST_MAX_REQUESTS", 3)
    BURST_WINDOW_SECONDS = _getenv_float("BURST_WINDOW_SECONDS", 1.0)


# ============================================================
# Concurrency（并发）
# ============================================================

class Concurrency:
    """并发配置（concurrency.py 使用）"""
    # 全局 LLM 并发数
    MAX_CONCURRENT = _getenv_int("MAX_CONCURRENT", 3)
    # 队列等待超时（LLM 调用可能慢）
    QUEUE_TIMEOUT_SECONDS = _getenv_float("QUEUE_TIMEOUT_SECONDS", 60.0)


# ============================================================
# Wiki Limits（知识图谱容量）
# ============================================================

class WikiLimits:
    """Character Wiki 容量限制（character_wiki.py 使用）"""
    MAX_CHARACTERS = _getenv_int("WIKI_MAX_CHARACTERS", 50)
    MAX_EVENTS = _getenv_int("WIKI_MAX_EVENTS", 200)
    MAX_DECISIONS = _getenv_int("WIKI_MAX_DECISIONS", 200)


# ============================================================
# Narrative（叙事容量）
# ============================================================

class Narrative:
    """叙事缓冲（game_state.py 使用）"""
    RECENT_SIZE = _getenv_int("NARRATIVE_RECENT_SIZE", 20)
    ARCHIVE_SIZE = _getenv_int("NARRATIVE_ARCHIVE_SIZE", 100)
    ARCHIVE_SUMMARY_MAX = _getenv_int("NARRATIVE_ARCHIVE_SUMMARY_MAX", 200)


# ============================================================
# Sanitizer（清洗阈值）
# ============================================================

class Sanitizer:
    """叙事清洗阈值（narrative_sanitizer.py 使用）"""
    # 清洗后 < 此字符数视为"全是元数据"，fallback
    MIN_LENGTH = _getenv_int("SANITIZER_MIN_LENGTH", 5)
    FALLBACK_TEXT = _getenv_str("SANITIZER_FALLBACK", "时间流逝。一切如常。")


# ============================================================
# Issue Reporter（反馈）
# ============================================================

class Feedback:
    """反馈系统（issue_reporter.py 使用）"""
    # 保存目录
    SAVE_DIR = _getenv_str("FEEDBACK_SAVE_DIR", "/tmp/issues")
    # 单条描述最大字符
    MAX_DESCRIPTION_LENGTH = _getenv_int("FEEDBACK_MAX_DESC", 5000)
    MIN_DESCRIPTION_LENGTH = _getenv_int("FEEDBACK_MIN_DESC", 5)
    # 分类（与 issue_reporter.ISSUE_CATEGORIES 同步）
    CATEGORIES = ["bug", "narrative", "ui", "feature", "data", "other"]


# ============================================================
# Logging（日志）
# ============================================================

class Logging:
    """日志配置（__init__.py 使用）"""
    LEVEL = _getenv_str("LOG_LEVEL", "INFO")
    FORMAT = _getenv_str(
        "LOG_FORMAT",
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # 关键路径（生产环境可设）
    LOG_FILE = _getenv_str("LOG_FILE", "")  # 空 = stderr


# ============================================================
# Server（HTTP 服务）
# ============================================================

class Server:
    """HTTP 服务（web_server.py 使用）"""
    DEFAULT_PORT = _getenv_int("WEB_PORT", 8765)
    DEFAULT_HOST = _getenv_str("WEB_HOST", "0.0.0.0")
    # 请求体最大尺寸
    MAX_REQUEST_SIZE = _getenv_int("WEB_MAX_REQUEST_SIZE", 1024 * 1024)  # 1MB


# ============================================================
# 集中导出
# ============================================================

__all__ = [
    "APP_VERSION", "APP_VERSION_NAME", "APP_IS_BETA",
    "RateLimits", "Concurrency", "WikiLimits",
    "Narrative", "Sanitizer", "Feedback",
    "Logging", "Server",
    "Seconds", "Rounds",
]


# ============================================================
# 便捷函数
# ============================================================

def log_config_on_startup(logger):
    """启动时打印所有关键配置（debug 用）"""
    logger.info("=" * 50)
    logger.info(f"应用: {APP_VERSION_NAME} (v{APP_VERSION}, beta={APP_IS_BETA})")
    logger.info(f"限流: 全局 {RateLimits.GLOBAL_MAX_REQUESTS}/{RateLimits.GLOBAL_WINDOW_SECONDS}s, "
                f"LLM {RateLimits.LLM_MAX_REQUESTS}/{RateLimits.LLM_WINDOW_SECONDS}s, "
                f"突发 {RateLimits.BURST_MAX_REQUESTS}/{RateLimits.BURST_WINDOW_SECONDS}s")
    logger.info(f"并发: {Concurrency.MAX_CONCURRENT} (timeout {Concurrency.QUEUE_TIMEOUT_SECONDS}s)")
    logger.info(f"Wiki: {WikiLimits.MAX_CHARACTERS} 角色 / {WikiLimits.MAX_EVENTS} 事件 / {WikiLimits.MAX_DECISIONS} 决策")
    logger.info(f"Narrative: {Narrative.RECENT_SIZE} recent + {Narrative.ARCHIVE_SIZE} archive")
    logger.info(f"Server: {Server.DEFAULT_HOST}:{Server.DEFAULT_PORT}")
    logger.info("=" * 50)


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print(f"Config Test (v{APP_VERSION})")
    print("=" * 50)
    print(f"APP_VERSION_NAME: {APP_VERSION_NAME}")
    print(f"GLOBAL_RATE: {RateLimits.GLOBAL_MAX_REQUESTS}/{RateLimits.GLOBAL_WINDOW_SECONDS}s")
    print(f"LLM_RATE: {RateLimits.LLM_MAX_REQUESTS}/{RateLimits.LLM_WINDOW_SECONDS}s")
    print(f"MAX_CONCURRENT: {Concurrency.MAX_CONCURRENT}")
    print(f"WIKI_MAX_CHARACTERS: {WikiLimits.MAX_CHARACTERS}")
    print(f"NARRATIVE_RECENT_SIZE: {Narrative.RECENT_SIZE}")
    print(f"SANITIZER_MIN_LENGTH: {Sanitizer.MIN_LENGTH}")
    print(f"LOG_LEVEL: {Logging.LEVEL}")
    print(f"WEB_PORT: {Server.DEFAULT_PORT}")

    # 测试类型安全
    import logging as _logging
    logger = _logging.getLogger("test")
    log_config_on_startup(logger)
    print("\n✅ Config 加载成功")