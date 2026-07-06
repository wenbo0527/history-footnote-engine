"""🆕 v1.7.30 我的档案 UI 静态测试

覆盖：
1. main.js 含 6 折叠区（cash/location/family/genealogy/property/inventory）
2. main.js 含 CITY_DISPLAY/RELATION_DISPLAY 常量
3. main.js 含 toggleSbSection/openMyProfile 函数
4. main.js 含 sidebar-my-profile-btn 按钮
5. main.js 含 localStorage 记忆折叠态
6. CSS .sb-section / .sb-section-header 等关键样式
7. CSS 移动端 @media 隐藏次要折叠区
8. CSS .sidebar-my-profile-btn 桌面端隐藏
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "src/history_footnote/web/static/js/main.js"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_6_sb_sections():
    print("[1/8] main.js 6 折叠区")
    src = JS.read_text(encoding="utf-8")
    sections = [
        ("cash 财务", "sb-section-cash"),
        ("location 位置", "sb-section-location"),
        ("family 家人", "sb-section-family"),
        ("genealogy 谱系", "sb-section-genealogy"),
        ("property 财产", "sb-section-property"),
        ("inventory 库存", "sb-section-inventory"),
    ]
    ok = True
    for name, cls in sections:
        ok = _step(f"  {name}（{cls}）", f'data-section="{cls.replace("sb-section-", "")}"' in src or cls in src) and ok
    return ok


def test_constants():
    print("\n[2/8] CITY_DISPLAY / RELATION_DISPLAY 常量")
    src = JS.read_text(encoding="utf-8")
    has_city = "const CITY_DISPLAY" in src and "shengze" in src and "suzhou" in src
    has_rel = "const RELATION_DISPLAY" in src and "wife" in src and "patriarch" in src
    return _step("  CITY_DISPLAY 5 城市", has_city) and _step("  RELATION_DISPLAY 至少含 wife/patriarch", has_rel)


def test_toggle_openMyProfile():
    print("\n[3/8] 折叠区切换 + 弹层入口函数")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  toggleSbSection + openMyProfile 函数定义",
        "function toggleSbSection" in src
        and "function openMyProfile" in src,
    )


def test_my_profile_button():
    print("\n[4/8] sidebar-my-profile-btn 按钮")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  按钮 + onclick 调 openMyProfile",
        'sidebar-my-profile-btn' in src
        and 'onclick="openMyProfile()"' in src,
    )


def test_localStorage_remember():
    print("\n[5/8] localStorage 记忆折叠态")
    src = JS.read_text(encoding="utf-8")
    return _step(
        "  localStorage 读写 hfe_sb_xxx_collapsed",
        "localStorage.setItem(`hfe_sb_" in src
        and "localStorage.getItem(`hfe_sb_" in src,
    )


def test_css_sb_section():
    print("\n[6/8] CSS 折叠区基础样式")
    src = CSS.read_text(encoding="utf-8")
    keys = [
        ".sb-section {",
        ".sb-section-header {",
        ".sb-section-body {",
        ".sb-section-body.collapsed",
        ".sb-item {",
        ".sb-item-name",
        ".sb-item-meta",
        ".sb-section-more",
    ]
    ok = True
    for k in keys:
        ok = _step(f"  {k}", k in src) and ok
    return ok


def test_mobile_media():
    print("\n[7/8] CSS 移动端 @media")
    src = CSS.read_text(encoding="utf-8")
    has_768 = (
        "@media (max-width: 768px)" in src
        and ".sb-section-genealogy" in src
        and ".sb-section-property" in src
        and ".sb-section-inventory" in src
        and "display: none" in src
    )
    has_480 = "@media (max-width: 480px)" in src
    return _step("  移动端隐藏次要折叠区", has_768) and _step("  极小屏 @media (480px)", has_480)


def test_profile_btn_desktop_hidden():
    print("\n[8/8] .sidebar-my-profile-btn 桌面端隐藏")
    src = CSS.read_text(encoding="utf-8")
    return _step(
        "  display: none 默认 + @media 切换",
        ".sidebar-my-profile-btn {\n  display: none" in src,
    )


if __name__ == "__main__":
    print("=== v1.7.30 我的档案 UI 静态测试 ===\n")
    ok1 = test_6_sb_sections()
    ok2 = test_constants()
    ok3 = test_toggle_openMyProfile()
    ok4 = test_my_profile_button()
    ok5 = test_localStorage_remember()
    ok6 = test_css_sb_section()
    ok7 = test_mobile_media()
    ok8 = test_profile_btn_desktop_hidden()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8]):
        print("\n🎉 8 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=} {ok8=}")
        sys.exit(1)
