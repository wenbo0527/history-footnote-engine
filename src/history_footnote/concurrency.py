"""🆕 v1.6+ 并发支持层

解决历史注脚体验引擎的并发问题：

Layer 1: 多进程（gunicorn / uwsgi）
Layer 2: 线程池（ThreadPoolExecutor）
Layer 3: per-session Lock（RLock）
Layer 4: LLM 全局并发控制（Semaphore）
Layer 5: 文件 IO 异步写入队列（SaveQueue）

使用示例：
    from history_footnote.concurrency import (
        SessionPool,
        LLMThrottle,
        AsyncSaveQueue,
        run_server,
    )
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ============================================================
# Layer 3: per-session Lock（RLock 防止同线程递归死锁）
# ============================================================

@dataclass
class SessionLock:
    """per-session 锁（带 owner thread 检测）

    RLock 比 Lock 优势：同一线程可重入（防止死锁）
    支持 `with` 语句（context manager protocol）
    """
    session_id: str
    lock: threading.RLock = field(default_factory=threading.RLock)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)

    def acquire(self, timeout: float | None = None) -> bool:
        # 注意：threading.RLock.acquire 不支持 timeout 参数
        # 如需超时，用 acquire(blocking=True) + 单独的超时机制
        acquired = self.lock.acquire(blocking=True)
        if acquired:
            self.last_used_at = time.time()
        return acquired

    def release(self) -> None:
        try:
            self.lock.release()
        except RuntimeError:
            # 重复 release（异常路径）→ 忽略
            pass

    def __enter__(self):
        """支持 `with` 语句"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 `with` 语句"""
        self.release()
        return False


# ============================================================
# Layer 3: SessionPool — 安全的会话池
# ============================================================

class SessionPool:
    """会话池 + LRU 淘汰 + 全局锁保护 dict 操作

    关键设计：
    1. 全局 self._pool_lock 保护 dict 读写（防 race condition）
    2. 每个 session 独立的 RLock（防同会话并发写入）
    3. LRU 淘汰（防内存爆炸）
    4. 异步关闭（释放资源）
    """

    def __init__(self, max_sessions: int = 50, session_ttl_seconds: int = 3600):
        self._pool: OrderedDict[str, tuple[Any, SessionLock]] = OrderedDict()
        self._pool_lock = threading.Lock()
        self.max_sessions = max_sessions
        self.session_ttl_seconds = session_ttl_seconds

    def add(self, session_id: str, game: Any) -> SessionLock:
        """添加会话（线程安全）"""
        with self._pool_lock:
            # LRU 淘汰：如果超过 max_sessions，移除最久未用的
            while len(self._pool) >= self.max_sessions:
                oldest_id = next(iter(self._pool))
                if oldest_id == session_id:
                    break  # 不淘汰刚加入的
                logger.info(f"[SessionPool] LRU 淘汰 session={oldest_id[:8]}")
                self._pool.pop(oldest_id, None)

            session_lock = SessionLock(session_id=session_id)
            self._pool[session_id] = (game, session_lock)
            logger.info(f"[SessionPool] 新增 session={session_id[:8]} (总数 {len(self._pool)})")
            return session_lock

    def get(self, session_id: str) -> tuple[Any, SessionLock] | None:
        """获取会话（线程安全，LRU 更新）"""
        with self._pool_lock:
            entry = self._pool.get(session_id)
            if entry is None:
                return None
            # 更新 LRU 位置
            self._pool.move_to_end(session_id)
            return entry

    def remove(self, session_id: str) -> None:
        """移除会话"""
        with self._pool_lock:
            self._pool.pop(session_id, None)
            logger.info(f"[SessionPool] 移除 session={session_id[:8]} (剩余 {len(self._pool)})")

    def cleanup_expired(self) -> int:
        """清理过期会话（每 N 秒调用一次）"""
        now = time.time()
        expired = []
        with self._pool_lock:
            for sid, (game, lock) in self._pool.items():
                if now - lock.last_used_at > self.session_ttl_seconds:
                    expired.append(sid)
            for sid in expired:
                self._pool.pop(sid, None)
                logger.info(f"[SessionPool] 清理过期 session={sid[:8]}")
        return len(expired)

    def size(self) -> int:
        with self._pool_lock:
            return len(self._pool)

    def list_all(self) -> list[str]:
        with self._pool_lock:
            return list(self._pool.keys())


# ============================================================
# Layer 4: LLM Throttle — 全局并发限流
# ============================================================

class LLMThrottle:
    """LLM 调用限流器

    用 Semaphore 限制同时调用 LLM 的数量：
    - 防止 MiniMax API rate limit
    - 防止本地 CPU/内存爆炸
    - 队列等待 → 自动调度
    """

    def __init__(self, max_concurrent: int = 3, queue_timeout: float = 60.0):
        # 🆕 v1.6.2 默认值：max=3（与全局一致）, queue_timeout=60s（兼容长 LLM 调用）
        self._semaphore = threading.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.queue_timeout = queue_timeout
        self._active = 0
        self._total_calls = 0
        self._lock = threading.Lock()

    def acquire(self, timeout: float | None = None) -> bool:
        """获取 LLM 调用许可"""
        timeout = timeout if timeout is not None else self.queue_timeout
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._active += 1
                self._total_calls += 1
            logger.debug(f"[LLMThrottle] 获得许可 (活跃 {self._active}/{self.max_concurrent})")
        return acquired

    def release(self) -> None:
        """释放 LLM 调用许可"""
        with self._lock:
            self._active = max(0, self._active - 1)
        self._semaphore.release()
        logger.debug(f"[LLMThrottle] 释放许可 (活跃 {self._active}/{self.max_concurrent})")

    def stats(self) -> dict:
        with self._lock:
            return {
                "active": self._active,
                "max_concurrent": self.max_concurrent,
                "total_calls": self._total_calls,
            }

    def __enter__(self):
        if not self.acquire():
            raise TimeoutError("LLM 限流：等待许可超时")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# ============================================================
# Layer 5: AsyncSaveQueue — 异步存档队列
# ============================================================

class AsyncSaveQueue:
    """异步存档写入队列

    设计目标：
    - 不阻塞游戏主循环
    - 串行化存档文件写入（避免 race condition）
    - 失败重试 3 次
    """

    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="async-save",
        )
        self._file_lock = threading.Lock()
        self._pending: dict[str, Future] = {}

    def submit_save(self, save_id: str, save_func: Callable[[], None]) -> Future:
        """提交存档任务"""
        if save_id in self._pending and not self._pending[save_id].done():
            logger.debug(f"[AsyncSaveQueue] 跳过重复存档 save_id={save_id}")
            return self._pending[save_id]

        def _save_with_retry():
            for attempt in range(3):
                try:
                    with self._file_lock:
                        save_func()
                    logger.debug(f"[AsyncSaveQueue] 存档成功 save_id={save_id}")
                    return
                except Exception as e:
                    logger.warning(f"[AsyncSaveQueue] 存档失败（第{attempt+1}次）save_id={save_id}: {e}")
                    time.sleep(0.5 * (attempt + 1))
            logger.error(f"[AsyncSaveQueue] 存档 3 次失败放弃 save_id={save_id}")

        future = self._executor.submit(_save_with_retry)
        self._pending[save_id] = future
        return future

    def wait_all(self, timeout: float = 10.0) -> None:
        """等待所有存档完成"""
        for fut in list(self._pending.values()):
            try:
                fut.result(timeout=timeout)
            except Exception:
                pass

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


# ============================================================
# 全局实例（默认配置）
# ============================================================

SESSION_POOL = SessionPool(max_sessions=50, session_ttl_seconds=3600)
LLM_THROTTLE = LLMThrottle(max_concurrent=3, queue_timeout=120.0)
SAVE_QUEUE = AsyncSaveQueue(max_workers=2)

# 全局 HTTP 线程池（用于 IO 密集操作）
HTTP_EXECUTOR = ThreadPoolExecutor(
    max_workers=20,
    thread_name_prefix="http-handler",
)


# ============================================================
# 过期清理后台线程
# ============================================================

_cleanup_thread_started = False
_cleanup_lock = threading.Lock()


def _start_cleanup_thread() -> None:
    """启动后台清理线程（每 5 分钟清理过期会话）"""
    global _cleanup_thread_started
    with _cleanup_lock:
        if _cleanup_thread_started:
            return
        _cleanup_thread_started = True

    def _cleanup_loop():
        while True:
            time.sleep(300)  # 5 分钟
            try:
                expired = SESSION_POOL.cleanup_expired()
                if expired > 0:
                    logger.info(f"[Cleanup] 清理了 {expired} 个过期会话")
            except Exception as e:
                logger.error(f"[Cleanup] 异常: {e}")

    t = threading.Thread(target=_cleanup_loop, daemon=True, name="session-cleanup")
    t.start()
    logger.info("[Concurrency] 后台清理线程已启动")


# 启动
_start_cleanup_thread()