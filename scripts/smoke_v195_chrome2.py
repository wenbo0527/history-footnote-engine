"""Chrome headless v2: 直接打开 http://localhost:8765，用 evaluate 注入 JS 触发 startGame"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

URL = "http://localhost:8765/"
OUT_DIR = Path("/tmp/v195_chrome")
OUT_DIR.mkdir(exist_ok=True)
SCREENSHOT = OUT_DIR / "screenshot.png"

# 1) 写一个 hook html，注入到 game 页面
HOOK_JS = r"""
(async () => {
  if (window.__testHookInjected) return;
  window.__testHookInjected = true;
  // 等 main.js 加载
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  // 调 /api/start
  const startResp = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      era_id: 'wanli1587',
      identity: 'weaving_male',
      gender: 'male',
      character: {
        name: '沈织户',
        age: 30,
        occupation: '织工',
        background: '沈家原也不是盛泽本地人...欠着绸缎牙行周二爷三两银子的旧账',
        starting_situation: '手头现银一两二钱，欠牙行周二爷三两（利息每月三分）...马上要交春税折银（合四钱二分）',
        family: { wife: '张氏（26岁）', mother: '张氏（58岁）', son: '大毛（5岁）' },
      }
    })
  });
  const startData = await startResp.json();
  window.__testData = startData;
  // 调 startGame 走前端完整渲染
  await window.startGame(startData);
  await new Promise(r => setTimeout(r, 300));
  // 标记 done
  document.title = '__test_done__';
})();
"""

# 写 hook JS 文件
hook_path = OUT_DIR / "hook.js"
hook_path.write_text(HOOK_JS, encoding="utf-8")

# 2) Chrome headless: 打开页面 + 注入 hook + 截图 + dump dom
# 用 CDP 不能（需要外部工具），改用以下方法：
# a) 打开页面
# b) 在 URL 加 hash 触发 main.js 注入
# c) 用 --enable-automation + 远程调试
# 简单方案：直接用 puppeteer-like 调用 chrome devtools

# 改用最简单方案：把 hook 注入到 main.js 末尾（不推荐污染源）—— 改用 Selenium
# 或者：写一个独立的小 HTML 跟 game 页面同源（在 server 起一个 endpoint）

# 最简方案：用 Chrome 的 --user-data-dir + DevTools Protocol
# 但这复杂。换用更直接的方法：在 index.html 注入一个测试 hook

# 实际上最简单的就是直接用 --enable-automation + --remote-debugging-port
# 然后通过 CDP 发命令。但 Python 端没装 websocket 库

# 退而求其次：直接用 Chrome 跑 1 次拿 main page DOM，再跑 1 次注入 + 拿 game page DOM
# 用 --evaluate-on-new-document 注入

# Chrome --evaluate-on-new-document 不是标准 flag，我用 --user-data-dir + 配合写 localStorage
# 不行，那就用最原始的方法：sed 在 main.js 末尾插入 hook（临时污染，用完恢复）

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    # 临时在 main.js 末尾注入 hook
    inject = f"\n\n/* __test_hook__ */\nif (window.location.search.includes('__test__')) {{ {HOOK_JS} }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")
    print("已注入测试 hook")

    # 跑 Chrome 打开带 query 的页面
    url = URL + "?__test__=1"
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--window-size=1440,900",
        "--virtual-time-budget=12000",
        "--screenshot=" + str(SCREENSHOT),
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    print(f"Chrome exit: {proc.returncode}")

    # 拿 DOM
    cmd2 = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=15000",
        "--dump-dom",
        url,
    ]
    proc2 = subprocess.run(cmd2, capture_output=True, timeout=30, text=True)
    dom = proc2.stdout
    print(f"DOM 大小: {len(dom)} chars")
    (OUT_DIR / "dom_after.html").write_text(dom, encoding="utf-8")

finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")

# 3) 分析 DOM
print("\n" + "=" * 60)
print("v1.9.5 Chrome 实际 DOM 分析")
print("=" * 60)

# 等 main.js 渲染完（query 含 __test__ 触发 hook）
# 关键 class
print("\n[1] 关键 class 出现次数:")
for cls in ["layout", "game-mode", "game-container", "game-header", "game-layout",
            "char-card", "narrative-area", "timeline", "game-input-slot",
            "action-area", "input-area", "voice-options", "voice-options-grid",
            "btn_submit", "player_input", "action-input"]:
    n = dom.count(f'class="{cls}"')
    n_id = dom.count(f'id="{cls}"')
    if n or n_id:
        print(f"  .{cls}: class={n} id={n_id}")

# 输入框
print("\n[2] 输入框:")
inputs = re.findall(r'<(input|textarea)\b[^>]*\bid="([^"]+)"', dom)
print(f"  {inputs}")
print(f"  textarea 数量: {dom.count('<textarea')}")
print(f"  input 数量: {dom.count('<input ')}")

# 重复 id
ids = re.findall(r'\bid="([^"]+)"', dom)
dup = {k: v for k, v in Counter(ids).items() if v > 1}
print(f"\n[3] 重复 id: {dup if dup else '无 ✓'}")

# voice-options-grid
vog = re.findall(r'id="voice-options-grid"[^>]*', dom)
print(f"\n[4] voice-options-grid 元素: {vog[:1]}")

# 声音按钮（更宽松的匹配：允许 class 内空格、允许内部有 span 等）
voice_items = re.findall(r'<button[^>]*class="voice-option-btn[^"]*"', dom)
print(f"  声音按钮（按 button 标签）: {len(voice_items)} 个")
# 提取 span.voice-name
voice_names = re.findall(r'class="voice-option-btn[^"]*"[^>]*>.*?<span class="voice-name">([^<]+)</span>', dom, re.DOTALL)
print(f"  声音名称: {voice_names}")

# 提交按钮
btns = re.findall(r'<button[^>]*\bid="([^"]+)"[^>]*>', dom)
print(f"\n[5] 按钮 id: {btns}")

# 4) 截图
print(f"\n[6] 截图: {SCREENSHOT} (大小: {SCREENSHOT.stat().st_size if SCREENSHOT.exists() else 0} bytes)")

# 5) 断言
print("\n" + "=" * 60)
print("断言")
print("=" * 60)
checks = [
    (".game-container 渲染", '<div class="game-container"' in dom),
    (".game-layout 渲染", '<div class="game-layout"' in dom),
    (".char-card 渲染", 'class="char-card"' in dom),
    (".narrative-area 渲染", 'class="narrative-area"' in dom),
    (".timeline 渲染", 'class="timeline"' in dom),
    (".game-input-slot 槽位存在", 'id="game-input-slot"' in dom),
    ("#action-area 存在", 'id="action-area"' in dom),
    ("#input-area 存在", 'id="input-area"' in dom),
    ("#voice-options-grid 存在", 'id="voice-options-grid"' in dom),
    ("textarea 唯一", dom.count('<textarea') == 1),
    ("input 元素 ≤ 1 (sidebar 的 new-task-input 是预期)", dom.count('<input ') <= 1),
    ("无重复 id", len(dup) == 0),
    ("#btn_submit 存在", 'id="btn_submit"' in dom),
    ("3 个开局声音 voice-option-btn (排除自由输入)", len(voice_items) - dom.count('voice-option-btn other') == 3),
]
passed = 0
for name, ok in checks:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}")
    if ok:
        passed += 1
print(f"\n通过: {passed}/{len(checks)}")
sys.exit(0 if passed == len(checks) else 1)
