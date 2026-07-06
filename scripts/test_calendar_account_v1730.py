"""🆕 v1.7.30 历法 + 账户体系 静态测试

覆盖：
1. rule_engine.check_calendar() 方法
2. rule_engine._parse_current_year() 支持中英文年份
3. rule_engine._check_city_condition() 城市过滤
4. game_loop 接入 check_calendar
5. game_loop.set_calendar_events_for_dm()
6. account_system.AccountSystem 完整 CRUD
7. 邀请码 + 账户 + 存档绑定
8. routers/account.py 6 个路由
9. router_registry 路由注册
10. main.js 账户登录 UI
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
RE = ROOT / "src/history_footnote/rule_engine.py"
GL = ROOT / "src/history_footnote/game_loop.py"
AS = ROOT / "src/history_footnote/account_system.py"
ACR = ROOT / "src/history_footnote/web_server/routers/account.py"
RR = ROOT / "src/history_footnote/web_server/router_registry.py"
JS = ROOT / "src/history_footnote/web/static/js/main.js"
SP = ROOT / "src/history_footnote/web_server/views/session.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_check_calendar():
    print("[1/10] rule_engine.check_calendar() 方法")
    src = RE.read_text(encoding="utf-8")
    return _step(
        "  def check_calendar + 触发逻辑（年份 + 城市 + evt_ids）",
        "def check_calendar" in src
        and "def _parse_current_year" in src
        and "def _check_city_condition" in src
        and "major_events" in src
        and "evt_ids" in src,
    )


def test_parse_current_year():
    print("\n[2/10] _parse_current_year 支持中英文")
    src = RE.read_text(encoding="utf-8")
    return _step(
        "  regex + 万历=1573 + _cn_to_int",
        "def _parse_current_year" in src
        and '"万历"' in src
        and "1573" in src
        and "def _cn_to_int" in src,
    )


def test_check_city_condition():
    print("\n[3/10] _check_city_condition 城市过滤")
    src = RE.read_text(encoding="utf-8")
    return _step(
        "  5 城市检查（suzhou/hangzhou/songjiang/nanjing/shengze）",
        all(c in src for c in ["suzhou", "hangzhou", "songjiang", "nanjing", "shengze"]),
    )


def test_game_loop_check_calendar():
    print("\n[4/10] game_loop 接入 check_calendar")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  check_calendar 调用 + set_calendar_events_for_dm 定义",
        "check_calendar" in src
        and "set_calendar_events_for_dm" in src
        and "calendar_events" in src,
    )


def test_set_calendar_events_for_dm():
    print("\n[5/10] set_calendar_events_for_dm() 方法")
    src = GL.read_text(encoding="utf-8")
    return _step(
        "  def set_calendar_events_for_dm",
        "def set_calendar_events_for_dm" in src,
    )


def test_account_system():
    print("\n[6/10] account_system.py 完整 CRUD")
    src = AS.read_text(encoding="utf-8")
    funcs = [
        "class AccountSystem",
        "create_invite_code",
        "verify_invite_code",
        "use_invite_code",
        "create_account",
        "get_account",
        "get_account_by_username",
        "list_accounts",
        "bind_save",
        "list_saves",
        "get_save_path",
    ]
    ok = True
    for f in funcs:
        ok = _step(f"  {f}", f in src) and ok
    return ok


def test_invite_and_save_binding():
    print("\n[7/10] 邀请码 + 账户 + 存档绑定")
    sys.path.insert(0, str(ROOT / "src"))
    import tempfile
    from history_footnote.account_system import AccountSystem

    tmp = Path(tempfile.mkdtemp(prefix="hf_acc_"))
    sys_inst = AccountSystem(tmp)
    inv = sys_inst.create_invite_code(label="test", max_uses=1)
    acc, err = sys_inst.create_account("测试用户", inv.code)
    sys_inst.bind_save(acc.account_id, "save_001")
    saves = sys_inst.list_saves(acc.account_id)
    ok = True
    ok = _step(f"  邀请码 {inv.code} 创建成功", bool(inv.code.startswith("INV-"))) and ok
    ok = _step(f"  账户 {acc.username} 创建（err={err}）", acc is not None and err == "") and ok
    ok = _step(f"  存档 save_001 绑定", len(saves) == 1 and saves[0]["save_id"] == "save_001") and ok
    return ok


def test_account_router():
    print("\n[8/10] routers/account.py 6 个路由")
    src = ACR.read_text(encoding="utf-8")
    funcs = [
        "handle_POST_account_register",
        "handle_POST_account_login",
        "handle_GET_account_saves",
        "handle_POST_account_create_save",
        "handle_GET_account_info",
        "handle_GET_account_invite_codes",
    ]
    ok = True
    for f in funcs:
        ok = _step(f"  {f}", f in src) and ok
    return ok


def test_router_registry():
    print("\n[9/10] router_registry 路由注册")
    src = RR.read_text(encoding="utf-8")
    return _step(
        "  4 路由（register/login/saves/info/invite_codes）",
        "/api/account/register" in src
        and "/api/account/login" in src
        and "/api/account/saves" in src
        and "/api/account/info" in src
        and "/api/account/invite_codes" in src,
    )


def test_main_js_account_ui():
    print("\n[10/10] main.js 账户 UI")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  showAccountLogin + registerAccount + showSavesList + state.account_id",
        "function showAccountLogin" in src
        and "function registerAccount" in src
        and "function showSavesList" in src
        and "function loginByAccountId" in src
        and "account_id:" in src
        and "INV-XXXX-XXXX" in src,
    )


if __name__ == "__main__":
    print("=== v1.7.30 历法 + 账户体系 静态测试 ===\n")
    ok1 = test_check_calendar()
    ok2 = test_parse_current_year()
    ok3 = test_check_city_condition()
    ok4 = test_game_loop_check_calendar()
    ok5 = test_set_calendar_events_for_dm()
    ok6 = test_account_system()
    ok7 = test_invite_and_save_binding()
    ok8 = test_account_router()
    ok9 = test_router_registry()
    ok10 = test_main_js_account_ui()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10]):
        print("\n🎉 10 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=} {ok8=} {ok9=} {ok10=}")
        sys.exit(1)
