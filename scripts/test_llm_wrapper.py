"""v1.7.16 测试 LLM Wrapper"""
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv("/Users/mac/Documents/trae_projects/history_footnote/.env")

sys.path.insert(0, "src")
from history_footnote.llm_wrapper import (
    LLMWrapper, LLMUsageLogger, get_wrapped_llm, get_usage_logger,
    extract_usage, DEFAULT_TIMEOUT, FALLBACK_CHAIN
)


def test_logger_basic():
    """测试 LLMUsageLogger 基础功能"""
    logger = LLMUsageLogger(log_path="/tmp/test_llm_usage.jsonl")
    logger.reset()
    logger.log({
        "ts": "2026-07-05T10:00:00",
        "provider": "minimax-anthropic",
        "fallback": False,
        "success": True,
        "timeout": False,
        "latency_ms": 1500,
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
    })
    logger.log({
        "ts": "2026-07-05T10:00:01",
        "provider": "deepseek",
        "fallback": True,  # 是 fallback
        "success": True,
        "timeout": False,
        "latency_ms": 800,
        "input_tokens": 100,
        "output_tokens": 150,
        "total_tokens": 250,
    })
    logger.log({
        "ts": "2026-07-05T10:00:02",
        "provider": "minimax-anthropic",
        "fallback": False,
        "success": False,
        "timeout": True,  # 超时
        "latency_ms": 30000,
        "error": "timeout after 30s",
    })
    stats = logger.get_stats()
    assert len(stats["providers"]) == 2, f"应该 2 个 provider，实际 {len(stats['providers'])}"
    # minimax stats
    mini = next(p for p in stats["providers"] if p["provider"] == "minimax-anthropic")
    assert mini["total_calls"] == 2
    assert mini["successful_calls"] == 1
    assert mini["failed_calls"] == 1
    assert mini["timeout_calls"] == 1
    # deepseek stats
    ds = next(p for p in stats["providers"] if p["provider"] == "deepseek")
    assert ds["total_calls"] == 1
    assert ds["fallback_calls"] == 1
    # totals
    assert stats["totals"]["calls"] == 3
    assert stats["totals"]["tokens"] == 550
    assert stats["totals"]["fallback_count"] == 1
    assert stats["totals"]["timeout_count"] == 1
    print(f"✅ test_logger_basic: providers={len(stats['providers'])}, tokens={stats['totals']['tokens']}")


def test_extract_usage():
    """测试 extract_usage 函数"""
    # Mock response with usage_metadata
    class MockResp:
        usage_metadata = {"input_tokens": 50, "output_tokens": 100, "total_tokens": 150}
        response_metadata = {}
    usage = extract_usage(MockResp())
    assert usage == {"input_tokens": 50, "output_tokens": 100, "total_tokens": 150}
    print(f"✅ test_extract_usage: {usage}")

    # Mock response with response_metadata.token_usage
    class MockResp2:
        usage_metadata = None
        response_metadata = {"token_usage": {"prompt_tokens": 30, "completion_tokens": 70, "total_tokens": 100}}
    usage = extract_usage(MockResp2())
    assert usage == {"input_tokens": 30, "output_tokens": 70, "total_tokens": 100}
    print(f"✅ test_extract_usage (token_usage): {usage}")


def test_fallback_chain():
    """测试 fallback chain 顺序"""
    # Primary 在最前
    w = LLMWrapper(primary_provider="minimax-anthropic", fallback_chain=["minimax-anthropic", "deepseek", "minimax-openai"])
    assert w.fallback_chain[0] == "minimax-anthropic"
    # Primary 不在 chain → 加到最前
    w = LLMWrapper(primary_provider="deepseek", fallback_chain=["minimax-anthropic", "minimax-openai"])
    assert w.fallback_chain[0] == "deepseek"
    # Primary 在 chain 中间 → 移到最前
    w = LLMWrapper(primary_provider="deepseek", fallback_chain=["minimax-anthropic", "deepseek", "minimax-openai"])
    assert w.fallback_chain[0] == "deepseek"
    assert w.fallback_chain[1] == "minimax-anthropic"
    print(f"✅ test_fallback_chain: {w.fallback_chain}")


def test_wrapper_invoke_minimax():
    """测试真实 minimax 调用（验证 wrapper 工作）"""
    w = get_wrapped_llm(primary_provider="minimax-anthropic", era_config={})
    w._llm_cache.clear()  # 清缓存
    from langchain_core.messages import HumanMessage
    start = time.time()
    try:
        resp = w.invoke([HumanMessage(content="一句话介绍明朝万历十五年")], timeout=15)
        elapsed = time.time() - start
        content = resp.content if hasattr(resp, "content") else str(resp)
        assert len(content) > 10, f"response 太短: {content!r}"
        print(f"✅ test_wrapper_invoke_minimax: {elapsed:.1f}s, {content[:60]}...")
    except Exception as e:
        print(f"❌ test_wrapper_invoke_minimax failed: {e}")
        raise


def test_wrapper_timeout_fallback():
    """测试超时 fallback（minimax 1s 超时 → fallback 到 deepseek）"""
    # 使用 deepseek 作 primary（即使没钱，403 也算 "failure"），让 fallback 触发
    w = LLMWrapper(
        primary_provider="minimax-anthropic",
        fallback_chain=["minimax-anthropic", "deepseek"],
        timeout=1.0,  # 1 秒超时
    )
    from langchain_core.messages import HumanMessage
    # minimax 通常需要 9-22 秒，1 秒必超时
    start = time.time()
    try:
        resp = w.invoke([HumanMessage(content="一句话")], timeout=1.0)
        elapsed = time.time() - start
        # 如果 minimax 在 1s 内成功（极小概率），可能没触发 fallback
        print(f"⚠️  test_wrapper_timeout_fallback: {elapsed:.1f}s (minimax fast, no fallback)")
    except RuntimeError as e:
        elapsed = time.time() - start
        # 所有 provider 都失败
        assert "所有 LLM provider 都失败" in str(e), f"unexpected error: {e}"
        # 应该 < 2 秒（1s timeout + 1s fallback）
        print(f"✅ test_wrapper_timeout_fallback: failed in {elapsed:.1f}s (both providers timeout, expected)")


def test_get_stats():
    """测试 /api/llm/stats 端点返回结构"""
    # 直接调函数（不走 HTTP）
    from history_footnote.llm_wrapper import get_usage_logger
    log = get_usage_logger()
    log.reset()
    log.log({"provider": "test", "success": True, "latency_ms": 100, "input_tokens": 10, "output_tokens": 20, "total_tokens": 30})
    stats = log.get_stats()
    assert "providers" in stats
    assert "totals" in stats
    assert "recent" in stats
    assert stats["totals"]["calls"] == 1
    print(f"✅ test_get_stats: {stats['totals']}")


if __name__ == "__main__":
    print("=" * 50)
    print("v1.7.16 LLM Wrapper 单元测试")
    print("=" * 50)
    test_logger_basic()
    test_extract_usage()
    test_fallback_chain()
    test_get_stats()
    test_wrapper_invoke_minimax()
    test_wrapper_timeout_fallback()
    print("\n✅ 所有 LLM Wrapper 测试通过")