"""KV 缓存单元测试"""
import sys
sys.path.insert(0, "src")

from history_footnote.kv_cache import (
    SystemPromptCache,
    GameSessionCache,
    CacheStats,
    GLOBAL_STATS,
    SYSTEM_PROMPT_CACHE,
    estimate_savings,
    get_cache_control_for_system,
)


def test_basic_cache_hit_miss():
    """基本缓存命中/未命中测试"""
    cache = SystemPromptCache()
    prompt = "你是万历十五年的 DM..."

    # 第 1 次：未命中
    cache.get_cache_control(prompt)
    assert cache.get_stats().cache_misses == 1
    assert cache.get_stats().cache_hits == 0

    # 第 2 次相同 prompt：命中
    cache.get_cache_control(prompt)
    assert cache.get_stats().cache_hits == 1
    assert cache.get_stats().cache_misses == 1

    # 第 3 次不同 prompt：未命中
    cache.get_cache_control("另一个 prompt")
    assert cache.get_stats().cache_misses == 2
    assert cache.get_stats().cache_hits == 1

    # 第 4 次又用第一个 prompt：未命中（之前的 hash 不同）
    cache.get_cache_control(prompt)
    assert cache.get_stats().cache_misses == 3
    assert cache.get_stats().cache_hits == 1

    print(f"✅ test_basic_cache_hit_miss: {cache.get_stats()}")


def test_hit_rate_calculation():
    """命中率计算"""
    cache = SystemPromptCache()
    prompt = "固定 prompt"

    for _ in range(10):
        cache.get_cache_control(prompt)

    # 第 1 次 miss + 9 次 hit = 90% 命中率
    stats = cache.get_stats()
    assert stats.hit_rate == 0.9, f"应为 90%，实际 {stats.hit_rate * 100:.0f}%"
    print(f"✅ test_hit_rate_calculation: hit_rate={stats.hit_rate * 100:.0f}%")


def test_real_scenario_50_rounds():
    """模拟 50 回合游戏（system prompt 不变）"""
    cache = SystemPromptCache()
    fixed_prompt = "你是万历十五年的 DM。" * 100  # 1500 tokens 的固定 prompt

    for _ in range(50):
        cache.get_cache_control(fixed_prompt)

    stats = cache.get_stats()
    expected_hit_rate = 49 / 50  # 第 1 次 miss + 49 次 hit
    assert abs(stats.hit_rate - expected_hit_rate) < 0.01
    print(f"✅ test_real_scenario_50_rounds: 50 回合命中率={stats.hit_rate * 100:.0f}%")


def test_get_cache_control_returns_ephemeral():
    """cache_control 配置"""
    cc = get_cache_control_for_system()
    assert cc == {"type": "ephemeral"}
    print(f"✅ test_get_cache_control_returns_ephemeral: {cc}")


def test_estimate_savings():
    """节省估算"""
    # 50 回合 × 1500 tokens = 75,000 tokens 系统 prompt
    saved = estimate_savings(75000, "minimax")
    assert saved > 0
    print(f"✅ test_estimate_savings: 节省 ${saved:.4f}")


def test_game_session_cache():
    """单局游戏缓存"""
    session = GameSessionCache(session_id="test_s_001")
    for i in range(20):
        session.mark_round(tokens_saved=1500)  # 每回合省 1500 tokens

    report = session.get_savings_report()
    assert "20" in report or "回合" in report
    print(f"✅ test_game_session_cache")
    print(report)


def test_global_singleton():
    """全局单例"""
    assert SYSTEM_PROMPT_CACHE is not None
    assert GLOBAL_STATS is not None
    print(f"✅ test_global_singleton: 全局单例存在")


if __name__ == "__main__":
    print("=" * 50)
    print("KV 缓存单元测试")
    print("=" * 50)
    test_basic_cache_hit_miss()
    test_hit_rate_calculation()
    test_real_scenario_50_rounds()
    test_get_cache_control_returns_ephemeral()
    test_estimate_savings()
    test_game_session_cache()
    test_global_singleton()
    print("\n✅ 所有 KV 缓存测试通过")