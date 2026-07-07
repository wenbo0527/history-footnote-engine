"""🆕 v1.8.2 4 板块统一菜单入口 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENU = ROOT / "src/history_footnote/web_server/routers/menu.py"
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"
ACCOUNT = ROOT / "src/history_footnote/account_system.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_create_guest():
    print("[1/5] AccountSystem.create_guest")
    src = ACCOUNT.read_text(encoding="utf-8")
    ok = True
    ok = _step("  def create_guest 存在", "def create_guest" in src) and ok
    ok = _step("  自动生成 account_id（guest_<hex>）", 'guest_"' in src or 'f"guest_{secrets' in src) and ok
    ok = _step("  role=guest", 'role="guest"' in src) and ok
    ok = _step("  幂等（已存在返回旧）", "已存在则返回" in src) and ok
    return ok


def test_menu_accepts_guest():
    print("\n[2/5] /api/menu 接受 guest")
    src = MENU.read_text(encoding="utf-8")
    ok = True
    ok = _step("  无 account_id → create_guest", "sys_inst.create_guest()" in src) and ok
    ok = _step("  找不到 account → create_guest(account_id)", "create_guest(account_id=account_id)" in src) and ok
    ok = _step("  不再 handler._json(404, ...)",
               "handler._json(404, {\"error\": \"account not found\"})" not in src) and ok
    ok = _step("  不再 handler._json(400, {\"error\": \"account_id required\"})",
               "handler._json(400, {\"error\": \"account_id required\"})" not in src) and ok
    return ok


def test_main_render_menu():
    print("\n[3/5] main.js renderMenu")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  async function renderMenu() 存在", "async function renderMenu()" in src) and ok
    ok = _step("  调 /api/menu", 'api(`/api/menu?account_id=' in src) and ok
    ok = _step("  渲染 sections（4 板块）", "menu.sections.map" in src) and ok
    ok = _step("  显示 user.username", "menu.user.username" in src) and ok
    ok = _step("  4 板块点击 menuSectionClick", "function menuSectionClick" in src) and ok
    ok = _step("  板块：new_game", "sectionId === \"new_game\"" in src) and ok
    ok = _step("  板块：saves", "sectionId === \"saves\"" in src) and ok
    ok = _step("  板块：settings", "sectionId === \"settings\"" in src) and ok
    ok = _step("  板块：admin", "sectionId === \"admin\"" in src) and ok
    return ok


def test_render_start_redirect():
    print("\n[4/5] renderStart → renderMenu")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function renderStart() 调 renderMenu()",
               "function renderStart() {" in src and "renderMenu();" in src) and ok
    return ok


def test_back_compat():
    print("\n[5/5] 向后兼容")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  renderWizard 仍存在（开始游戏用）", "function renderWizard" in src) and ok
    ok = _step("  showSavesList 仍存在（saves 板块用）", "function showSavesList" in src) and ok
    ok = _step("  showAdminPanel 仍存在（admin 板块用）", "function showAdminPanel" in src) and ok
    ok = _step("  logoutAccount 仍存在（切换账户）", "function logoutAccount" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.8.2 4 板块统一菜单入口 静态测试 ===\n")
    ok1 = test_create_guest()
    ok2 = test_menu_accepts_guest()
    ok3 = test_main_render_menu()
    ok4 = test_render_start_redirect()
    ok5 = test_back_compat()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
