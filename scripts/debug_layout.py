"""debug layout 在 1440 视口下的实际尺寸"""
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
  await new Promise(r => setTimeout(r, 2000));
  const l = document.getElementById("app-layout");
  const m = document.getElementById("main");
  const dump = {
    viewport: { w: window.innerWidth, h: window.innerHeight },
    body: document.body.getBoundingClientRect(),
    bodyComputed: { w: getComputedStyle(document.body).width, ml: getComputedStyle(document.body).marginLeft },
    layout: l ? l.getBoundingClientRect() : null,
    layoutComputed: l ? { w: getComputedStyle(l).width, display: getComputedStyle(l).display, pos: getComputedStyle(l).position } : null,
    main: m ? m.getBoundingClientRect() : null,
    mainComputed: m ? { w: getComputedStyle(m).width, ml: getComputedStyle(m).marginLeft, pl: getComputedStyle(m).paddingLeft, pr: getComputedStyle(m).paddingRight } : null,
    bodyChildren: Array.from(document.body.children).map(c => ({tag: c.tagName, id: c.id, w: c.offsetWidth, x: c.getBoundingClientRect().x})),
  };
  const pre = document.createElement("pre");
  pre.id = "__layout__";
  pre.textContent = JSON.stringify(dump, null, 2);
  document.body.appendChild(pre);
  document.title = "__done__";
})();
}
"""
    main_js.write_text(backup + inject, encoding="utf-8")
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--window-size=1440,900",
        "--virtual-time-budget=8000",
        "--dump-dom",
        "http://localhost:8765/?__test__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
    dom = proc.stdout
    m = re.search(r'<pre id="__layout__"[^>]*>(.+?)</pre>', dom, re.DOTALL)
    if m:
        data = json.loads(html.unescape(m.group(1)))
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("没找到 dump")
finally:
    main_js.write_text(backup, encoding="utf-8")
