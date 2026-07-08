"""测试滚动到一半的截图"""
import time, subprocess
from pathlib import Path

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = """
if (window.location.search.includes("__test__")) {
(async () => {
  if (window.__testHookInjected) return;
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
  document.getElementById("main").scrollTop = 500;
  document.title = "__done__";
})();
}
"""
    main_js.write_text(backup + inject, encoding="utf-8")
    time.sleep(2)
    cmd = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1280,800", "--virtual-time-budget=12000", "--screenshot=/tmp/v195_scrolled.png", "http://localhost:8765/?__test__=1"]
    subprocess.run(cmd, capture_output=True, timeout=20)
    print("screenshot done")
finally:
    main_js.write_text(backup, encoding="utf-8")
