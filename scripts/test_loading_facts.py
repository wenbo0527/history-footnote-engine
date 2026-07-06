"""🆕 v1.7.30 等待时小知识轮播验证

覆盖：
1. LoadingModal.show() 输出 .loading-facts 容器
2. JS 包含静态 WANLI_FACTS 知识库
3. collectFacts 4 个数据源（world_dwell / era_data / WANLI_FACTS / narrative_history）
4. cycleFact / refreshFacts / renderFact 三个方法定义
5. 5 秒自动轮播 + hover 暂停 8 秒
6. 左右翻页按钮
7. CSS 8 关键样式
8. 静态知识库条数 ≥ 10
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "src/history_footnote/web/static/js/main.js"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def get_show_fn_text():
    """提取 LoadingModal.show() 整个函数（花括号平衡）"""
    src = JS.read_text(encoding="utf-8")
    lines = src.splitlines()
    fn_start = None
    for i, line in enumerate(lines):
        if line.startswith("  show("):
            fn_start = i
            break
    if fn_start is None:
        return ""
    text = "\n".join(lines[fn_start:])
    depth = 0
    started = False
    end_index = None
    in_string = None
    in_comment = None
    for i, ch in enumerate(text):
        c2 = text[i : i + 2]
        if in_string is not None:
            if ch == "\\":
                continue
            if ch == in_string:
                in_string = None
            continue
        if in_comment is not None:
            if in_comment == "//" and ch == "\n":
                in_comment = None
            elif in_comment == "/*" and c2 == "*/":
                in_comment = None
                continue
            continue
        if c2 == "//":
            in_comment = "//"
            continue
        if c2 == "/*":
            in_comment = "/*"
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            continue
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                end_index = i + 1
                break
    return text[:end_index] if end_index else ""


def get_full_modal_block():
    """获取 LoadingModal 整个对象定义 + 后面 WANLI_FACTS"""
    src = JS.read_text(encoding="utf-8")
    lines = src.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("const LoadingModal = {"):
            start = i
            break
    if start is None:
        return ""
    return "\n".join(lines[start:])


def test_modal_show_output():
    print("[1/7] LoadingModal.show() 输出 .loading-facts 容器")
    show = get_show_fn_text()
    if not show:
        return _step("show() 函数存在", False)
    return _step(
        "  show() 输出 loading-facts 容器 + loading-facts-header",
        'class="loading-facts"' in show
        and 'class="loading-facts-header"' in show,
    )


def test_static_facts_library():
    print("\n[2/7] 静态 WANLI_FACTS 知识库")
    block = get_full_modal_block()
    has_lib = "const WANLI_FACTS" in block
    return _step(
        "  WANLI_FACTS 常量定义",
        has_lib,
    )


def test_collect_facts_sources():
    print("\n[3/7] collectFacts 4 个数据源")
    block = get_full_modal_block()
    sources = [
        ("wizard.world_dwell", "wizard.world_dwell" in block),
        ("wizard.era_data", "wizard.era_data" in block),
        ("WANLI_FACTS 静态", "WANLI_FACTS" in block),
        ("state.narrative_history", "narrative_history" in block),
    ]
    all_ok = True
    for name, ok in sources:
        all_ok = _step(f"  来源：{name}", ok) and all_ok
    return all_ok


def test_fact_methods():
    print("\n[4/7] cycleFact / refreshFacts / renderFact 三个方法")
    block = get_full_modal_block()
    return _step(
        "  三个方法都存在",
        "cycleFact(direction)" in block
        and "refreshFacts()" in block
        and "renderFact()" in block,
    )


def test_auto_cycle_and_hover_pause():
    print("\n[5/7] 自动轮播 + hover 暂停")
    block = get_full_modal_block()
    auto_5s = "setInterval" in block and "5000" in block
    hover_pause = "mouseenter" in block and "factPauseUntil" in block
    return _step(
        "  5 秒自动 + hover 暂停",
        auto_5s and hover_pause,
    )


def test_prev_next_buttons():
    print("\n[6/7] 翻页按钮")
    show = get_show_fn_text()
    return _step(
        "  上一条/下一条按钮 + onclick 调 cycleFact",
        "LoadingModal.cycleFact(-1)" in show
        and "LoadingModal.cycleFact(1)" in show,
    )


def test_css():
    print("\n[7/7] CSS 关键样式")
    src = CSS.read_text(encoding="utf-8")
    checks = [
        (".loading-facts {", ".loading-facts {" in src),
        (".loading-facts-header", ".loading-facts-header" in src),
        (".loading-facts-prev", ".loading-facts-prev" in src),
        (".loading-facts-next", ".loading-facts-next" in src),
        (".loading-facts-content", ".loading-facts-content" in src),
        (".loading-facts-fadeout 动画", ".loading-facts-fadeout" in src),
        (".loading-facts-source 标签", ".loading-facts-source" in src),
        (".loading-facts-counter", ".loading-facts-counter" in src),
    ]
    all_ok = True
    for name, ok in checks:
        all_ok = _step(f"  {name}", ok) and all_ok
    return all_ok


def test_static_facts_count():
    """静态事实 ≥ 10 条"""
    print("\n[Bonus] 静态知识库条数")
    block = get_full_modal_block()
    # 简单数 { cat: ..., text: ... } 出现次数
    count = block.count("{ cat:") + block.count("{cat:")
    return _step(
        f"  WANLI_FACTS 共 {count} 条（≥ 10）",
        count >= 10,
    )


if __name__ == "__main__":
    print("=== v1.7.30 等待时小知识轮播验证 ===\n")
    ok1 = test_modal_show_output()
    ok2 = test_static_facts_library()
    ok3 = test_collect_facts_sources()
    ok4 = test_fact_methods()
    ok5 = test_auto_cycle_and_hover_pause()
    ok6 = test_prev_next_buttons()
    ok7 = test_css()
    ok8 = test_static_facts_count()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8]):
        print("\n🎉 8 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=} {ok8=}")
        sys.exit(1)
