"""🆕 v2.9.x W44: 性能监控 MetricsCollector 测试

测试目标：
1. record_request 含 latency list + P50/P95/P99
2. record_llm_call 按 provider 分组 + token 累加
3. _percentile 正确（边界 + 中间）
4. snapshot 含 endpoints + llm 字段
5. memory 限制（>1000 latencies 自动截断）
6. reset 清理
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W44_001_record_request_keeps_latencies():
    """record_request 保留 latency 列表"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    m.record_request("/api/test", 100.0)
    m.record_request("/api/test", 200.0)
    m.record_request("/api/test", 300.0)
    snap = m.snapshot()
    ep = snap["endpoints"]["/api/test"]
    assert ep["count"] == 3
    assert ep["avg_ms"] == 200.0
    return True


def test_W44_002_p50_p95_p99_correct():
    """P50/P95/P99 百分位正确"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    # 100 个延迟：1, 2, 3, ..., 100
    for i in range(1, 101):
        m.record_request("/api/p", float(i))
    snap = m.snapshot()
    ep = snap["endpoints"]["/api/p"]
    # P50 = 第 50 个 = 50.0
    assert 49 <= ep["p50_ms"] <= 51, f"P50 应 ~50，实际 {ep['p50_ms']}"
    # P95 = 第 95 个 = 95.0
    assert 94 <= ep["p95_ms"] <= 96, f"P95 应 ~95，实际 {ep['p95_ms']}"
    # P99 = 第 99 个 = 99.0
    assert 98 <= ep["p99_ms"] <= 100, f"P99 应 ~99，实际 {ep['p99_ms']}"
    return True


def test_W44_003_percentile_helper():
    """_percentile 静态方法正确（线性插值 Numpy 风格）"""
    from history_footnote.web_enhancements import MetricsCollector
    # 空列表
    assert MetricsCollector._percentile([], 0.5) == 0.0
    # 1 个值
    assert MetricsCollector._percentile([100], 0.5) == 100
    # 边界 P0/P100
    vals = list(range(1, 11))  # 1..10
    assert MetricsCollector._percentile(vals, 0.0) == 1.0
    assert MetricsCollector._percentile(vals, 1.0) == 10.0
    # P50 用线性插值：(5+6)/2 = 5.5
    assert MetricsCollector._percentile(vals, 0.5) == 5.5
    # P90 线性插值：pos=9*0.9=8.1, lower=8 (val=9), weight=0.1 → 9*0.9 + 10*0.1 = 9.1
    assert abs(MetricsCollector._percentile(vals, 0.9) - 9.1) < 0.01
    return True


def test_W44_004_record_llm_call_groups_by_provider():
    """record_llm_call 按 provider 分组"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    m.record_llm_call("openai", 500, 1000, 200)
    m.record_llm_call("openai", 700, 1500, 300)
    m.record_llm_call("anthropic", 600, 1200, 250)
    snap = m.snapshot()
    assert "openai" in snap["llm"]
    assert "anthropic" in snap["llm"]
    # openai: 2 calls, 2500 prompt, 500 completion
    assert snap["llm"]["openai"]["count"] == 2
    assert snap["llm"]["openai"]["total_prompt_tokens"] == 2500
    assert snap["llm"]["openai"]["total_completion_tokens"] == 500
    # anthropic: 1 call
    assert snap["llm"]["anthropic"]["count"] == 1
    return True


def test_W44_005_llm_avg_tokens_correct():
    """LLM 平均 token 正确"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    m.record_llm_call("deepseek", 1000, 2000, 400)  # 2000/400
    m.record_llm_call("deepseek", 2000, 4000, 800)  # 4000/800
    snap = m.snapshot()
    ds = snap["llm"]["deepseek"]
    assert ds["avg_prompt_tokens"] == 3000  # (2000+4000)/2
    assert ds["avg_completion_tokens"] == 600  # (400+800)/2
    assert ds["avg_latency_ms"] == 1500  # (1000+2000)/2
    return True


def test_W44_006_llm_p50_p95():
    """LLM P50/P95 正确"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    for i in range(1, 21):  # 20 latencies: 1..20
        m.record_llm_call("mock", float(i * 100), 100, 50)
    snap = m.snapshot()
    llm = snap["llm"]["mock"]
    # P50 = 1000ms (中位数)
    assert 900 <= llm["p50_latency_ms"] <= 1100
    # P95 = 1900ms
    assert 1800 <= llm["p95_latency_ms"] <= 2000
    return True


def test_W44_007_latency_memory_limit():
    """latency 列表超过 1000 自动截断（防内存爆炸）"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    # 记录 1500 次
    for i in range(1500):
        m.record_request("/api/x", float(i))
    snap = m.snapshot()
    ep = snap["endpoints"]["/api/x"]
    # count 应是 1500（全部累加）
    assert ep["count"] == 1500
    # avg_ms 仍按 1500 计算
    assert ep["avg_ms"] > 0
    # latencies list 应被截断到 1000
    assert len(m._endpoints["/api/x"]["latencies"]) == 1000
    return True


def test_W44_008_llm_latency_memory_limit():
    """LLM latency 同样有 1000 截断"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    for i in range(1200):
        m.record_llm_call("openai", float(i), 10, 5)
    snap = m.snapshot()
    llm = snap["llm"]["openai"]
    assert llm["count"] == 1200  # count 累加
    assert len(m._llm["openai"]["latencies"]) == 1000  # latencies 截断
    return True


def test_W44_009_snapshot_has_llm_field():
    """snapshot 含 llm 字段"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    snap = m.snapshot()
    assert "llm" in snap
    assert "endpoints" in snap
    assert "uptime_seconds" in snap
    return True


def test_W44_010_reset_clears_endpoints():
    """reset 清理 endpoints + uptime 重置"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    m.record_request("/api/x", 100.0)
    m.reset()
    snap = m.snapshot()
    # endpoints 已被清空
    assert "/api/x" not in snap["endpoints"]
    return True


def test_W44_011_no_llm_calls_yet_empty():
    """未调 LLM 时 llm 字段为空 dict"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    snap = m.snapshot()
    assert snap["llm"] == {}
    return True


def test_W44_012_error_rate_correct():
    """error_rate 正确（含 error 标记）"""
    from history_footnote.web_enhancements import MetricsCollector
    m = MetricsCollector()
    m.record_request("/api/x", 100, error=False)
    m.record_request("/api/x", 200, error=False)
    m.record_request("/api/x", 300, error=True)
    m.record_request("/api/x", 400, error=True)
    snap = m.snapshot()
    ep = snap["endpoints"]["/api/x"]
    assert ep["count"] == 4
    assert ep["errors"] == 2
    assert ep["error_rate"] == 0.5
    return True
