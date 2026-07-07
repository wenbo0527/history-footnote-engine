"""🆕 v1.8.0 main.js admin 登录 form 静态测试"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_admin_login_form():
    print("[1/5] adminLoginForm 函数（form modal）")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function adminLoginForm() 存在", "function adminLoginForm()" in src) and ok
    ok = _step("  form modal HTML（account_id + password input）",
               "hfe-admin-input-account" in src and "hfe-admin-input-password" in src) and ok
    ok = _step("  错误显示 div", 'hfe-admin-login-error' in src) and ok
    ok = _step("  取消/登录 按钮", 'hfe-admin-login-cancel' in src and 'hfe-admin-login-submit' in src) and ok
    ok = _step("  5 次错锁定提示", '5 次错将锁定 15 分钟' in src) and ok
    return ok


def test_admin_login_form_submit():
    print("\n[2/5] form submit 调 /api/admin/login")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  fetch POST /api/admin/login", 'fetch("/api/admin/login"' in src) and ok
    ok = _step("  credentials: include（带 cookie）", 'credentials: "include"' in src) and ok
    ok = _step("  Content-Type: application/json", '"Content-Type": "application/json"' in src) and ok
    ok = _step("  body JSON.stringify({account_id, password})",
               'JSON.stringify({ account_id, password' in src) and ok
    return ok


def test_login_error_handling():
    print("\n[3/5] 错误处理（错密 + 锁定）")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  401 处理（剩余次数）", "data.remaining" in src) and ok
    ok = _step("  429 处理（锁定）", "r.status === 429" in src) and ok
    ok = _step("  锁定文案", '账户已锁定 15 min' in src) and ok
    ok = _step("  失败后 select password", "$password.select()" in src) and ok
    return ok


def test_admin_logout():
    print("\n[4/5] adminLogout 函数")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function adminLogout() 存在", "async function adminLogout()" in src) and ok
    ok = _step("  fetch POST /api/admin/logout", 'fetch("/api/admin/logout"' in src) and ok
    ok = _step("  清 sessionStorage token", 'removeItem("hfe_admin_token")' in src) and ok
    ok = _step("  location.reload() 刷新", "location.reload()" in src) and ok
    ok = _step("  logout 按钮 onclick", 'onclick="adminLogout()"' in src) and ok
    return ok


def test_backward_compat():
    print("\n[5/5] 向后兼容（v1.7.47 ADMIN_TOKEN）")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  whoami 先试 session cookie", 'api("/api/admin/whoami")' in src) and ok
    ok = _step("  老 sessionStorage token 提示升级", "检测到旧版 ADMIN_TOKEN" in src) and ok
    ok = _step("  取消升级 → 继续用老 token", "继续用旧 token" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.8.0 main.js admin 登录 form 静态测试 ===\n")
    ok1 = test_admin_login_form()
    ok2 = test_admin_login_form_submit()
    ok3 = test_login_error_handling()
    ok4 = test_admin_logout()
    ok5 = test_backward_compat()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
