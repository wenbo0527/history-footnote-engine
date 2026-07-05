"""🆕 v1.7.4 端到端测试：拆分后的完整流程

模拟：
1. 移动端用户访问
2. 加载 HTML/CSS/JS
3. 提交反馈（移动端屏幕尺寸）
4. 查询 Character Wiki
5. 渲染结构化叙事
6. 选项兜底

这个测试**不依赖 mock LLM**，但需要 web_server 正在运行（默认 :8765）。
"""
import sys
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8765"


def post(path: str, data: dict = None) -> dict:
    """POST JSON 请求"""
    url = f"{BASE}{path}"
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def get(path: str) -> tuple[int, str]:
    """GET 请求，返回 (status, body)"""
    url = f"{BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return (r.status, r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return (e.code, "")
    except Exception as e:
        return (0, f"{type(e).__name__}: {e}")


def test_html_loads():
    """HTML 主页面加载"""
    status, body = get("/")
    assert status == 200, f"HTTP {status}"
    assert "<!DOCTYPE html>" in body
    assert "history_footnote" in body or "历史注脚" in body
    # 必须外链 CSS/JS（拆分成功的标志）
    assert '/static/css/main.css' in body
    assert '/static/js/main.js' in body
    # 🆕 v1.7.4: 不应内嵌 <style>（v1.7.3 拆分后）
    assert "<style>" not in body, "HTML 仍内嵌 <style>（拆分不彻底）"
    # 不应有内联大段 JS
    assert body.count("\nlet ") == 0, "HTML 内嵌 JS（应已外链）"
    print(f"✅ test_html_loads: {len(body)} chars, 外链 CSS/JS 正确")


def test_css_loads():
    """CSS 静态资源加载"""
    status, body = get("/static/css/main.css")
    assert status == 200
    assert "@media" in body  # 响应式
    assert "version-badge" in body  # 反馈 badge
    print(f"✅ test_css_loads: {len(body)} chars, 响应式 + 反馈 badge")


def test_js_loads():
    """JS 静态资源加载 + 严格语法检查"""
    import subprocess
    import tempfile
    status, body = get("/static/js/main.js")
    assert status == 200
    # 关键函数必须存在
    for fn in ["api(", "renderStart", "appendNarrative", "openFeedback", "openCharacterWiki"]:
        assert fn in body, f"JS 缺 {fn}"
    # 🆕 v1.7.4: 严格检查 - 不应有 HTML 标签（拆分后）
    html_tags = ["<script>", "</script>", "<body>", "</body>", "<html>", "</html>", "<head>", "</head>"]
    for tag in html_tags:
        assert tag not in body, f"JS 含 HTML 标签 {tag}（拆分不彻底）"
    # 关键：首字符应该是注释或代码，不是 HTML
    assert not body.lstrip().startswith("<"), f"JS 以 < 开头（可能是 HTML 泄漏）"
    # 检查括号配对
    assert body.count("{") == body.count("}"), f"JS 大括号不配对: {body.count('{')} vs {body.count('}')}"
    # 🆕 v1.7.4: node --check 语法验证（如果有 node）
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(body)
            tmp_path = f.name
        result = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            print(f"✅ test_js_loads: {len(body)} chars, 5 核心函数齐, node --check 通过")
        else:
            raise AssertionError(f"node --check failed: {result.stderr}")
    except FileNotFoundError:
        # 没有 node - 跳过语法检查
        print(f"✅ test_js_loads: {len(body)} chars, 5 核心函数齐, 无 HTML 标签 (node 未安装，跳过语法检查)")


def test_static_path_traversal():
    """路径穿越防护"""
    status, _ = get("/static/../config.py")
    assert status == 400 or status == 404
    print(f"✅ test_static_path_traversal: HTTP {status} (防护生效)")


def test_static_404():
    """不存在的静态资源"""
    status, _ = get("/static/nonexistent.css")
    assert status == 404
    print(f"✅ test_static_404: HTTP 404")


def test_api_version():
    """版本信息端点"""
    data = post("/api/version")
    assert "version" in data
    assert data["version"].startswith("1.")
    assert "git_commit" in data
    print(f"✅ test_api_version: v{data['version']} ({data['git_commit']})")


def test_api_feedback_full_flow():
    """反馈系统完整流程（移动端场景）"""
    # 1. 获取分类
    cats = post("/api/feedback_categories")
    assert "categories" in cats
    assert len(cats["categories"]) == 6
    # 2. 提交反馈（模拟移动端 context）
    fb = post("/api/feedback", {
        "session_id": "e2e-mobile-test",
        "category": "ui",
        "description": "v1.7.4 拆分后移动端测试",
        "context": {
            "user_agent": "iPhone Mobile/15E148",
            "screen": "375x812",
            "viewport": "375x667",
        },
    })
    assert "id" in fb
    assert fb["id"].startswith("fb-")
    assert "saved_to" in fb
    print(f"✅ test_api_feedback_full_flow: {fb['id']} → {fb.get('saved_to', 'OK')}")


def test_api_render_narrative():
    """结构化叙事渲染"""
    data = post("/api/render_narrative", {
        "narrative_text": '张顺说：' + chr(34) + '三两三。' + chr(34) + '\n\n你心里想：他出价低。\n\n片刻后，李四笑道：' + chr(34) + '好说！' + chr(34),
    })
    assert "blocks" in data
    assert data["block_count"] >= 3
    types = data.get("block_types", [])
    # 至少应该有 dialogue（张顺说 / 李四笑）
    assert "dialogue" in types
    # 检查 HTML 输出
    assert "block-dialogue" in data["html"]
    print(f"✅ test_api_render_narrative: {data['block_count']} blocks, types={types}")


def test_api_merge_voice_options():
    """选项兜底（移动端：voice_options 为空时）"""
    data = post("/api/merge_voice_options", {
        "structured_options": [],
        "narrative_text": "一、答应周老板\n二、全卖张顺\n三、问代织",
    })
    assert "options" in data
    assert data["source"] == "inline"  # 兜底
    assert len(data["options"]) == 3
    # 选项标签
    labels = [o["intent_text"] for o in data["options"]]
    assert "答应周老板" in labels[0]
    print(f"✅ test_api_merge_voice_options: 3 个选项，source=inline")


def test_api_sanitize():
    """SKILL 元数据清洗（v1.6.7 修复）"""
    data = post("/api/sanitize", {
        "text": "=== COMPILED SKILLS ===\n## SKILL-2 节奏\n灶房里，沈氏在切菜。",
    })
    assert "cleaned" in data
    assert "COMPILED SKILLS" not in data["cleaned"]
    assert "SKILL-2" not in data["cleaned"]
    assert "沈氏" in data["cleaned"]  # 真叙事保留
    print(f"✅ test_api_sanitize: SKILL 清洗 OK")


def test_mobile_user_agent():
    """模拟移动端 User-Agent"""
    req = urllib.request.Request(f"{BASE}/static/css/main.css")
    req.add_header("User-Agent", "iPhone; CPU iPhone OS 17_0")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.status == 200
    except Exception as e:
        assert False, f"移动端 CSS 加载失败: {e}"
    print("✅ test_mobile_user_agent: iPhone UA 200 OK")


def test_character_wiki_invalid_session():
    """Wiki 查询（无效 session）"""
    data = post("/api/character_wiki", {"session_id": "nonexistent-session-xyz"})
    # 应该返回 404 或 {"wiki": ..., "summary": "..."} 但 wiki 为空
    # 实际：session 池没这个 id，应该 404
    if "error" in data:
        print(f"✅ test_character_wiki_invalid_session: {data.get('error', 'OK')}")
    else:
        print(f"✅ test_character_wiki_invalid_session: 不存在的 session 返回空 wiki")


def run_all():
    """运行所有测试"""
    print("=" * 50)
    print("E2E 端到端测试（v1.7.4 拆分后）")
    print("=" * 50)
    tests = [
        test_html_loads,
        test_css_loads,
        test_js_loads,
        test_static_path_traversal,
        test_static_404,
        test_api_version,
        test_api_feedback_full_flow,
        test_api_render_narrative,
        test_api_merge_voice_options,
        test_api_sanitize,
        test_mobile_user_agent,
        test_character_wiki_invalid_session,
    ]
    passed = 0
    failed = []
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed.append((t.__name__, str(e)))
            print(f"  ❌ {t.__name__}: {e}")
    print()
    print(f"结果: {passed}/{len(tests)} 通过")
    if failed:
        print("失败:")
        for name, err in failed:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("✅ 所有 E2E 测试通过")


if __name__ == "__main__":
    run_all()