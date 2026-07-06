"""🆕 v1.7.30 discoveries + 14 类 EventId 静态测试

覆盖：
1. state.discoveries 字段定义
2. add_discovery() / update_discovery() / get_discoveries() / get_discoveries_summary()
3. event_parser 6 类 discover.* 处理器
4. event_parser EVENT_RE 支持属性值含 /
5. format_state 暴露 discoveries + 11 个 v1.7.30 字段
6. main.js sidebar 信件 + 知识 折叠区
7. main.js flattenDiscoveries() 助手
8. system_prompt 加 discover.* 主动创建指引
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GS = ROOT / "src/history_footnote/game_state.py"
EP = ROOT / "src/history_footnote/event_parser.py"
FS = ROOT / "src/history_footnote/web_server/views/format_state.py"
JS = ROOT / "src/history_footnote/web/static/js/main.js"
SP = ROOT / "src/history_footnote/dm/prompts/system_base.md"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_state_discoveries_field():
    print("[1/8] state.discoveries 字段")
    src = GS.read_text(encoding="utf-8")
    return _step(
        "  discoveries: dict = field(default_factory=dict)",
        "discoveries: dict = field(default_factory=dict)" in src,
    )


def test_add_discovery():
    print("\n[2/8] add_discovery() / update_discovery() / get_discoveries() / get_discoveries_summary()")
    src = GS.read_text(encoding="utf-8")
    ok = True
    for fn in ["def add_discovery", "def update_discovery", "def get_discoveries", "def get_discoveries_summary"]:
        ok = _step(f"  {fn}", fn in src) and ok
    return ok


def test_event_parser_6_kinds():
    print("\n[3/8] event_parser 6 类 discover.* 处理器")
    src = EP.read_text(encoding="utf-8")
    ok = True
    ok = _step("  _apply_discover_event", "def _apply_discover_event" in src) and ok
    ok = _step("  _HANDLERS[\"discover\"]", '_HANDLERS["discover"]' in src) and ok
    ok = _step("  6 种 kind 验证（place/person/item/letter/event/fact）",
               "valid_kinds = {\"place\", \"person\", \"item\", \"letter\", \"event\", \"fact\"}" in src) and ok
    return ok


def test_event_parser_attrs_with_slash():
    """修复 bug：EVENT_RE attrs 接受属性值含 /"""
    print("\n[4/8] EVENT_RE attrs 接受 /")
    src = EP.read_text(encoding="utf-8")
    return _step(
        "  正则 (?P<attrs>.*?)\\s*/>（替代 [^/]*?）",
        '(?P<attrs>.*?)\\s*/>' in src,
    )


def test_format_state_v1730():
    print("\n[5/8] format_state 暴露 v1.7.30 字段")
    src = FS.read_text(encoding="utf-8")
    fields = [
        "cash", "rice", "debt", "monthly_burn", "financial_log",
        "family_members", "genealogy",
        "city_properties", "inventory",
        "discoveries", "current_city",
    ]
    ok = True
    for f in fields:
        ok = _step(f"  {f}", f'"{f}"' in src) and ok
    return ok


def test_sidebar_letters_facts():
    print("\n[6/8] sidebar 信件 + 知识 折叠区")
    src = JS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  sb-section-letters", "sb-section-letters" in src) and ok
    ok = _step("  sb-section-facts", "sb-section-facts" in src) and ok
    return ok


def test_flatten_discoveries():
    print("\n[7/8] flattenDiscoveries() 助手")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  function flattenDiscoveries + renderSidebar 调它",
        "function flattenDiscoveries" in src
        and "flattenDiscoveries(data);" in src,
    )


def test_system_prompt_discover():
    print("\n[8/8] system_prompt 加 discover.* 主动创建指引")
    src = SP.read_text(encoding="utf-8")
    return _step(
        "  discover.* 段 + 14 类 EventId + 主动创建指引",
        "discover.*" in src
        and "14 类" in src
        and "discover.letter" in src
        and "主动创建指引" in src,
    )


if __name__ == "__main__":
    print("=== v1.7.30 discoveries + 14 类 EventId 静态测试 ===\n")
    ok1 = test_state_discoveries_field()
    ok2 = test_add_discovery()
    ok3 = test_event_parser_6_kinds()
    ok4 = test_event_parser_attrs_with_slash()
    ok5 = test_format_state_v1730()
    ok6 = test_sidebar_letters_facts()
    ok7 = test_flatten_discoveries()
    ok8 = test_system_prompt_discover()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8]):
        print("\n🎉 8 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=} {ok8=}")
        sys.exit(1)
