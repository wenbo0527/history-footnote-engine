"""v1.9.5 修复后 重新截图 review"""
import json
import re
import subprocess
import sys
from pathlib import Path

URL_BASE = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_v2")
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
      era_id: 'wanli1587', identity: 'weaving_male', gender: 'male',
      character: { name: '沈织户', age: 30, occupation: '织工', hometown: '盛泽镇' }
    })
  });
  const startData = await startResp.json();
  await window.startGame(startData);
  await new Promise(r => setTimeout(r, 500));
  document.title = '__test_done__';
})();
"""

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = f"\nif (window.location.search.includes('__test__')) {{ (async () => {{ {HOOK_JS} }})() }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")

    viewports = [
        ("1920x1080", 1920, 1080),
        ("1440x900", 1440, 900),
        ("1280x720", 1280, 720),
        ("1024x768", 1024, 768),
        ("375x667", 375, 667),
    ]
    for label, w, h in viewports:
        out = OUT_DIR / f"screen_{label}.png"
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={w},{h}",
            "--virtual-time-budget=15000",
            f"--screenshot={out}",
            f"{URL_BASE}/?__test__=1",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        print(f"[{label}] {out.stat().st_size if out.exists() else 0} bytes")
finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")
