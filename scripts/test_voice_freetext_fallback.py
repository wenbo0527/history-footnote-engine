"""🆕 v1.7.30 折叠态自由输入 fallback 验证

覆盖：
1. 折叠态下也保留 .voice-options-freetext-fallback 按钮（grid 外）
2. voiceOptions 为空时强制 effectiveCollapsed=false（不可折叠，避免死局）
3. voiceOptions 全是 freetext 时强制 effectiveCollapsed=false
4. 折叠按钮在空选项时 disabled
5. 桌面/移动端 fallback 按钮都存在
6. fallback 按钮的 onclick 调 showFreeInputTab
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
MAIN_JS = ROOT / "src/history_footnote/web/static/js/main.js"
MAIN_CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def get_fn_body(name):
    """通过花括号平衡获取函数体"""
    src = MAIN_JS.read_text(encoding="utf-8")
    lines = src.splitlines()
    fn_start = None
    for i, line in enumerate(lines):
        if line.startswith(f"function {name}"):
            fn_start = i
            break
    if fn_start is None:
        return ""
    text = "\n".join(lines[fn_start:])
    depth = 0
    started = False
    end_index = None
    in_string = None
    in_comment = None
    for i, ch in enumerate(text):
        c2 = text[i : i + 2]
        if in_string is not None:
            if ch == "\\":
                continue
            if ch == in_string:
                in_string = None
            continue
        if in_comment is not None:
            if in_comment == "//" and ch == "\n":
                in_comment = None
            elif in_comment == "/*" and c2 == "*/":
                in_comment = None
                continue
            continue
        if c2 == "//":
            in_comment = "//"
            continue
        if c2 == "/*":
            in_comment = "/*"
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            continue
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                end_index = i + 1
                break
    return text[:end_index] if end_index else ""


def test_js_freetext_fallback_always_present():
    """appendVoiceOptions 必须输出 .voice-options-freetext-fallback 按钮（grid 外）"""
    body = get_fn_body("appendVoiceOptions")
    if not body:
        return _step("找到 appendVoiceOptions", False)
    return _step(
        "  js: appendVoiceOptions 输出 voice-options-freetext-fallback class",
        'class="voice-options-freetext-fallback"' in body,
    )


def test_js_effective_collapsed_logic():
    """空 options 时强制 effectiveCollapsed=false + 折叠按钮 disabled"""
    body = get_fn_body("appendVoiceOptions")
    if not body:
        return _step("找到 appendVoiceOptions", False)
    has_real_options = (
        'const hasRealOptions' in body
        and "voiceOptions.filter(v => !v.is_freetext).length > 0" in body
    )
    has_effective_collapsed = (
        'const effectiveCollapsed' in body
        and "hasRealOptions ? initialCollapsed : false" in body
    )
    has_disabled_attr = (
        '${hasRealOptions ? "" : "disabled"}' in body
    )
    ok = True
    ok = _step("  js: hasRealOptions 计算逻辑（剔除 is_freetext）", has_real_options) and ok
    ok = _step("  js: effectiveCollapsed = hasRealOptions ? initialCollapsed : false", has_effective_collapsed) and ok
    ok = _step("  js: 无选项时折叠按钮 disabled", has_disabled_attr) and ok
    return ok


def test_js_freetext_fallback_outside_grid():
    """fallback 按钮在 .voice-options-grid 之外（grid 折叠后仍可见）"""
    body = get_fn_body("appendVoiceOptions")
    if not body:
        return _step("找到 appendVoiceOptions", False)
    # 用字符串顺序：grid 在前，freetext-fallback 在后
    grid_idx = body.find('id="voice-options-grid"')
    fallback_idx = body.find('class="voice-options-freetext-fallback"')
    return _step(
        "  js: fallback 按钮在 grid 之后（grid 外）",
        grid_idx > 0 and fallback_idx > grid_idx,
        f"grid_idx={grid_idx}, fallback_idx={fallback_idx}",
    )


def test_js_freetext_fallback_onclick():
    """fallback 按钮 onclick 调 showFreeInputTab"""
    body = get_fn_body("appendVoiceOptions")
    if not body:
        return _step("找到 appendVoiceOptions", False)
    # 提取 fallback 按钮的 onclick
    m = re.search(
        r'class="voice-options-freetext-fallback"[^>]*onclick="([^"]+)"',
        body,
    )
    if not m:
        return _step("  js: fallback 按钮存在", False)
    return _step(
        f"  js: fallback 按钮 onclick = {m.group(1)}",
        m.group(1) == "showFreeInputTab()",
    )


def test_css_freetext_fallback_minimal():
    """CSS 关键样式"""
    src = MAIN_CSS.read_text(encoding="utf-8")
    checks = [
        (".voice-options-freetext-fallback {", ".voice-options-freetext-fallback {" in src),
        ("hover 反馈", ".voice-options-freetext-fallback:hover" in src),
        ("active 反馈", ".voice-options-freetext-fallback:active" in src),
        ("focus-visible 焦点环", ".voice-options-freetext-fallback:focus-visible" in src),
        ("移动端 @media 紧凑样式",
         re.search(
             r"@media\s*\([^)]*max-width:\s*480px[^)]*\)[^{]*\{[\s\S]*?voice-options-freetext-fallback",
             src,
         ) is not None),
        ("折叠态更紧凑",
         ".voice-options-collapsed .voice-options-freetext-fallback" in src),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  css: {name}", ok) and all_ok
    return all_ok


def test_aria_consistency():
    """fallback 按钮有 aria-label 便于无障碍访问"""
    body = get_fn_body("appendVoiceOptions")
    if not body:
        return _step("找到 appendVoiceOptions", False)
    return _step(
        "  js: fallback 按钮带 aria-label",
        'aria-label="自由输入"' in body,
    )


def test_no_voice_options_special_case():
    """空 voiceOptions 时，fallback 文案要更醒目"""
    body = get_fn_body("appendVoiceOptions")
    if not body:
        return _step("找到 appendVoiceOptions", False)
    return _step(
        "  js: 空 options 时 fallbackText 提示「DM 没生成选项」",
        "DM 没生成选项——直接描述你想做什么" in body,
    )


if __name__ == "__main__":
    print("=== v1.7.30 折叠态自由输入 fallback 验证 ===\n")
    print("[1/6] JS：fallback 按钮始终存在")
    ok1 = test_js_freetext_fallback_always_present()
    print("\n[2/6] JS：空选项时强制不折叠")
    ok2 = test_js_effective_collapsed_logic()
    print("\n[3/6] JS：fallback 在 grid 外")
    ok3 = test_js_freetext_fallback_outside_grid()
    print("\n[4/6] JS：fallback onclick 调 showFreeInputTab")
    ok4 = test_js_freetext_fallback_onclick()
    print("\n[5/6] CSS：关键样式")
    ok5 = test_css_freetext_fallback_minimal()
    print("\n[6/6] ARIA + 文案")
    ok6 = test_aria_consistency() and test_no_voice_options_special_case()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
