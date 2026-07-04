"""历史注脚体验引擎 - 主入口

🆕 v1.7.2 架构改进：
- __init__.py 集中 logging 配置
- 所有子模块继承统一日志格式
- 避免在每个模块重复 basicConfig
"""
from __future__ import annotations

import logging
import os

# 注意：必须在任何子模块 import logging 之前
_LOGGING_CONFIGURED = False


def _configure_logging():
    """集中配置 logging

    - 格式：时间 [等级] 模块名: 消息
    - 等级：LOG_LEVEL 环境变量（默认 INFO）
    - 输出：stderr 或 LOG_FILE 指定文件
    - 重复调用安全（避免 basicConfig 覆盖）
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    from history_footnote.config import Logging

    level = getattr(logging, Logging.LEVEL.upper(), logging.INFO)
    fmt = Logging.FORMAT
    formatter = logging.Formatter(fmt)

    # 输出到 stderr（默认）或文件
    handlers: list[logging.Handler] = []
    if Logging.LOG_FILE:
        try:
            file_handler = logging.FileHandler(Logging.LOG_FILE, encoding="utf-8")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except OSError as e:
            # 文件打开失败 → fallback stderr
            print(f"[logging] 文件打开失败 {Logging.LOG_FILE}: {e}, fallback to stderr")
    if not handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)

    root = logging.getLogger()
    root.setLevel(level)
    # 清除已有 handlers（防止重复）
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)

    # 第三方库的噪音调高
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("http.server").setLevel(logging.WARNING)

    _LOGGING_CONFIGURED = True

    # 启动日志
    logger = logging.getLogger(__name__)
    from history_footnote.config import log_config_on_startup
    log_config_on_startup(logger)


# 自动配置（import history_footnote 时触发）
_configure_logging()
