"""v1.9.5 布局 inspector: dump 1024px 视口下 game-layout 实际尺寸"""
import json
import re
import subprocess
import sys
from pathlib import Path

URL_BASE = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_inspect")
OUT_DIR.mkdir(exist_ok=True)

HOOK_JS = r"""
(async () => {
  if (window.__testHookInjected) return;
  window.__testHookInjected = true;
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  const startResp = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      era_id: 'wanli1587',
      identity: 'weaving_male',
      gender: 'male',
      character: { name: '沈织户', age: 30, occupation: '织工', hometown: '盛泽镇' }
    })
  });
  const startData = await startResp.json();
  await window.startGame(startData);
  await new Promise(r => setTimeout(r, 200));
  // dump layout
  const gl = document.querySelector('.game-layout');
  const children = Array.from(gl.children);
  window.__layoutInfo = {
    viewport: { w: window.innerWidth, h: window.innerHeight },
    gameLayout: {
      width: gl.offsetWidth,
      flexWrap: getComputedStyle(gl).flexWrap,
      children: children.map(c => ({
        class: c.className.split(' ')[0],
        width: c.offsetWidth,
        height: c.offsetHeight,
        offsetTop: c.offsetTop,
        offsetLeft: c.offsetLeft,
        flex: getComputedStyle(c).flex,
        display: getComputedStyle(c).display,
      }))
    }
  };
  document.title = '__test_done__';
})();
"""

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")

try:
    inject = f"\n/* __test_hook__ */\nif (window.location.search.includes('__test__')) {{ {HOOK_JS} }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")

    # 多个视口
    for label, w, h in [("1920", 1920, 1080), ("1440", 1440, 900), ("1280", 1280, 720), ("1024", 1024, 768), ("768", 768, 1024), ("375", 375, 667)]:
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new", "--disable-gpu", "--no-sandbox",
            f"--window-size={w},{h}",
            "--virtual-time-budget=12000",
            f"--screenshot={OUT_DIR}/screen_{label}.png",
            f"{URL_BASE}/?__test__=1",
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)

    # dump dom 拿 layoutInfo
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--window-size=1024,768",
        "--virtual-time-budget=15000",
        "--dump-dom",
        f"{URL_BASE}/?__test__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
    dom = proc.stdout

    # 找 layoutInfo（用 document.title 触发）
    # dump-dom 拿的是 initial DOM 渲染完，hook 跑完后改的 window.__layoutInfo 在 DOM 看不到
    # 改用 console.log
finally:
    main_js.write_text(backup, encoding="utf-8")

# 改用 evaluate 模式（通过 --enable-logging --v=1 + console.log 收集）
# 实际上 Chrome headless 的 --dump-dom 包含所有静态 DOM，hook 的副作用（改 window）不会出来
# 我用更直接的方法：在 page 里 postMessage 到 console
print("用 --enable-logging + console.log 把 layoutInfo 写到 stderr")
main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    hook_with_console = HOOK_JS.replace("document.title = '__test_done__';", "document.title = '__test_done__'; setTimeout(() => { console.log('LAYOUT_INFO:' + JSON.stringify(window.__layoutInfo)); }, 100);")
    inject = f"\n/* __test_hook__ */\nif (window.location.search.includes('__test__')) {{ {hook_with_console} }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")

    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--enable-logging=stderr", "--v=0",
        f"--window-size=1024,768",
        "--virtual-time-budget=15000",
        f"{URL_BASE}/?__test__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    stderr = proc.stderr.decode("utf-8", errors="ignore")
    # 找 LAYOUT_INFO 行
    matches = re.findall(r"LAYOUT_INFO:(.+)", stderr)
    if matches:
        info = json.loads(matches[-1])
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print("❌ 没找到 LAYOUT_INFO 行（hook 没跑成功）")
        # 退而求其次：用 dump-dom
        print("\n回退：从 dom_after.html 找 char-card/narrative/timeline 的内联 style")
        cmd2 = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new", "--disable-gpu", "--no-sandbox",
            f"--window-size=1024,768",
            "--virtual-time-budget=15000",
            "--dump-dom",
            f"{URL_BASE}/?__test__=1",
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, timeout=30, text=True)
        dom = proc2.stdout
        for cls in ["game-layout", "char-card", "narrative-area", "timeline", "game-container-inner", "game-input-slot"]:
            for m in re.finditer(rf'<(\w+)\s+class="{cls}"[^>]*>', dom):
                print(f"  {cls}: {m.group(0)[:200]}")
finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")
