"""🆕 v1.7.29 移动端折叠原型静态验证

不依赖 jsdom/node — 通过解析 main.js/main.css 字符串验证逻辑正确性：
1. 默认折叠逻辑（matchMedia + 默认折叠）
2. localStorage 持久化 key
3. 新回合脉冲 hook
4. CSS 折叠态 + 脉冲动画 + 移动端专属样式
5. ARIA aria-controls 与 grid id 一致

跑法：
    python3 scripts/test_voice_options_collapse.py
"""
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parent.parent
MAIN_JS = _ROOT / "src/history_footnote/web/static/js/main.js"
MAIN_CSS = _ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def get_append_fn_body() -> str:
    """通过 AST 解析获取 appendVoiceOptions 函数体。

    用 Python ast 解析 JS 不可行，直接手写简易花括号匹配。
    """
    src = MAIN_JS.read_text(encoding="utf-8")
    lines = src.splitlines()
    fn_start = None
    for i, line in enumerate(lines):
        if line.startswith("function appendVoiceOptions"):
            fn_start = i
            break
    if fn_start is None:
        return ""
    # 从 fn_start 起，扫描整文件，每 `}`-1，嵌套平衡结束
    text = "\n".join(lines[fn_start:])
    depth = 0
    started = False
    end_index = None
    in_string = None  # None | "'" | '"' | '`'
    in_comment = None  # None | "//" | "/*"
    for i, ch in enumerate(text):
        c2 = text[i : i + 2]
        if in_string is not None:
            if ch == "\\":
                continue
            if in_string == "`" and c2 == "${":
                # template literal expr: skip '{'
                # 让后续 brace counter 处理
                continue
            if ch == in_string:
                in_string = None
            continue
        if in_comment is not None:
            if in_comment == "//" and ch == "\n":
                in_comment = None
            elif in_comment == "/*" and c2 == "*/":
                in_comment = None
                continue  # skip the '*/'
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
                end_index = i + 1  # 包含这个 }
                break
    if end_index is None:
        return ""
    return text[:end_index] + "\n"


def test_js_mobile_default_collapsed():
    fn_body = get_append_fn_body()
    if not fn_body:
        return _step("解析 appendVoiceOptions 函数", False, "未找到")
    checks = [
        ("PREF_KEY 常量", "hfe_voice_options_collapsed" in fn_body),
        ("localStorage 读取", "localStorage.getItem" in fn_body),
        ("localStorage 写入", "localStorage.setItem" in fn_body),
        ("移动端默认折叠", "isMobile" in fn_body),
        ("toggle 点击事件", "voice-options-toggle" in fn_body and "addEventListener" in fn_body),
        ("新回合脉冲 class 触发", "voice-options-new-round" in fn_body),
        ("保存偏好函数", "savePref" in fn_body),
        ("ARIA 属性 aria-expanded", "aria-expanded" in fn_body),
        ("当前回合标签", "voice-options-round-tag" in fn_body),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  js: {name}", ok) and all_ok
    return all_ok


def test_css_min_styles():
    src = MAIN_CSS.read_text(encoding="utf-8")
    checks = [
        (".voice-options-toggle {", ".voice-options-toggle {" in src),
        (".voice-options-grid.collapsed", ".voice-options-grid.collapsed" in src),
        (".voice-options-round-tag", ".voice-options-round-tag {" in src),
        ("@keyframes voice-pulse", "@keyframes voice-pulse" in src),
        (".voice-options-new-round", ".voice-options-new-round" in src),
        ("@media (max-width: 480px) 紧凑",
         re.search(r"@media\s*\([^)]*max-width:\s*480px[^)]*\)[^{]*\{[\s\S]*?voice-options-collapsed", src) is not None),
        ("hover 反馈", ".voice-options-toggle:hover" in src),
        ("ARIA focus-visible", ".voice-options-toggle:focus-visible" in src),
        ("网格过渡 transition", "transition" in src),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  css: {name}", ok) and all_ok
    return all_ok


def test_aria_consistency():
    """aria-controls 与 grid id 一致：'voice-options-grid'"""
    fn_body = get_append_fn_body()
    has_aria_controls = 'aria-controls="voice-options-grid"' in fn_body
    has_grid_id = 'id="voice-options-grid"' in fn_body
    return _step("  js: aria-controls 与 grid id 一致", has_aria_controls and has_grid_id)


def test_localstorage_key_uniqueness():
    """localStorage key 出现 1 次（仅在 PREF_KEY 常量定义；set/getItem 用变量引用）"""
    fn_body = get_append_fn_body()
    count = fn_body.count("hfe_voice_options_collapsed")
    # 应该 1 次：const PREF_KEY = "..." 定义
    # 用变量引用 PREF_KEY 是正确做法
    return _step(
        "  js: localStorage key 仅在 PREF_KEY 中定义 1 次",
        count == 1,
        f"实际 {count} 次"
    )


def test_remove_prefs_after_pulse():
    fn_body = get_append_fn_body()
    has_set_timeout_remove = re.search(
        r"setTimeout\(\s*\(\)\s*=>\s*div\.classList\.remove\(\"voice-options-new-round\"\),\s*1000",
        fn_body,
    )
    return _step(
        "  js: 脉冲后 1s 移除 class",
        has_set_timeout_remove is not None,
    )


if __name__ == "__main__":
    print("=== v1.7.29 voice 选项移动端折叠静态验证 ===\n")
    print("[1/5] JS 折叠逻辑")
    ok1 = test_js_mobile_default_collapsed()
    print("\n[2/5] CSS 关键样式")
    ok2 = test_css_min_styles()
    print("\n[3/5] ARIA 一致性")
    ok3 = test_aria_consistency()
    print("\n[4/5] localStorage key 唯一")
    ok4 = test_localstorage_key_uniqueness()
    print("\n[5/5] 脉冲一次性清理")
    ok5 = test_remove_prefs_after_pulse()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：JS=({ok1},{ok3},{ok4},{ok5}) CSS={ok2}")
        sys.exit(1)
