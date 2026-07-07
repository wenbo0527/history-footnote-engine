"""🆕 v1.8.6 admin 设置功能 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"
ADMIN = ROOT / "src/history_footnote/web_server/routers/admin.py"
REGISTRY = ROOT / "src/history_footnote/web_server/router_registry.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_backend_handler():
    print("[1/5] 后端 handler")
    src = ADMIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  handle_GET_admin_settings 存在", "def handle_GET_admin_settings" in src) and ok
    ok = _step("  handle_POST_admin_settings 存在", "def handle_POST_admin_settings(" in src) and ok
    ok = _step("  handle_POST_admin_settings_reset 存在", "def handle_POST_admin_settings_reset" in src) and ok
    ok = _step("  ENV_PATH 用 .env", 'ENV_PATH = Path(os.environ.get("ENV_PATH", ".env"))' in src) and ok
    ok = _step("  _read_env_settings 读 .env", "def _read_env_settings" in src) and ok
    ok = _step("  _write_env_settings 写 .env", "def _write_env_settings" in src) and ok
    ok = _step("  白名单 ALLOWED 4 字段", '"LLM_MAX_REQUESTS": int' in src and "GLOBAL_WINDOW_SECONDS" in src) and ok
    ok = _step("  范围校验 ≥ 1", "必须 ≥ 1" in src) and ok
    ok = _step("  ADMIN_TOKEN mask", "***" in src) and ok
    return ok


def test_backend_route():
    print("\n[2/5] 后端路由注册")
    src = REGISTRY.read_text(encoding="utf-8")
    ok = True
    ok = _step("  /api/admin/settings POST", '"/api/admin/settings": _admin.handle_POST_admin_settings' in src) and ok
    ok = _step("  /api/admin/settings/reset", '"/api/admin/settings/reset"' in src) and ok
    ok = _step("  /api/admin/settings GET", '"/api/admin/settings": _admin.handle_GET_admin_settings' in src) and ok
    return ok


def test_frontend_tab():
    print("\n[3/5] 前端 settings tab")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  按钮 onclick=adminShowTab('settings')", "adminShowTab('settings')" in src) and ok
    ok = _step("  case 'settings' 分支", 'tab === "settings"' in src) and ok
    ok = _step("  renderAdminSettings 调用", "await renderAdminSettings()" in src) and ok
    return ok


def test_frontend_functions():
    print("\n[4/5] 前端函数")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  async function renderAdminSettings 存在", "async function renderAdminSettings" in src) and ok
    ok = _step("  async function adminSaveSettings 存在", "async function adminSaveSettings" in src) and ok
    ok = _step("  async function adminResetSettings 存在", "async function adminResetSettings" in src) and ok
    ok = _step("  4 输入框 set-llm-max/win/g-max/g-win", all(k in src for k in ["set-llm-max", "set-llm-win", "set-g-max", "set-g-win"])) and ok
    ok = _step("  4 按钮：保存/重置/重载/重启", all(k in src for k in ["adminSaveSettings", "adminResetSettings", "renderAdminSettings", "location.reload"])) and ok
    ok = _step("  withLoading 包 spinner", "withLoading(\"加载设置" in src or "withLoading(\"保存" in src) and ok
    return ok


def test_ux():
    print("\n[5/5] UX 细节")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  HAPTIC.tap 进入", "HAPTIC.tap()" in src) and ok
    ok = _step("  HAPTIC.success 保存成功", "HAPTIC.success()" in src) and ok
    ok = _step("  范围校验前端", "必须 ≥ 1" in src) and ok
    ok = _step("  confirm 恢复默认", "confirm(\"确定恢复默认" in src) and ok
    ok = _step("  警告 panel（重启影响）", "中断所有用户" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.8.6 admin 设置功能 静态测试 ===\n")
    ok1 = test_backend_handler()
    ok2 = test_backend_route()
    ok3 = test_frontend_tab()
    ok4 = test_frontend_functions()
    ok5 = test_ux()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
