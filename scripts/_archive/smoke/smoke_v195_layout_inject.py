"""用 Chrome 把 layout 详细尺寸写到 document.title"""
import json
import re
import subprocess
import sys
from pathlib import Path

URL_BASE = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_inspect2")
OUT_DIR.mkdir(exist_ok=True)

HOOK_JS = r"""
  if (window.__testHookInjected) return;
  window.__testHookInjected = true;
  console.log('[HOOK] start');
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  console.log('[HOOK] startGame ready, calling /api/start');
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
  console.log('[HOOK] startGame done');
  await new Promise(r => setTimeout(r, 2000));
  console.log('[HOOK] about to dump');

  // 收集布局信息
  const dump = {};
  dump.viewport = { w: window.innerWidth, h: window.innerHeight };
  const layout = document.getElementById('app-layout');
  const lRect = layout.getBoundingClientRect();
  dump.layout = {
    gridTemplateColumns: getComputedStyle(layout).gridTemplateColumns,
    offsetWidth: layout.offsetWidth,
    className: layout.className,
    inlineStyle: layout.getAttribute('style'),
    viewportX: lRect.x,
    viewportWidth: lRect.width,
    display: getComputedStyle(layout).display,
  };
  const main = document.getElementById('main');
  const mainRect = main.getBoundingClientRect();
  dump.main = {
    offsetWidth: main.offsetWidth,
    offsetHeight: main.offsetHeight,
    gridArea: getComputedStyle(main).gridArea,
    gridColumn: getComputedStyle(main).gridColumn,
    width: getComputedStyle(main).width,
    transform: getComputedStyle(main).transform,
    clientWidth: main.clientWidth,
    clientLeft: main.clientLeft,
    boundingRect: { x: mainRect.x, y: mainRect.y, w: mainRect.width, h: mainRect.height },
    left: main.offsetLeft,
    padding: getComputedStyle(main).padding,
    boxSizing: getComputedStyle(main).boxSizing,
    inlineStyle: main.getAttribute('style'),
    position: getComputedStyle(main).position,
    top: getComputedStyle(main).top,
    mainViewportX: mainRect.x,
    mainViewportWidth: mainRect.width,
  };
  dump.mainParent = main.parentElement ? main.parentElement.tagName + "#" + main.parentElement.id + "." + main.parentElement.className.split(" ")[0] : "null";
  const container = document.querySelector('.game-container');
  const cRect = container.getBoundingClientRect();
  dump.gameContainer = { offsetWidth: container.offsetWidth, viewportX: cRect.x, viewportWidth: cRect.width };
  const inner = document.querySelector('.game-container-inner');
  dump.gameContainerInner = { offsetWidth: inner.offsetWidth };
  const gl = document.querySelector('.game-layout');
  dump.gameLayout = {
    offsetWidth: gl.offsetWidth,
    flexWrap: getComputedStyle(gl).flexWrap,
    children: Array.from(gl.children).map(c => ({
      class: c.className.split(' ')[0],
      offsetWidth: c.offsetWidth,
      offsetLeft: c.offsetLeft,
      offsetTop: c.offsetTop,
      flex: getComputedStyle(c).flex,
    })),
  };
  // sidebar 实际状态
  const sb = document.querySelector('.sidebar');
  if (sb) {
    dump.sidebar = {
      offsetWidth: sb.offsetWidth,
      offsetHeight: sb.offsetHeight,
      display: getComputedStyle(sb).display,
      width: getComputedStyle(sb).width,
      gridColumn: getComputedStyle(sb).gridColumn,
      visible: sb.offsetParent !== null,
    };
  }
  // body / html 的 transform / position
  dump.bodyTransform = getComputedStyle(document.body).transform;
  dump.htmlTransform = getComputedStyle(document.documentElement).transform;
  dump.bodyDisplay = getComputedStyle(document.body).display;
  dump.htmlDisplay = getComputedStyle(document.documentElement).display;
  dump.bodyScrollLeft = document.body.scrollLeft;
  dump.htmlScrollLeft = document.documentElement.scrollLeft;
  dump.bodyRect = document.body.getBoundingClientRect();
  dump.htmlRect = document.documentElement.getBoundingClientRect();
  dump.bodyChildren = Array.from(document.body.children).map(c => ({tag: c.tagName, id: c.id, class: c.className.split(" ")[0], x: c.getBoundingClientRect().x, w: c.getBoundingClientRect().width}));
  // 写到 DOM 里（dump-dom 能拿到）
  const pre = document.createElement('pre');
  pre.id = '__layout_dump__';
  pre.style.display = 'none';
  pre.textContent = JSON.stringify(dump, null, 2);
  document.body.appendChild(pre);
  console.log('[HOOK] dump done, sidebar=' + JSON.stringify(dump.sidebar));
  document.title = '__test_done__';
"""

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = f"\n/* __test_hook__ */\nif (window.location.search.includes('__test__')) {{ (async () => {{ {HOOK_JS} }})() }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")

    for label, w, h in [("1280", 1280, 720), ("1024", 1024, 768)]:
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new", "--disable-gpu", "--no-sandbox",
            f"--window-size={w},{h}",
            "--virtual-time-budget=15000",
            "--dump-dom",
            f"{URL_BASE}/?__test__=1",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        dom = proc.stdout
        (OUT_DIR / f"dom_{label}.html").write_text(dom, encoding="utf-8")
        # 提取 __layout_dump__
        m = re.search(r'<pre id="__layout_dump__"[^>]*>(.+?)</pre>', dom, re.DOTALL)
        if m:
            import html
            data = html.unescape(m.group(1))
            info = json.loads(data)
            print(f"\n=== 视口 {label}x{h} ===")
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            print(f"视口 {label}: 没找到 __layout_dump__")

finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")
