"""v1.9.5 完整端到端 review：首页 + Wizard + 游戏页 × 桌面/移动"""
import re
import subprocess
import sys
import time
from pathlib import Path

URL = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_full_review")
OUT_DIR.mkdir(exist_ok=True)

# 3 段：home / wizard / game
PAGES = {
    "home": f"{URL}/",
    "wizard": f"{URL}/",
    "game": f"{URL}/?__test__=1",
}

HOOKS = {
    "home": "",  # 不用 hook，直接截图首页
    "wizard": "",  # wizard 需要手动点，我们只截图首页 + 游戏中
    "game": r"""
(async () => {
  if (window.__testHookInjected) return;
  window.__testHookInjected = true;
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  try { localStorage.removeItem("hfe_voice_options_collapsed"); } catch(_){}
  window.__VOICE_PREFS_EXPLICIT = false;
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
}

VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 375, 812),
]

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")

try:
    # 给 game page 注入 hook
    game_hook = HOOKS["game"]
    inject = f"\nif (window.location.search.includes('__test__')) {{ (async () => {{ {game_hook} }})() }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")
    print("✓ 注入 game hook")

    # 截图 3 页 × 2 视口
    for page_name, page_url in PAGES.items():
        for vp_name, w, h in VIEWPORTS:
            time.sleep(8)  # 限流
            out = OUT_DIR / f"{page_name}_{vp_name}_{w}x{h}.png"
            cmd = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "--headless=new", "--disable-gpu", "--no-sandbox",
                "--hide-scrollbars",
                f"--window-size={w},{h}",
                "--virtual-time-budget=15000",
                f"--screenshot={out}",
                page_url,
            ]
            proc = subprocess.run(cmd, capture_output=True, timeout=30)
            size = out.stat().st_size if out.exists() else 0
            print(f"  {page_name} @ {vp_name} ({w}x{h}): {size} bytes (exit={proc.returncode})")
finally:
    main_js.write_text(backup, encoding="utf-8")
    print("✓ 恢复 main.js")
