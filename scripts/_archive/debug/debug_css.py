"""调试 .layout gridTemplateColumns 实际应用"""
from pathlib import Path
import subprocess
import json
import re

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = """
if (window.location.search.includes('__test_css__')) {
  setTimeout(() => {
    const l = document.getElementById('app-layout');
    const cs = getComputedStyle(l);
    const dump = {
      gridTemplateColumns: cs.gridTemplateColumns,
      cssRules: []
    };
    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules) {
          if (rule.selectorText && rule.selectorText.includes('layout')) {
            dump.cssRules.push({ selector: rule.selectorText, gridTemplateColumns: rule.style.gridTemplateColumns });
          }
        }
      } catch (e) {}
    }
    console.log('CSS_DUMP:' + JSON.stringify(dump));
  }, 2000);
}
"""
    main_js.write_text(backup + inject, encoding="utf-8")

    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--enable-logging=stderr", "--v=1",
        "--window-size=1280,720",
        "--virtual-time-budget=8000",
        "http://localhost:8765/?__test_css__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    err = proc.stderr.decode("utf-8", errors="ignore")
    for line in err.split("\n"):
        if "CSS_DUMP" in line or "CONSOLE" in line or "INFO" in line:
            print(line[:300])
finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")
