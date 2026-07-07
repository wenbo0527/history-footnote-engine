"""🆕 v1.9.1 narrative 折叠修复 + 视觉对比度优化 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_narrative_collapse_fix():
    """narrative 折叠修复（事件代理）"""
    print("[1/5] narrative 折叠修复")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  data-collapse-toggle 替代 onclick", "data-collapse-toggle=" in src) and ok
    ok = _step("  data-target 不再用于 toggle", 'data-target="${id}"' not in src or src.count('data-target="${id}"') == 0) and ok
    ok = _step("  document.addEventListener 事件代理", 'document.addEventListener("click"' in src) and ok
    ok = _step("  closest button[data-collapse-toggle]", 'closest("button[data-collapse-toggle]")' in src) and ok
    ok = _step("  narrativeToggle console.warn 调试", "console.warn" in src) and ok
    ok = _step("  btn.innerHTML 替代 textContent", "btn.innerHTML" in src) and ok
    return ok


def test_no_transparent_narrative():
    """narrative 改不透明"""
    print("\n[2/5] narrative 不透明")
    src = CSS.read_text(encoding="utf-8")
    js = MAIN.read_text(encoding="utf-8")
    ok = True
    # 1. .narrative 改 #fffaf0（不透明）
    ok = _step("  .narrative background 不透明 #fffaf0", ".narrative {" in src and "background: #fffaf0" in src) and ok
    ok = _step("  .narrative 不用 rgba 透明（旧 namerative 用）", "rgba(255, 250, 235, 0.7)" not in src or src.find(".narrative {") < src.find("rgba(255, 250, 235, 0.7)")) and ok
    ok = _step("  border-left 加深到 #5a3e1f", "border-left: 4px solid #5a3e1f" in src) and ok
    ok = _step("  box-shadow 微阴影", "box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05)" in src) and ok
    # 2. preview/full 透明
    ok = _step("  preview/full background transparent", "background: transparent !important" in src) and ok
    return ok


def test_timeline_contrast():
    """大事记高对比"""
    print("\n[3/5] 大事记高对比")
    src = CSS.read_text(encoding="utf-8")
    js = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  .timeline 背景 #f0e6c8", ".timeline {" in src and "background: #f0e6c8" in src) and ok
    ok = _step("  .timeline 边框 2px #5a3e1f", "border: 2px solid #5a3e1f" in src) and ok
    ok = _step("  .timeline-title 加深", ".timeline-title" in src and "color: #3a2a17" in src) and ok
    ok = _step("  .timeline-year 加深加粗", "color: #3a2a17" in src and "font-weight: 700" in src) and ok
    ok = _step("  .timeline-event.highlight 红色", "highlight" in src and "color: #c0392b" in src) and ok
    ok = _step("  timeline-item 分隔线", ".timeline-item" in src and "border-bottom: 1px solid" in src) and ok
    # JS 改用 class
    ok = _step("  renderTimeline 用 .timeline-title class", "class=\"timeline-title\"" in js) and ok
    ok = _step("  renderTimeline 用 .timeline-item class", "class=\"timeline-item\"" in js) and ok
    ok = _step("  renderTimeline 用 .timeline-year class", "class=\"timeline-year\"" in js) and ok
    ok = _step("  renderTimeline 用 .timeline-event class", "class=\"timeline-event" in js) and ok
    return ok


def test_char_card_border():
    """角色卡边框加深"""
    print("\n[4/5] 角色卡边框")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  .char-card 边框 2px #c4a878", ".char-card {" in src and "border: 2px solid #c4a878" in src) and ok
    ok = _step("  旧 1px 移除", "char-card 1px solid" not in src) and ok
    ok = _step("  box-shadow 微阴影", "0 2px 6px rgba(0, 0, 0, 0.08)" in src) and ok
    return ok


def test_collapse_button_hover():
    """折叠按钮 hover 效果"""
    print("\n[5/5] 折叠按钮 hover/active")
    src = CSS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  button[data-collapse-toggle]:hover", 'button[data-collapse-toggle]:hover' in src) and ok
    ok = _step("  transform: translateY(-1px)", "transform: translateY(-1px)" in src) and ok
    ok = _step("  button:hover 背景加深", "background: #3a2a17" in src) and ok
    ok = _step("  :active 状态", "button[data-collapse-toggle]:active" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.9.1 narrative 折叠 + 视觉对比度 静态测试 ===\n")
    ok1 = test_narrative_collapse_fix()
    ok2 = test_no_transparent_narrative()
    ok3 = test_timeline_contrast()
    ok4 = test_char_card_border()
    ok5 = test_collapse_button_hover()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
