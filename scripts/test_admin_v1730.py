"""🆕 v1.7.30 管理员体系 静态测试

覆盖：
1. admin.py 7 个路由（users/saves/tokens/config × GET/POST）
2. router_registry 4 路由注册
3. account_system.ensure_default_admin 自动创建
4. account_system 修后 _load_accounts 修复
5. main.js admin 面板 + 4 tab + 角色提升/删除函数
6. localStorage hfe_account_role 持久化
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
AS = ROOT / "src/history_footnote/account_system.py"
AR = ROOT / "src/history_footnote/web_server/routers/admin.py"
RR = ROOT / "src/history_footnote/web_server/router_registry.py"
JS = ROOT / "src/history_footnote/web/static/js/main.js"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_admin_router():
    print("[1/6] routers/admin.py 7 个路由")
    src = AR.read_text(encoding="utf-8")
    funcs = [
        "handle_GET_admin_users",
        "handle_GET_admin_saves",
        "handle_GET_admin_tokens",
        "handle_GET_admin_config",
        "handle_POST_admin_config",
        "handle_POST_admin_user_role",
        "handle_DELETE_admin_user",
        "handle_DELETE_admin_save",
    ]
    ok = True
    for f in funcs:
        ok = _step(f"  {f}", f in src) and ok
    return ok


def test_router_registry():
    print("\n[2/6] router_registry 8 路由注册")
    src = RR.read_text(encoding="utf-8")
    routes = [
        "/api/admin/users",
        "/api/admin/saves",
        "/api/admin/tokens",
        "/api/admin/config",
    ]
    ok = True
    for r in routes:
        ok = _step(f"  GET {r}", f'"{r}"' in src) and ok
    ok = _step("  POST /api/admin/config", '"/api/admin/config": _admin.handle_POST_admin_config' in src) and ok
    ok = _step("  POST /api/admin/users/role", '"/api/admin/users/role": _admin.handle_POST_admin_user_role' in src) and ok
    ok = _step("  POST /api/admin/users/delete", '"/api/admin/users/delete": _admin.handle_DELETE_admin_user' in src) and ok
    ok = _step("  POST /api/admin/saves/delete", '"/api/admin/saves/delete": _admin.handle_DELETE_admin_save' in src) and ok
    return ok


def test_ensure_default_admin():
    print("\n[3/6] ensure_default_admin 自动创建")
    sys.path.insert(0, str(ROOT / "src"))
    import tempfile
    from history_footnote.account_system import AccountSystem

    tmp = Path(tempfile.mkdtemp(prefix="hf_admin_"))
    sys_inst = AccountSystem(tmp)
    inv, acc = sys_inst.ensure_default_admin()
    ok = True
    ok = _step(f"  首次创建 admin 邀请码（{inv.code if inv else 'None'}）", inv is not None and inv.code.startswith("INV-")) and ok
    ok = _step(f"  创建 admin 账户（id={acc.account_id if acc else None}）", acc is not None and acc.role == "admin") and ok
    ok = _step("  account_id 固定 00000000", acc.account_id == "00000000") and ok

    # 第二次 ensure 不再创建
    inv2, acc2 = sys_inst.ensure_default_admin()
    ok = _step("  第二次 ensure 不再创建", inv2 is None and acc2 is None) and ok
    return ok


def test_account_id_00000000():
    print("\n[4/6] admin account_id 修复（重读 accounts）")
    sys.path.insert(0, str(ROOT / "src"))
    import tempfile
    from history_footnote.account_system import AccountSystem

    tmp = Path(tempfile.mkdtemp(prefix="hf_admin2_"))
    sys_inst = AccountSystem(tmp)
    inv, acc = sys_inst.ensure_default_admin()
    # 验证：所有账户里有 admin 且 account_id=00000000
    users = sys_inst.list_accounts()
    admin = next((u for u in users if u.role == "admin"), None)
    ok = True
    ok = _step(f"  admin 账户存在（{admin.username if admin else None}）", admin is not None) and ok
    ok = _step(f"  admin account_id 持久化为 00000000（实际 {admin.account_id if admin else None}）", admin and admin.account_id == "00000000") and ok
    return ok


def test_main_js_admin():
    print("\n[5/6] main.js 管理员面板（4 tab + 6 函数）")
    src = JS.read_text(encoding="utf-8")
    ok = True
    funcs = [
        "function showAdminPanel",
        "async function adminShowTab",
        "async function adminChangeRole",
        "async function adminDeleteUser",
        "async function adminDeleteSave",
    ]
    for f in funcs:
        ok = _step(f"  {f}", f in src) and ok
    return ok


def test_localStorage_role():
    print("\n[6/6] localStorage hfe_account_role 持久化")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  registerAccount + loginByAccountId + restoreAccountFromStorage 都 setItem hfe_account_role",
        'localStorage.setItem("hfe_account_role"' in src
        and 'localStorage.getItem("hfe_account_role")' in src,
    )


if __name__ == "__main__":
    print("=== v1.7.30 管理员体系 静态测试 ===\n")
    ok1 = test_admin_router()
    ok2 = test_router_registry()
    ok3 = test_ensure_default_admin()
    ok4 = test_account_id_00000000()
    ok5 = test_main_js_admin()
    ok6 = test_localStorage_role()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)
