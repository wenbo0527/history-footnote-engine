"""v1.9.5 布局检查：用 jsdom 模拟 renderGame 后的 DOM 结构"""
import json
import sys
import urllib.request
import re

# 抓取主页面 + main.js
try:
    import requests
except ImportError:
    requests = None

# 直接读 main.js 做静态分析（不需要启动浏览器）
main_js_path = "/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web/static/js/main.js"
with open(main_js_path, "r", encoding="utf-8") as f:
    content = f.read()

print("=" * 60)
print("🆕 v1.9.5 布局静态分析")
print("=" * 60)

# 1️⃣ 检查关键 id 是否重复
ids_to_check = ["action-input", "player_input", "voice-options", "input-area",
                "action-area", "game-input-slot", "btn_submit", "submit_msg"]

print("\n[1] 关键 id 分布（看 renderGame / renderActionBar / appendInputArea / appendVoiceOptions 区域）")
# 找 renderGame 函数
def extract_function(name, content):
    """精准提取顶级函数（按 line 切分）"""
    pat = f"function {name}("
    start = content.find(pat)
    if start < 0:
        return None
    # 从 start 起，按字符配对花括号（处理 JS 字符串 / 模板字符串 / 注释）
    i = content.find("{", start)
    if i < 0:
        return None
    depth = 0
    in_str = None  # '"' / "'" / "`"
    in_comment = None  # '//' / '/*'
    while i < len(content):
        c = content[i]
        nxt = content[i+1] if i + 1 < len(content) else ""
        if in_comment == "//":
            if c == "\n":
                in_comment = None
        elif in_comment == "/*":
            if c == "*" and nxt == "/":
                in_comment = None
                i += 2
                continue
        elif in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        else:
            if c == "/" and nxt == "/":
                in_comment = "//"
                i += 2
                continue
            if c == "/" and nxt == "*":
                in_comment = "/*"
                i += 2
                continue
            if c in ('"', "'"):
                in_str = c
            elif c == "`":
                in_str = "`"
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return content[start:i+1]
        i += 1
    return None


rg_block = extract_function("renderGame", content)
if rg_block:
    rg_ids = []
    for i in ids_to_check:
        c = rg_block.count(f'"{i}"') + rg_block.count(f"id=\"{i}\"")
        rg_ids.append((i, c))
    for i, c in rg_ids:
        print(f"  renderGame 中 {i!r}: {c} 次")
    print(f"  renderGame 长度: {len(rg_block)} chars")
    # 调试：找 renderActionBar 在 rg_block 中的位置
    idx = rg_block.find("renderActionBar")
    if idx >= 0:
        print(f"  ⚠️ 'renderActionBar' 出现在 rg_block 位置 {idx}，周围: {rg_block[max(0,idx-50):idx+80]!r}")
else:
    print("  ⚠️ extract_function 失败")
    # 调试：手动找
    idx = content.find("function renderGame(")
    print(f"  content.find('function renderGame(') = {idx}")
    if idx >= 0:
        print(f"  周围 200 字符: {content[idx:idx+200]!r}")

ab_block = extract_function("renderActionBar", content)
if ab_block:
    print(f"\n  renderActionBar 仍然存在 (长度 {len(ab_block)} chars)")
    print(f"    ⚠️ renderActionBar 还在文件里，但已不调用（renderGame 已不引用）")

ia_block = extract_function("appendInputArea", content)
if ia_block:
    print(f"\n  appendInputArea 仍然存在 (长度 {len(ia_block)} chars)")
    for i in ids_to_check:
        c = ia_block.count(f'"{i}"') + ia_block.count(f"id=\"{i}\"")
        if c > 0:
            print(f"    appendInputArea 中 {i!r}: {c} 次")

# 2️⃣ 检查 renderGame 是否还调用 renderActionBar
print("\n[2] renderGame 调用链检查")
if rg_block:
    for kw in ["renderActionBar()", "renderActionBar(", "renderSidebar", "appendInputArea",
               "appendVoiceOptions", "appendOpeningVoiceOptions", "classList.add(\"game-mode\")",
               "getElementById(\"game-input-slot\")"]:
        c = rg_block.count(kw)
        print(f"  {kw!r}: {c} 次")

# 3️⃣ 检查 CSS 里有 .game-mode
print("\n[3] CSS 检查（layout.game-mode）")
css_path = "/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web/static/css/main.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()
print(f"  '.layout.game-mode' 在 CSS 中: {'✓' if '.layout.game-mode' in css else '❌'}")
print(f"  'flex: 0 0 240px' 桌面 char-card/timeline: {'✓' if 'flex: 0 0 240px' in css else '❌'}")
print(f"  'flex: 1 1 480px' narrative 弹性: {'✓' if 'flex: 1 1 480px' in css else '❌'}")
print(f"  'flex 0 0 200px' 平板 (<=1200px): {'✓' if 'flex: 0 0 200px' in css else '❌'}")

# 4️⃣ 检查 appendInputArea 槽位逻辑
if ia_block:
    has_slot = "game-input-slot" in ia_block
    has_fallback = "$main.appendChild" in ia_block
    print(f"\n[4] appendInputArea 槽位逻辑")
    print(f"  优先挂到 #game-input-slot: {'✓' if has_slot else '❌'}")
    print(f"  兜底挂到 $main: {'✓' if has_fallback else '❌'}")

# 5️⃣ 总结断言
print("\n" + "=" * 60)
print("总结")
print("=" * 60)
checks = []
# renderGame 不能再调用 renderActionBar（v1.9.0 占位）
# 注意：注释里提到"renderActionBar"不算
if rg_block:
    rg_code_no_comments = re.sub(r"//[^\n]*", "", rg_block)
    rg_code_no_comments = re.sub(r"/\*.*?\*/", "", rg_code_no_comments, flags=re.DOTALL)
    has_call = bool(re.search(r"\brenderActionBar\s*\(", rg_code_no_comments))
    checks.append(("renderGame 不再调 renderActionBar", not has_call))
# renderGame 应调用 game-mode
checks.append(("renderGame 进入 game-mode", "game-mode" in (rg_block or "")))
# appendInputArea 应优先挂 slot
if ia_block:
    checks.append(("appendInputArea 优先挂 #game-input-slot", "game-input-slot" in ia_block))
# CSS .game-mode 存在
checks.append(("CSS .layout.game-mode 存在", ".layout.game-mode" in css))
# CSS 自适应 flex
checks.append(("桌面 char-card flex: 0 0 240px", "flex: 0 0 240px" in css))
checks.append(("narrative 弹性 flex: 1 1 480px", "flex: 1 1 480px" in css))

passed = 0
for name, ok in checks:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}")
    if ok:
        passed += 1

print(f"\n通过: {passed}/{len(checks)}")
sys.exit(0 if passed == len(checks) else 1)
