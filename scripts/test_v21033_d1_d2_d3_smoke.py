"""🆕 v2.10.33 D1+D2+D3 静态扫描验证

D1.1: /routes/+page.svelte 不再强制跳 /login
D1.2: StartMenu.svelte 增加「游客快速试玩」按钮 + handleQuickGuestTry
D2.1: /api/start 接受 scripted 字段, 写到 state.scripted_intent
D2.2: /game/+page.svelte 不再读 URL/sessionStorage, 只读 state.scripted_intent
D3.1: account.logout() 清 hfe_* prefix
"""
from __future__ import annotations

import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def main():
    print("=== v2.10.33 D1+D2+D3 静态扫描 ===\n")
    frontend = ROOT / "src/frontend/src"
    backend = ROOT / "src/history_footnote"

    # ---------- D1.1: +page.svelte ----------
    print("[D1.1] 首页不再强制跳 /login")
    src = (frontend / "routes/+page.svelte").read_text(encoding="utf-8")
    ok1 = _step(
        "已移除 goto('/login?next=/')",
        "goto('/login?next=/')" not in src,
    )
    ok2 = _step(
        "检查游客访问标记存在",
        "游客也能看 StartMenu" in src or "checking = false" in src,
    )

    # ---------- D1.2: StartMenu ----------
    print("\n[D1.2] StartMenu 增加游客快速试玩入口")
    src = (frontend / "lib/components/home/StartMenu.svelte").read_text(encoding="utf-8")
    ok3 = _step("游客按钮文案存在", "游客快速试玩" in src or "立刻开局" in src)
    ok4 = _step("handleQuickGuestTry 函数存在", "handleQuickGuestTry" in src)
    ok5 = _step("setGuest 已 import", "setGuest" in src)
    ok6 = _step("调用 ensureGuestAccountId", "ensureGuestAccountId" in src)

    # ---------- D2.1: backend scripted_intent ----------
    print("\n[D2.1] 后端 /api/start 接受 scripted 字段")
    src = (backend / "web_server/routers/session.py").read_text(encoding="utf-8")
    ok7 = _step(
        "session.py 接受 scripted 字段",
        "scripted_intent" in src and "body.get(\"scripted\"" in src,
    )

    # ---------- D2.1 前端: startGame 透传 scripted ----------
    src = (frontend / "lib/api/start.ts").read_text(encoding="utf-8")
    ok8 = _step(
        "startGame 接受 scripted 参数",
        "scripted" in src and "scripted?: boolean" in src,
    )

    # ---------- D2.1 前端: wizard.setScripted ----------
    src = (frontend / "lib/stores/wizard.svelte.ts").read_text(encoding="utf-8")
    ok9 = _step(
        "wizard store 含 scripted 字段 + setScripted 方法",
        "scripted:" in src and "setScripted" in src,
    )

    # ---------- D2.1 前端: WizardShell 用 wizard.state.scripted ----------
    src = (frontend / "lib/components/wizard/WizardShell.svelte").read_text(encoding="utf-8")
    ok10 = _step(
        "WizardShell 透传 scripted 到 startGame",
        "scripted: isScripted" in src or "scripted: wizard.state.scripted" in src,
    )

    # ---------- D2.2 前端: /game 不读 URL/sessionStorage scripted ----------
    src = (frontend / "routes/game/+page.svelte").read_text(encoding="utf-8")
    ok11 = _step(
        "/game 不再读 sessionStorage hfe_wizard_scripted",
        "sessionStorage.getItem('hfe_wizard_scripted')" not in src,
    )
    ok12 = _step(
        "/game 改用 state.scripted_intent",
        "scripted_intent" in src and "intentScripted" in src,
    )

    # ---------- D2.2 后端: format_state 透传 scripted_intent ----------
    src = (backend / "web_server/views/format_state.py").read_text(encoding="utf-8")
    ok13 = _step(
        "format_state 透传 scripted_intent",
        "scripted_intent" in src and "_compute_ending" in src,
    )

    # ---------- D3.1: logout 清所有 hfe_* ----------
    src = (frontend / "lib/api/account.ts").read_text(encoding="utf-8")
    ok14 = _step(
        "logout 清 hfe_ 前缀的 key",
        "key.startsWith('hfe_')" in src,
    )
    ok15 = _step(
        "logout 也清 sessionStorage hfe_",
        "sessionStorage" in src and "startsWith('hfe_')" in src,
    )

    # ---------- 综合: mapper / types 透传 ----------
    src = (frontend / "lib/api/mapper.ts").read_text(encoding="utf-8")
    ok16 = _step(
        "mapper 透传 no_match + ending + scripted_intent",
        "no_match" in src and "ending" in src and "scripted_intent" in src,
    )

    src = (frontend / "lib/api/types.ts").read_text(encoding="utf-8")
    ok17 = _step(
        "types 含 Ending interface + no_match + scripted_intent",
        "interface Ending" in src and "no_match?" in src and "scripted_intent?" in src,
    )

    src = (frontend / "lib/components/modals/index.ts").read_text(encoding="utf-8")
    ok18 = _step(
        "EndingModal 已 export",
        "EndingModal" in src,
    )

    src = (frontend / "lib/components/modals/EndingModal.svelte").read_text(encoding="utf-8")
    ok19 = _step(
        "EndingModal.svelte 存在且非空",
        len(src) > 1000,
        detail=f"{len(src)} chars",
    )

    # ---------- GameView 接入 EndingModal ----------
    src = (frontend / "routes/game/+page.svelte").read_text(encoding="utf-8")
    ok20 = _step(
        "GameView 含 EndingModal 实例",
        "<EndingModal" in src,
    )

    all_ok = all([
        ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10,
        ok11, ok12, ok13, ok14, ok15, ok16, ok17, ok18, ok19, ok20,
    ])
    print("\n=== 汇总 ===")
    if all_ok:
        print(f"🎉 D1+D2+D3 全部 {sum([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10, ok11, ok12, ok13, ok14, ok15, ok16, ok17, ok18, ok19, ok20])}/20 项静态扫描通过")
        sys.exit(0)
    else:
        passed = sum([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10, ok11, ok12, ok13, ok14, ok15, ok16, ok17, ok18, ok19, ok20])
        print(f"❌ 失败 ({passed}/20)")
        sys.exit(1)


if __name__ == "__main__":
    main()