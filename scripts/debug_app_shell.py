"""debug App Shell 结构 - 详细 dump header/main/footer 实际状态"""
import time, subprocess, re, json, html
from pathlib import Path

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = """
if (window.location.search.includes("__test__")) {
(async () => {
  if (window.__testHookInjected) {
    await new Promise(r => setTimeout(r, 2000));
    await dumpAll();
    return;
  }
  window.__testHookInjected = true;
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === "function") break;
    await new Promise(r => setTimeout(r, 100));
  }
  const r = await fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({era_id:"wanli1587",identity:"weaving_male",gender:"male",character:{name:"沈织户",age:30,occupation:"织工",hometown:"盛泽镇"}})
  });
  const d = await r.json();
  await window.startGame(d);
  await new Promise(rr => setTimeout(rr, 1500));
  await dumpAll();

  async function dumpAll() {
    const l = document.getElementById("app-layout");
    const m = document.getElementById("main");
    const header = document.querySelector(".app-header");
    const footer = document.querySelector(".app-footer");
    const inner = document.querySelector(".app-main-inner");
    const get = (el) => el ? {
      h: el.offsetHeight, sh: el.scrollHeight, st: el.scrollTop,
      x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y,
      w: el.offsetWidth, visible: el.offsetParent !== null,
      className: el.className,
    } : null;
    const dump = {
      viewport: { w: window.innerWidth, h: window.innerHeight },
      layout: get(l),
      main: get(m),
      header: get(header),
      footer: get(footer),
      inner: get(inner),
      charCard: get(document.querySelector(".char-card")),
      narrative: get(document.querySelector(".narrative-area")),
      timeline: get(document.querySelector(".timeline")),
      gameInputSlot: get(document.querySelector("#game-input-slot")),
    };
    const pre = document.createElement("pre");
    pre.id = "__appshell__";
    pre.textContent = JSON.stringify(dump, null, 2);
    document.body.appendChild(pre);
    document.title = "__done__";
  }
})();
}
"""
    main_js.write_text(backup + inject, encoding="utf-8")
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--window-size=1280,800",
        "--virtual-time-budget=12000",
        "--dump-dom",
        "http://localhost:8765/?__test__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=20, text=True)
    dom = proc.stdout
    m = re.search(r'<pre id="__appshell__"[^>]*>(.+?)</pre>', dom, re.DOTALL)
    if m:
        data = json.loads(html.unescape(m.group(1)))
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("没找到 dump")
finally:
    main_js.write_text(backup, encoding="utf-8")
