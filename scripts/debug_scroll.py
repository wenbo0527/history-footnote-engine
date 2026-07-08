"""debug scroll 在游戏页 + 首页"""
from pathlib import Path
import subprocess
import re
import json
import html

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = """
if (window.location.search.includes("__test__")) {
(async () => {
  if (window.__testHookInjected) {
    await new Promise(r => setTimeout(r, 2000));
    await dumpScroll();
    return;
  }
  window.__testHookInjected = true;
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  const startResp = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({era_id: 'wanli1587', identity: 'weaving_male', gender: 'male', character: {name:'沈织户',age:30,occupation:'织工',hometown:'盛泽镇'}})
  });
  const startData = await startResp.json();
  await window.startGame(startData);
  await new Promise(r => setTimeout(r, 500));
  await dumpScroll();

  async function dumpScroll() {
    const l = document.getElementById("app-layout");
    const m = document.getElementById("main");
    const dump = {
      viewport: { w: window.innerWidth, h: window.innerHeight },
      body: { h: document.body.offsetHeight, sh: document.body.scrollHeight, st: document.body.scrollTop, overflow: getComputedStyle(document.body).overflow },
      html: { h: document.documentElement.offsetHeight, sh: document.documentElement.scrollHeight, st: document.documentElement.scrollTop, overflow: getComputedStyle(document.documentElement).overflow },
      layout: l ? { h: l.offsetHeight, sh: l.scrollHeight, st: l.scrollTop, overflow: getComputedStyle(l).overflow } : null,
      main: m ? { h: m.offsetHeight, sh: m.scrollHeight, st: m.scrollTop, overflow: getComputedStyle(m).overflow, overflowY: getComputedStyle(m).overflowY } : null,
      mainInnerHTMLLen: m ? m.innerHTML.length : 0,
    };
    const pre = document.createElement("pre");
    pre.id = "__scroll__";
    pre.textContent = JSON.stringify(dump, null, 2);
    document.body.appendChild(pre);
    document.title = "__done__";
  }
})();
}
"""
    main_js.write_text(backup + inject, encoding="utf-8")
    for path, name in [("http://localhost:8765/", "home"), ("http://localhost:8765/?__test__=1", "game")]:
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new", "--disable-gpu", "--no-sandbox",
            "--window-size=1280,800",
            "--virtual-time-budget=8000",
            "--dump-dom",
            path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
        dom = proc.stdout
        m = re.search(r'<pre id="__scroll__"[^>]*>(.+?)</pre>', dom, re.DOTALL)
        if m:
            data = json.loads(html.unescape(m.group(1)))
            print(f"\n=== {name} ===")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\n=== {name} === (没找到 dump)")
finally:
    main_js.write_text(backup, encoding="utf-8")
