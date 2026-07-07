"""🆕 v1.8.3 admin 移动端 + 暗色模式 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_admin_tabs_class():
    print("[1/5] admin 面板 class")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  .admin-tabs class 存在", "class=\"admin-tabs\"" in src) and ok
    ok = _step("  4 个 admin-tab-btn", src.count("class=\"admin-tab-btn\"") >= 4) and ok
    return ok


def test_admin_mobile_css():
    print("\n[2/5] admin 移动端 CSS")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  .admin-tabs 768px 改 grid", ".admin-tabs" in src and "grid-template-columns: 1fr 1fr" in src) and ok
    ok = _step("  .admin-tab-btn 大触摸区", "min-height: 48px" in src) and ok
    ok = _step("  380px 改 1 列", "max-width: 380px" in src) and ok
    ok = _step("  archive-item flex-wrap", "flex-wrap" in src) and ok
    return ok


def test_form_modal_mobile():
    print("\n[3/5] form modal 移动端 full screen")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  .form-modal-overlay 768px 全屏", "form-modal-overlay" in src and "max-width: 100vw" in src) and ok
    ok = _step("  100dvh 适配 iOS Safari", "100dvh" in src) and ok
    ok = _step("  sticky header", "position: sticky" in src) and ok
    # main.js 加 class
    main = MAIN.read_text(encoding="utf-8")
    ok = _step("  modal.className = form-modal-overlay", 'modal.className = "form-modal-overlay"' in main) and ok
    return ok


def test_dark_mode():
    print("\n[4/5] 暗色模式")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  @media prefers-color-scheme: dark", "prefers-color-scheme: dark" in src) and ok
    ok = _step("  body 暗背景 #1a1410", "#1a1410" in src) and ok
    ok = _step("  text 暗前景 #f5e6c8", "#f5e6c8" in src) and ok
    ok = _step("  card 暗背景 #2a201a", "#2a201a" in src) and ok
    ok = _step("  主按钮暗色适配", "background: #d4a574" in src) and ok
    return ok


def test_backward_compat():
    print("\n[5/5] 向后兼容")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  桌面端 admin-tabs 仍 flex", "display:flex;gap:8px;margin:16px 0;flex-wrap:wrap" in src or "display: flex" in src) and ok
    ok = _step("  桌面端 form-modal 仍居中", "min-width:380px" in MAIN.read_text(encoding="utf-8")) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.8.3 admin 移动端 + 暗色模式 静态测试 ===\n")
    ok1 = test_admin_tabs_class()
    ok2 = test_admin_mobile_css()
    ok3 = test_form_modal_mobile()
    ok4 = test_dark_mode()
    ok5 = test_backward_compat()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
