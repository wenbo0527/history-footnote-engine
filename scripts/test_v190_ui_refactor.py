"""🆕 v1.9.0 UI 重构 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_state_game():
    print("[1/5] state.game 字段")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  state.game 存在", "game: {" in src) and ok
    ok = _step("  round_current", "round_current:" in src) and ok
    ok = _step("  year_current 1587", "year_current: 1587" in src) and ok
    ok = _step("  year_max 1601", "year_max: 1601" in src) and ok
    ok = _step("  city 苏州府", "苏州府" in src) and ok
    ok = _step("  cash/looms/reputation", all(k in src for k in ["cash:", "looms:", "reputation:"])) and ok
    ok = _step("  family/skills/history", all(k in src for k in ["family:", "skills:", "history:"])) and ok
    ok = _step("  quick_actions 4 项", '"问行情", "去机房", "问税关", "闲逛"' in src) and ok
    ok = _step("  timeline 4 大事", "1587, event: \"你出生\"" in src and "1601, event: \"葛贤抗税\"" in src) and ok
    return ok


def test_5_render_functions():
    print("\n[2/5] 5 render 函数")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function renderGameHeader", "function renderGameHeader()" in src) and ok
    ok = _step("  function renderCharacterCard", "function renderCharacterCard()" in src) and ok
    ok = _step("  function renderTimeline", "function renderTimeline()" in src) and ok
    ok = _step("  function renderActionBar", "function renderActionBar()" in src) and ok
    ok = _step("  function renderGameFull", "function renderGameFull(" in src) and ok
    ok = _step("  顶部 banner 渐变背景", "linear-gradient(135deg, #5a3e1f" in src) and ok
    ok = _step("  时代进度条", "时代进度" in src) and ok
    ok = _step("  银两/织机/声望", all(k in src for k in ["💰", "🧵", "⭐"])) and ok
    ok = _step("  submitAction 函数", "async function submitAction" in src) and ok
    ok = _step("  useQuickAction 函数", "function useQuickAction" in src) and ok
    return ok


def test_layout_3_column():
    print("\n[3/5] 3 栏布局")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  renderGameLayout 存在", "function renderGameLayout(" in src) and ok
    ok = _step("  display:flex 3 栏", "display:flex;gap:16px" in src) and ok
    ok = _step("  narrative-area flex:1", "narrative-area" in src and "flex:1" in src) and ok
    ok = _step("  char-card 240px", "width:240px" in src) and ok
    ok = _step("  timeline 200px", "width:200px" in src) and ok
    return ok


def test_responsive_css():
    print("\n[4/5] 响应式 CSS")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  @media 900px 3 栏折叠", "max-width: 900px" in src) and ok
    ok = _step("  flex-direction: column", "flex-direction: column" in src) and ok
    ok = _step("  @media 600px banner 简化", "max-width: 600px" in src) and ok
    ok = _step("  暗色模式游戏组件", ".game-container" in src and "prefers-color-scheme: dark" in src) and ok
    return ok


def test_components():
    print("\n[5/5] 组件细节")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  角色家庭默认数据", "妻\", name: \"张氏\"" in src) and ok
    ok = _step("  母 沈王氏", "沈王氏" in src) and ok
    ok = _step("  技能挽丝/织绸", "挽丝" in src and "织绸" in src) and ok
    ok = _step("  timeline highlight 红色", "highlight" in src and "#c0392b" in src) and ok
    ok = _step("  快捷行动 4 项", "问行情" in src and "去机房" in src and "问税关" in src and "闲逛" in src) and ok
    ok = _step("  历史输入显示", "history" in src and "slice(-3)" in src) and ok
    ok = _step("  提交 toast", "showToast" in src) and ok
    ok = _step("  HAPTIC.tap", "HAPTIC.tap()" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.9.0 UI 重构 静态测试 ===\n")
    ok1 = test_state_game()
    ok2 = test_5_render_functions()
    ok3 = test_layout_3_column()
    ok4 = test_responsive_css()
    ok5 = test_components()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
