"""🆕 v1.7.23 API 字段名一致性测试

验证所有端点的响应字段名符合 docs/api/FIELD_REGISTRY.md 规范
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8765"


def call(method, path, data=None, timeout=30):
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(f"{BASE}{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def test_start_response():
    """POST /api/start 响应字段"""
    code, r = call("POST", "/api/start", {
        "era_id": "wanli1587", "identity": "农妇",
        "gender": "女", "hometown": "徽州",
    })
    assert code == 200, f"start failed: {code}"
    # 必含字段
    for f in ("session_id", "era_id", "round_number", "current_date",
              "action_points_current", "action_points_max",
              "last_voice_options", "recent_narratives"):
        assert f in r, f"start response missing {f}"
    assert isinstance(r["last_voice_options"], list), "last_voice_options must be list"
    assert isinstance(r["recent_narratives"], list), "recent_narratives must be list"
    assert len(r["recent_narratives"]) >= 1, "must have opening narrative"
    # recent_narratives[0] 字段
    n = r["recent_narratives"][0]
    for f in ("round", "summary", "narrative"):
        assert f in n, f"recent_narratives[0] missing {f}"
    print(f"  ✅ /api/start 字段: {sorted(r.keys())[:8]}...")


def test_input_response():
    """POST /api/input 响应字段"""
    code, start = call("POST", "/api/start", {
        "era_id": "wanli1587", "identity": "农妇", "gender": "女", "hometown": "徽州",
    })
    sid = start["session_id"]
    code, r = call("POST", "/api/input", {
        "session_id": sid, "input": "我先扫一眼家里有什么",
    })
    assert code == 200, f"input failed: {code}"
    for f in ("session_id", "round_number", "current_date",
              "last_voice_options", "recent_narratives"):
        assert f in r, f"input response missing {f}"
    # round_number 是 int
    assert isinstance(r["round_number"], int), "round_number must be int"
    print(f"  ✅ /api/input 字段: {sorted(r.keys())[:8]}...")


def test_archives_response():
    """GET /api/archives 响应字段"""
    code, r = call("GET", "/api/archives")
    assert code == 200, f"archives failed: {code}"
    # ✅ v1.7.23: 字段是 archives (list)，不是 sessions (dict)
    assert "archives" in r, "must have 'archives' field"
    assert isinstance(r["archives"], list), "'archives' must be list"
    assert "sessions" not in r, "'sessions' is deprecated (v1.7.23+)"
    print(f"  ✅ /api/archives 字段: archives=list[{len(r['archives'])}]")


def test_recap_response():
    """POST /api/recap 响应字段"""
    code, start = call("POST", "/api/start", {
        "era_id": "wanli1587", "identity": "农妇", "gender": "女", "hometown": "徽州",
    })
    sid = start["session_id"]
    code, r = call("POST", "/api/recap", {"session_id": sid, "recent_count": 5})
    assert code == 200, f"recap failed: {code}"
    # ✅ v1.7.23: 字段是 recent (list)，不是 narratives
    for f in ("round_number", "current_date", "recent", "archive"):
        assert f in r, f"recap response missing {f}"
    assert isinstance(r["recent"], list), "recent must be list"
    print(f"  ✅ /api/recap 字段: round_number/date/recent/archive")


def test_merge_voice_options_response():
    """POST /api/merge_voice_options 响应字段"""
    code, r = call("POST", "/api/merge_voice_options", {
        "structured_options": [],
        "narrative_text": "你打算：一、去牙行\n二、回家\n三、再想",
    })
    assert code == 200, f"merge failed: {code}"
    # ✅ v1.7.23: 字段是 options (list)，不是 merged
    assert "options" in r, "must have 'options' field"
    assert "merged" not in r, "'merged' is deprecated (v1.7.23+)"
    assert isinstance(r["options"], list), "'options' must be list"
    print(f"  ✅ /api/merge_voice_options 字段: options=list[{len(r['options'])}]")


def test_sanitize_response():
    """POST /api/sanitize 响应字段"""
    code, r = call("POST", "/api/sanitize", {"text": "<zh>思考</zh>这是正文"})
    assert code == 200, f"sanitize failed: {code}"
    assert "cleaned" in r, "must have 'cleaned' field"
    print(f"  ✅ /api/sanitize 字段: cleaned (len={len(r['cleaned'])})")


def test_llm_stats_response():
    """GET /api/llm/stats 响应字段"""
    code, r = call("GET", "/api/llm/stats")
    assert code == 200, f"stats failed: {code}"
    for f in ("providers", "totals"):
        assert f in r, f"stats missing {f}"
    assert isinstance(r["totals"], dict), "totals must be dict"
    print(f"  ✅ /api/llm/stats 字段: providers/totals")


def test_error_response_format():
    """错误响应包含 error 字段"""
    # 404 端点
    code, r = call("POST", "/api/nonexistent_endpoint")
    assert code in (404, 405), f"expected 404/405, got {code}"
    assert "error" in r, f"error response missing 'error' field: {r}"
    print(f"  ✅ 错误响应: {r.get('error')}")


def main():
    print("=" * 60)
    print("v1.7.23 API 字段名一致性测试")
    print("=" * 60)
    try:
        test_start_response()
        test_input_response()
        test_archives_response()
        test_recap_response()
        test_merge_voice_options_response()
        test_sanitize_response()
        test_llm_stats_response()
        test_error_response_format()
    except AssertionError as e:
        print(f"\n❌ 失败: {e}", file=sys.stderr)
        sys.exit(1)
    print("\n✅ 全部字段名符合规范（v1.7.23）")


if __name__ == "__main__":
    main()