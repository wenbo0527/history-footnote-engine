"""并发支持层单元测试"""
import sys
import threading
import time
sys.path.insert(0, "src")

from history_footnote.concurrency import (
    SessionPool,
    LLMThrottle,
    AsyncSaveQueue,
    SessionLock,
    SESSION_POOL,
    LLM_THROTTLE,
    SAVE_QUEUE,
)


def test_session_pool_basic():
    """基本添加/获取/移除"""
    pool = SessionPool(max_sessions=10)
    pool.add("s1", "game1")
    pool.add("s2", "game2")

    entry = pool.get("s1")
    assert entry is not None
    assert entry[0] == "game1"

    pool.remove("s1")
    assert pool.get("s1") is None
    print("✅ test_session_pool_basic: 增删查正常")


def test_session_pool_lru():
    """LRU 淘汰机制"""
    pool = SessionPool(max_sessions=2)
    pool.add("s1", "g1")
    pool.add("s2", "g2")
    # 访问 s1（更新 LRU）
    pool.get("s1")
    # 添加 s3 → 应淘汰 s2（最久未用）
    pool.add("s3", "g3")
    assert pool.get("s2") is None  # s2 被淘汰
    assert pool.get("s1") is not None
    assert pool.get("s3") is not None
    print("✅ test_session_pool_lru: LRU 淘汰正确")


def test_session_pool_concurrent_safety():
    """并发安全：多线程同时增删"""
    pool = SessionPool(max_sessions=300)  # 大于 250
    errors = []

    def worker(i):
        try:
            for j in range(50):
                sid = f"s_{i}_{j}"
                pool.add(sid, f"game_{i}_{j}")
                pool.get(sid)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"并发错误: {errors}"
    # 应有 5 * 50 = 250 个 session
    assert pool.size() == 250, f"应有 250 个，实际 {pool.size()}"
    print(f"✅ test_session_pool_concurrent_safety: 250 个并发 session 正常")


def test_llm_throttle_limit():
    """LLM 限流：max=2 时只能同时跑 2 个"""
    throttle = LLMThrottle(max_concurrent=2)
    active = [0]
    peak = [0]
    lock = threading.Lock()

    def worker(i):
        with throttle:
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.1)
            with lock:
                active[0] -= 1

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert peak[0] <= 2, f"峰值 {peak[0]} 超过 max=2"
    print(f"✅ test_llm_throttle_limit: 限流正确（峰值 {peak[0]}/2）")


def test_llm_throttle_stats():
    """LLM 限流统计"""
    throttle = LLMThrottle(max_concurrent=2)

    def worker():
        with throttle:
            time.sleep(0.02)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    # 等所有线程跑完再读统计
    for t in threads:
        t.join()
    stats = throttle.stats()
    assert stats["total_calls"] == 5, f"应有 5 次调用，实际 {stats['total_calls']}"
    print(f"✅ test_llm_throttle_stats: 统计正常（total={stats['total_calls']}）")


def test_async_save_queue():
    """异步存档队列"""
    queue = AsyncSaveQueue(max_workers=2)
    counter = [0]
    lock = threading.Lock()

    def save_task(save_id):
        with lock:
            counter[0] += 1

    futures = [queue.submit_save(f"s{i}", lambda i=i: save_task(i)) for i in range(5)]
    queue.wait_all(timeout=5.0)
    queue.shutdown(wait=True)

    assert counter[0] == 5, f"应有 5 次写入，实际 {counter[0]}"
    print(f"✅ test_async_save_queue: 5 个异步存档全部完成")


def test_session_lock_reentrant():
    """RLock 重入性（同线程可多次 acquire）"""
    lock = SessionLock(session_id="test")
    with lock.lock:
        # 同一线程重入 → 不应死锁
        with lock.lock:
            with lock.lock:
                pass
    print("✅ test_session_lock_reentrant: RLock 递归正常")


def test_global_session_pool_thread_safety():
    """全局 SESSION_POOL 多线程安全"""
    initial_size = SESSION_POOL.size()

    def worker(i):
        SESSION_POOL.add(f"global_test_{i}", f"game_{i}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert SESSION_POOL.size() >= initial_size + 10
    # 清理
    for i in range(10):
        SESSION_POOL.remove(f"global_test_{i}")
    print("✅ test_global_session_pool_thread_safety: 全局 SessionPool 安全")


if __name__ == "__main__":
    print("=" * 50)
    print("并发支持层单元测试")
    print("=" * 50)
    test_session_pool_basic()
    test_session_pool_lru()
    test_session_pool_concurrent_safety()
    test_llm_throttle_limit()
    test_llm_throttle_stats()
    test_async_save_queue()
    test_session_lock_reentrant()
    test_global_session_pool_thread_safety()
    print("\n✅ 所有测试通过")