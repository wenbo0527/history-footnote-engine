"""🆕 v1.8.3 UX 核心工具 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_spinner():
    print("[1/6] spinner 全局")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function showSpinner 存在", "function showSpinner" in src) and ok
    ok = _step("  function hideSpinner 存在", "function hideSpinner" in src) and ok
    ok = _step("  注入 hfe-spin keyframes", "hfe-spin-keyframes" in src) and ok
    ok = _step("  全屏遮罩 z-index 99999", "z-index:99999" in src) and ok
    return ok


def test_toast():
    print("\n[2/6] toast 通知")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function showToast 存在", "function showToast" in src) and ok
    ok = _step("  4 种类型：success/error/warning/info", all(t in src for t in ["success", "error", "warning", "info"])) and ok
    ok = _step("  容器 #hfe-toast-container", "hfe-toast-container" in src) and ok
    ok = _step("  自动移除 setTimeout", "setTimeout" in src) and ok
    ok = _step("  注入 hfe-toast-in keyframes", "hfe-toast-in" in src) and ok
    return ok


def test_haptic():
    print("\n[3/6] 触觉反馈")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function haptic 存在", "function haptic" in src) and ok
    ok = _step("  navigator.vibrate 调用", "navigator.vibrate" in src) and ok
    ok = _step("  const HAPTIC 预设", "const HAPTIC" in src) and ok
    ok = _step("  4 预设：tap/success/error/warning", all(k in src for k in ["tap:", "success:", "error:", "warning:"])) and ok
    ok = _step("  menuSectionClick 用 HAPTIC.tap", "menuSectionClick(sectionId)" in src and "HAPTIC.tap()" in src) and ok
    return ok


def test_empty_state():
    print("\n[4/6] 空状态")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function renderEmptyState 存在", "function renderEmptyState" in src) and ok
    ok = _step("  5 预设：no_saves/no_archives/error/network/loading", all(p in src for p in ["no_saves", "no_archives", "error", "network", "loading"])) and ok
    ok = _step("  showSavesList 用 renderEmptyState", "renderEmptyState(\"no_saves\")" in src) and ok
    return ok


def test_button_loading():
    print("\n[5/6] 按钮 loading 状态")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function setButtonLoading 存在", "function setButtonLoading" in src) and ok
    ok = _step("  function withLoading 存在", "function withLoading" in src) and ok
    ok = _step("  showSavesList 用 withLoading", "withLoading(\"加载存档" in src) and ok
    return ok


def test_toast_replace_alert():
    print("\n[6/6] 替代 alert/confirm")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    # 找 showSavesList 是否仍用 alert
    has_old_alert = "alert(data.error)" in src or "alert(\"网络错误" in src
    ok = _step("  showSavesList 不再用 alert", not has_old_alert) and ok
    ok = _step("  showSavesList 用 showToast", "showToast(data.error" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.8.3 UX 核心工具 静态测试 ===\n")
    ok1 = test_spinner()
    ok2 = test_toast()
    ok3 = test_haptic()
    ok4 = test_empty_state()
    ok5 = test_button_loading()
    ok6 = test_toast_replace_alert()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
