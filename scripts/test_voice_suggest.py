"""🆕 v1.7.30 折叠态"帮我一下"功能静态验证

覆盖：
1. 后端 router 存在（handle_POST_voice_options_suggest）
2. router 已注册到 POST_ROUTES（/api/voice_options/suggest）
3. prompt 强调"可执行方案"而非"情绪名"（user feedback 修正）
4. 前端 suggestVoiceOptions 函数存在 + 调 /api/voice_options/suggest
5. 触发条件：hasRealOptions=false 时显示
6. CSS：suggest 按钮 + loading 动画 + used 置灰
7. 限流：SESSION_LLM_RATE_LIMITER 存在
8. 错误降级：3 个 fallback 选项
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
ROUTER = ROOT / "src/history_footnote/web_server/routers/voice_suggest.py"
REGISTRY = ROOT / "src/history_footnote/web_server/router_registry.py"
ENH = ROOT / "src/history_footnote/web_enhancements.py"
JS = ROOT / "src/history_footnote/web/static/js/main.js"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_router_exists():
    print("[1/7] 后端 router")
    if not ROUTER.exists():
        return _step("voice_suggest.py 存在", False)
    src = ROUTER.read_text(encoding="utf-8")
    return _step(
        "  router: handle_POST_voice_options_suggest 定义",
        "def handle_POST_voice_options_suggest" in src,
    )


def test_router_registry():
    print("\n[2/7] 路由注册")
    src = REGISTRY.read_text(encoding="utf-8")
    return _step(
        "  /api/voice_options/suggest 在 POST_ROUTES",
        '"/api/voice_options/suggest"' in src,
    )


def test_prompt_user_feedback():
    """用户反馈：prompt 必须强调"可执行方案"而非"情绪名" """
    print("\n[3/7] prompt 设计（用户反馈修正）")
    src = ROUTER.read_text(encoding="utf-8")
    checks = [
        ("明确要求 voice_name 是动作（不是情绪名）", "不是情绪名" in src or "**不是**" in src),
        ("明确说 3~8 字短句", "3~8" in src or "3-8" in src),
        ("要求应急 + 治本 + 迂回覆盖", "应急" in src and "治本" in src and "迂回" in src),
        ("要求贴合万历十五年社会现实", "万历十五年" in src),
        ("要求严格 JSON 数组输出", "JSON" in src),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  {name}", ok) and all_ok
    return all_ok


def test_frontend_suggest_function():
    print("\n[4/7] 前端 suggestVoiceOptions 函数")
    src = JS.read_text(encoding="utf-8")
    checks = [
        ("suggestVoiceOptions 函数定义", "async function suggestVoiceOptions" in src),
        ("调 /api/voice_options/suggest", "/api/voice_options/suggest" in src),
        ("loading 状态切换", "loading" in src and "DM 在想" in src),
        ("成功后重渲染", "appendVoiceOptions(data.voice_options)" in src),
        ("强制展开（避免建议后立即折叠）", "window.__VOICE_PREFS__" in src),
        ("错误降级到'网络出错'", "网络出错" in src),
        ("used 状态", ".classList.add(\"used\")" in src or "'used'" in src),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  {name}", ok) and all_ok
    return all_ok


def test_trigger_condition():
    print("\n[5/7] 触发条件")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  hasRealOptions=false 时显示 suggest 按钮（语音选项 < 2）",
        "const suggestButton = hasRealOptions" in src
        and "voice-options-suggest-btn" in src,
    )


def test_css_styles():
    print("\n[6/7] CSS 样式")
    src = CSS.read_text(encoding="utf-8")
    checks = [
        (".voice-options-suggest-btn {", ".voice-options-suggest-btn {" in src),
        ("hover 反馈", ".voice-options-suggest-btn:hover" in src),
        ("active 反馈", ".voice-options-suggest-btn:active" in src),
        ("focus-visible 焦点环", ".voice-options-suggest-btn:focus-visible" in src),
        ("disabled 状态", ".voice-options-suggest-btn:disabled" in src),
        ("loading 旋转动画", "@keyframes suggest-spin" in src),
        ("used 置灰状态", ".voice-options-suggest-btn.used" in src),
        ("移动端 @media 覆盖", re.search(
            r"@media\s*\([^)]*max-width:\s*480px[^)]*\)[^{]*\{[\s\S]*?voice-options-suggest-btn",
            src,
        ) is not None),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  {name}", ok) and all_ok
    return all_ok


def test_rate_limit_and_fallback():
    print("\n[7/7] 限流 + 错误降级")
    enh = ENH.read_text(encoding="utf-8")
    router = ROUTER.read_text(encoding="utf-8")
    checks = [
        ("SESSION_LLM_RATE_LIMITER 定义", "SESSION_LLM_RATE_LIMITER" in enh),
        ("限流检查 sid:", "SESSION_LLM_RATE_LIMITER.allow(f\"sid:{sid}\")" in router),
        ("全局 LLM 限流", "LLM_RATE_LIMITER.allow(client_ip)" in router),
        ("3 个 fallback 选项", "sug_fallback_1" in router and "sug_fallback_3" in router),
        ("fallback_used 标记", "fallback_used" in router),
        ("_is_suggestion 标记", "_is_suggestion" in router),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  {name}", ok) and all_ok
    return all_ok


if __name__ == "__main__":
    print("=== v1.7.30 折叠态「帮我一下」静态验证 ===\n")
    ok1 = test_router_exists()
    ok2 = test_router_registry()
    ok3 = test_prompt_user_feedback()
    ok4 = test_frontend_suggest_function()
    ok5 = test_trigger_condition()
    ok6 = test_css_styles()
    ok7 = test_rate_limit_and_fallback()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7]):
        print("\n🎉 7 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=}")
        sys.exit(1)
